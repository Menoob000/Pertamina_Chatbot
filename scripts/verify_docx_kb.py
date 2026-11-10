"""Generate review artifacts and exercise a separate local DOCX KB collection."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["RKS_CSMS_LLM_ENABLED"] = "false"
os.environ["RKS_SEARCH_SEMANTIC_ENABLED"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"

from docx import Document
import pymupdf
from tests.test_docx_kb import make_source
from tools.rks.catalog import list_sources
from tools.rks.retrieval import search_evidence
from tools.rks.service import create_document, artifact_file


def finalize_existing(folder):
    from tools.rks.validation import validate_docx
    report_path = folder / "verification.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = report["generation"]
    artifact = folder / "artifacts" / result["artifact_id"]
    docx_path, pdf_path = artifact / "RKS.docx", artifact / "RKS.pdf"
    render = json.loads((folder / "word_diagnostic.json").read_text(encoding="utf-8"))
    extracted = json.loads((artifact / "extraction.json").read_text(encoding="utf-8"))
    result["verification"] = validate_docx(extracted, docx_path)
    assert result["verification"]["passed"], result["verification"]
    result["preview"] = {**render, "available": True,
                         "toc_verified": not render["toc_mismatches"] and render["toc_entries_checked"] >= extracted["heading_count"]}
    result["docx_sha256"] = hashlib.sha256(docx_path.read_bytes()).hexdigest()
    result["pdf_sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    result["preview_url"] = f"/api/rks/{result['artifact_id']}/preview.pdf"
    result["issues"] = [issue for issue in result["issues"] if "render" not in issue["message"].lower()]
    result["status"] = "perlu pemeriksaan" if result["issues"] else "lengkap"
    (artifact / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(docx_path, folder / "RKS_Dari_KB_DOCX.docx")
    shutil.copyfile(pdf_path, folder / "RKS_Dari_KB_DOCX.pdf")
    pages = folder / "qa_pages"
    pages.mkdir(exist_ok=True)
    with pymupdf.open(pdf_path) as pdf:
        for number, page in enumerate(pdf, 1):
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(pages / f"page-{number}.png")
        report["pdf_pages"] = len(pdf)
    report["renderer_note"] = "Native Word renderer required execution outside the sandbox COM session."
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"preview": result["preview"], "verification": result["verification"], "pages": report["pdf_pages"]}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--directory", default="output/docx_kb_review")
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    folder = (ROOT / args.directory).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if args.finalize_existing:
        finalize_existing(folder)
        return
    kb = folder / "kb_input"
    source = make_source(kb / "RKS-overhaul-tangki-UNIT-UJI-2026-rev-1.docx")
    report = {"source": str(source), "source_kind": "explicit demonstration fixture, not real project data"}
    if args.database:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_postgres import PGVector
        from rag.doc_loader import loader, _connect, PGVECTOR_CONNECTION
        collection = "docx_kb_review_" + uuid4().hex[:10]
        embeddings = HuggingFaceEmbeddings(model_name=__import__("config").EMBEDDING_MODEL,
                                           model_kwargs={"local_files_only": True})
        store = PGVector(embeddings=embeddings, collection_name=collection, connection=PGVECTOR_CONNECTION)
        first = loader(kb, collection_name=collection, vector_store=store)
        assert len(first["indexed"]) == 1 and not first["failed"], first
        repeat = loader(kb, collection_name=collection, vector_store=store)
        assert len(repeat["skipped"]) == 1 and not repeat["indexed"], repeat
        doc = Document(source)
        doc.add_paragraph("Pembaruan sumber untuk pemeriksaan indeks versi kedua.")
        doc.save(source)
        revised = loader(kb, collection_name=collection, vector_store=store)
        assert len(revised["indexed"]) == 1 and not revised["failed"], revised
        corrupt = kb / "RKS-corrupt.docx"
        corrupt.write_bytes(b"not a Word file")
        try:
            isolated = loader(kb, collection_name=collection, vector_store=store)
            assert len(isolated["failed"]) == 1 and len(isolated["skipped"]) == 1, isolated
        finally:
            corrupt.unlink()
        with _connect(PGVECTOR_CONNECTION) as conn:
            rows = conn.execute("SELECT is_active, count(*) FROM documents WHERE collection_name = %s GROUP BY is_active", (collection,)).fetchall()
            assert dict(rows) == {True: 1, False: 1}, rows
            stale = conn.execute("""
                SELECT count(*) FROM langchain_pg_embedding e JOIN langchain_pg_collection c ON e.collection_id=c.uuid
                WHERE c.name=%s AND e.cmetadata->>'source_sha256' <> %s
            """, (collection, hashlib.sha256(source.read_bytes()).hexdigest())).fetchone()[0]
            assert stale == 0, stale
        semantic = store.similarity_search_with_relevance_scores("pelat 6 mm", k=3, filter={"document_type": "RKS"})
        assert semantic and semantic[0][0].metadata.get("location"), semantic
        hybrid = search_evidence("pelat 6 mm", list_sources(kb), semantic_store=store,
                                 use_semantic=True, score_threshold=.1)
        assert any(hit.get("semantic_score") is not None for hit in hybrid["results"]), hybrid
        report["database"] = {"collection": collection, "first": first, "repeat": repeat,
                               "revised": revised, "corrupt_isolation": isolated,
                               "active_versions": dict((str(k), v) for k, v in rows), "stale_vectors": stale,
                               "semantic_hits": len(semantic), "hybrid": hybrid}
    result = create_document("overhaul tangki UNIT-UJI", data_dir=kb, output_dir=folder / "artifacts")
    assert result["status"] != "gagal", result
    assert result["verification"]["passed"], result.get("verification")
    docx_path = artifact_file(result["artifact_id"], "docx", folder / "artifacts")
    shutil.copyfile(docx_path, folder / "RKS_Dari_KB_DOCX.docx")
    if result.get("preview", {}).get("available"):
        pdf_path = artifact_file(result["artifact_id"], "pdf", folder / "artifacts")
        shutil.copyfile(pdf_path, folder / "RKS_Dari_KB_DOCX.pdf")
        pngs = folder / "qa_pages"
        pngs.mkdir(exist_ok=True)
        with pymupdf.open(pdf_path) as pdf:
            for number, page in enumerate(pdf, 1):
                page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(pngs / f"page-{number}.png")
            report["pdf_pages"] = len(pdf)
    report["generation"] = result
    (folder / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"folder": str(folder), "preview": result["preview"],
                      "literal_verification": result["verification"],
                      "database": report.get("database", {}).get("collection")}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
