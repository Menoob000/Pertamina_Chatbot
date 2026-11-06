"""Immutable per-request artifacts and public RKS service contract."""
from __future__ import annotations

import hashlib
import json
import re
import logging
from pathlib import Path
from uuid import uuid4

from .catalog import DATA_DIR, ROOT, list_sources, search_sources, public_source
from .extraction import extract_document
from .document import render_document
from .preview import finalize_and_preview
from .validation import validate_docx

OUTPUT_DIR = ROOT / "output" / "rks"


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
        return {"status": "gagal", "message": "Tidak ditemukan RKS yang sesuai. Sebutkan pekerjaan atau identitas aset lebih spesifik."}
    elif len(candidates) > 1 and candidates[0]["score"] - candidates[1]["score"] < 3:
        return {"status": "pilih sumber", "message": "Ada beberapa RKS yang sama relevannya. Pilih RKS acuan.",
                "candidates": [public_source(x) for x in candidates[:5]]}
    else:
        source = candidates[0]
    artifact_id = uuid4().hex
    folder = output_dir / artifact_id
    folder.mkdir(parents=True)
    try:
        extracted = extract_document(source, folder / "assets")
        if hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Sumber berubah saat dibaca. Cari ulang RKS acuan.")
        (folder / "extraction.json").write_text(json.dumps(extracted, ensure_ascii=False, indent=2), encoding="utf-8")
        if not any(p["elements"] for p in extracted["pages"]):
            raise ValueError("Tidak ada isi yang dapat dipindahkan.")
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
        manifest = {"artifact_id": artifact_id, "status": "perlu pemeriksaan" if issues else "lengkap",
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
