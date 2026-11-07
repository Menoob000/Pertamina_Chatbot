"""Immutable per-request artifacts and public RKS service contract."""
from __future__ import annotations

import hashlib
import json
import re
import logging
import config
from pathlib import Path
from uuid import uuid4

from .catalog import DATA_DIR, ROOT, list_sources, search_sources, public_source
from .text_extraction import extract_text_document
from .document import render_document
from .preview import finalize_and_preview
from .validation import validate_docx
from .retrieval import search_evidence
from .template import render_general_template

OUTPUT_DIR = ROOT / "output" / "rks"
PIPELINE_VERSION = "rks-editable-layout-v16"


def _general_template(query: str, output_dir: Path, render_preview: bool) -> dict:
    artifact_id = uuid4().hex
    folder = output_dir / artifact_id
    folder.mkdir(parents=True)
    docx = folder / "RKS.docx"
    try:
        render_general_template(query, docx)
        preview = finalize_and_preview(docx, 8) if render_preview else {
            "available": False, "message": "Preview belum dirender."}
        manifest = {"artifact_id": artifact_id, "pipeline_version": PIPELINE_VERSION,
                    "status": "perlu pemeriksaan", "mode": "template umum", "source": None,
                    "source_pages": 0, "evidence": [], "section_provenance": [], "preview": preview,
                    "issues": [{"page": None, "message": "Sumber knowledge base yang cukup relevan tidak ditemukan. Semua placeholder harus dilengkapi dan diperiksa."}],
                    "docx_sha256": hashlib.sha256(docx.read_bytes()).hexdigest(),
                    "docx_url": f"/api/rks/{artifact_id}/document.docx",
                    "preview_url": f"/api/rks/{artifact_id}/preview.pdf" if preview.get("available") else None,
                    "boq_status": "belum tersedia", "boq_note": "BOQ belum tersedia; isi oleh pengguna pada tahap tender.",
                    "message": "Template umum tanpa fakta proyek atau sitasi knowledge base. Isi bagian bertanda kurung siku sebelum digunakan."}
        if preview.get("available"):
            manifest["pdf_sha256"] = hashlib.sha256(docx.with_suffix(".pdf").read_bytes()).hexdigest()
        (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
    except Exception:
        logging.getLogger(__name__).exception("General RKS template creation failed")
        failure = {"artifact_id": artifact_id, "status": "gagal", "mode": "template umum",
                   "message": "Template umum RKS gagal dibuat. Periksa log layanan."}
        (folder / "manifest.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
        return failure


def create_document(query: str, source_id: str = "", *, data_dir: Path = DATA_DIR,
                    output_dir: Path = OUTPUT_DIR, render_preview: bool = True) -> dict:
    candidates = search_sources(query, data_dir)
    if source_id:
        # Explicit selection must still be a catalog source, never an arbitrary
        # client-supplied path or a fuzzy fallback to an unrelated PDF.
        source = next((x for x in list_sources(data_dir) if x["source_id"] == source_id), None)
        if source is None:
            return {"status": "gagal", "message": "Sumber tidak ditemukan atau telah berubah. Cari ulang RKS acuan."}
    elif not candidates:
        # A relevant passage can rescue a source whose filename is uninformative.
        catalog = list_sources(data_dir)
        rescue = search_evidence(query, catalog, top_k=1)
        top = rescue["results"][0] if rescue["results"] else None
        source = next((s for s in catalog if top and s["source_id"] == top["source_id"]), None)
        if source is None:
            return _general_template(query, output_dir, render_preview)
        source = {**source, "match_score": top["score"], "score": top["score"],
                  "matched_terms": top["matched_terms"]}
    else:
        source = candidates[0]
    alternatives = [public_source(x) for x in candidates if x["source_id"] != source["source_id"]]
    artifact_id = uuid4().hex
    folder = output_dir / artifact_id
    folder.mkdir(parents=True)
    try:
        extracted = extract_text_document(source)
        if hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Sumber berubah saat dibaca. Cari ulang RKS acuan.")
        (folder / "extraction.json").write_text(json.dumps(extracted, ensure_ascii=False, indent=2), encoding="utf-8")
        if not any(p["elements"] for p in extracted["pages"]):
            raise ValueError("Tidak ada isi yang dapat dipindahkan.")
        headings = []
        section_provenance = []
        for page in extracted["pages"]:
            for element in page["elements"]:
                if element["kind"] == "heading" and element["text"] not in headings:
                    headings.append(element["text"])
                    section_provenance.append({"section": element["text"],
                                               "filename": source["filename"],
                                               "source_id": source["source_id"],
                                               "page": page["page"]})
        section_queries = headings[:max(1, config.RKS_SEARCH_MAX_SECTIONS)] if headings else [query]
        evidence = []
        semantic_available = True
        for heading in section_queries:
            retrieved = search_evidence(heading, [source], top_k=config.RKS_SEARCH_TOP_K,
                                        use_semantic=semantic_available)
            if retrieved["semantic_status"] == "tidak tersedia":
                semantic_available = False
            evidence.append({"section": heading, "status": retrieved["status"],
                             "semantic_status": retrieved["semantic_status"],
                             "sources": retrieved["results"]})
        docx = folder / "RKS.docx"
        render_document(extracted, docx)
        preview = finalize_and_preview(docx, extracted["heading_count"]) if render_preview else {
            "available": False, "message": "Preview belum dirender."}
        issues = list(extracted["issues"])
        verification = validate_docx(extracted, docx)
        if not verification["passed"]:
            issues.append({"page": None, "message": "Pemeriksaan DOCX mendeteksi selisih teks atau jumlah gambar; hasil perlu diperiksa terhadap sumber."})
        if not preview.get("available"):
            issues.append({"page": None, "message": preview.get("message", "Preview belum tersedia.")})
        elif not preview.get("toc_verified"):
            issues.append({"page": None, "message": "Daftar isi pada DOCX dan preview perlu pemeriksaan."})
        boq_pages = []
        mentions_boq = False
        for page in extracted["pages"]:
            mentions_boq |= bool(re.search(r"\bBOQ\b|bill of quantit", page["source_text"], re.I))
            for element in page["elements"]:
                if element["kind"] in {"table", "image"} and not element.get("page_fallback"):
                    headers = re.findall(r"\b(?:uraian|volume|satuan|qty|harga)\b", element.get("text", ""), re.I)
                    if len(set(x.lower() for x in headers)) >= 3:
                        boq_pages.append(page["page"])
        boq_status = "tabel terdeteksi; perlu konfirmasi" if boq_pages else "rujukan saja" if mentions_boq else "tidak ditemukan"
        tied = any(x.get("match_score") == source.get("match_score") and
                   x.get("score") == source.get("score") for x in candidates
                   if x["source_id"] != source["source_id"])
        selection_note = ("Beberapa sumber memiliki skor sama; sumber pertama dipilih berdasarkan nama berkas. "
                          "Periksa kecocokan proyek sebelum digunakan." if tied else
                          "Sumber dengan peringkat tertinggi dipilih otomatis.")
        manifest = {"artifact_id": artifact_id, "pipeline_version": PIPELINE_VERSION,
                    "mode": "sumber knowledge base", "selection": {"method": "peringkat otomatis",
                    "match_score": source.get("match_score"), "alternatives": alternatives,
                    "note": selection_note}, "evidence": evidence,
                    "section_provenance": section_provenance,
                    "status": "perlu pemeriksaan" if issues else "lengkap",
                    "source": public_source(source), "source_pages": len(extracted["pages"]),
                    "issues": issues, "preview": preview, "verification": verification,
                    "heading_count": extracted["heading_count"],
                    "docx_sha256": hashlib.sha256(docx.read_bytes()).hexdigest(),
                    "docx_url": f"/api/rks/{artifact_id}/document.docx",
                    "preview_url": f"/api/rks/{artifact_id}/preview.pdf" if preview.get("available") else None,
                    "boq_status": boq_status, "boq_source_pages": sorted(set(boq_pages)),
                    "boq_note": f"BOQ: {boq_status}. Isi mengikuti sumber; tidak ada item, volume, atau harga yang ditambahkan.",
                    "message": "Draf tertata dari RKS referensi. Data proyek asal tetap tercantum."}
        if preview.get("available"):
            manifest["pdf_sha256"] = hashlib.sha256(docx.with_suffix(".pdf").read_bytes()).hexdigest()
        (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
    except Exception as exc:
        logging.getLogger(__name__).exception("RKS generation failed for %s", source["filename"])
        failure = {"artifact_id": artifact_id, "status": "gagal", "source": public_source(source),
                   "message": "Pembuatan RKS gagal. Sumber belum dapat diproses; pilih RKS acuan lain atau periksa log layanan."}
        (folder / "manifest.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
        return failure


def get_document(artifact_id: str, output_dir: Path = OUTPUT_DIR) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", artifact_id):
        raise FileNotFoundError("Identitas dokumen tidak valid.")
    return json.loads((output_dir / artifact_id / "manifest.json").read_text(encoding="utf-8"))


def artifact_file(artifact_id: str, kind: str, output_dir: Path = OUTPUT_DIR) -> Path:
    manifest = get_document(artifact_id, output_dir)
    if manifest["status"] == "gagal" or kind not in {"docx", "pdf"}:
        raise FileNotFoundError("File tidak tersedia.")
    if kind == "pdf" and not manifest.get("preview", {}).get("available"):
        raise FileNotFoundError("Preview belum tersedia.")
    path = output_dir / artifact_id / f"RKS.{kind}"
    expected = manifest.get(f"{kind}_sha256")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise FileNotFoundError("File berubah setelah finalisasi. Buat ulang dokumen.")
    return path


def latest_document(source_id: str, output_dir: Path = OUTPUT_DIR):
    """Reuse only a verified preview produced from this exact source/version."""
    paths = sorted(output_dir.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if ((manifest.get("source") or {}).get("source_id") != source_id or
                    manifest.get("pipeline_version") != PIPELINE_VERSION or
                    not manifest.get("preview", {}).get("available")):
                continue
            for kind in ("docx", "pdf"):
                artifact_file(manifest["artifact_id"], kind, output_dir)
            return manifest
        except (OSError, ValueError, KeyError):
            continue
    return None
