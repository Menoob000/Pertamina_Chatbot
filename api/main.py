"""
FastAPI Backend for Pertamina Dokumen Tender Generation.
Provides RESTful endpoints to extract context from RKS/BOQ and generate formal Dokumen Tender DOCX files.
"""

import os
import io
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv

from tools.tender.generator import generate_tender_document, export_tender_to_docx, _active_tender_store
from tools.tender.extractor import extract_rks_info, extract_boq_info
from tools.tender.docx import OUTPUT_DIR

load_dotenv()

HOST = os.getenv("FASTAPI_HOST", "127.0.0.1")
PORT = int(os.getenv("FASTAPI_PORT", "8000"))

app = FastAPI(
    title="Pertamina Tender Generator API",
    description="Dedicated API service to generate formal Dokumen Tender and Contract Amendments based on Pertamina Procurement Guidelines.",
    version="1.0.0",
)

# Enable CORS for Streamlit / Frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TenderGenerateRequest(BaseModel):
    nama_pengadaan: str = "Pengadaan Jasa / Barang"
    nomor_tender: str = "No.Project/DT/PND970000/2026-S7"
    tanggal: str = "04 Desember 2025"
    prime_cost: float = 13283434534.0
    total_dengan_kr: float = 14346100000.0
    resiko_csms: str = "Tinggi"
    tkdn_minimal: float = 20.12
    pejabat_procurement_nama: str = "Rigga Widar Atmagi"
    pejabat_procurement_jabatan: str = "Area Manager Procurement Kalimantan"
    pejabat_berwenang: str = "Sr. Manager Opt. & Maint. Regional Kalimantan"
    pengawas_pekerjaan: str = "Region Manager RPD Regional Kalimantan"
    metode_pemenuhan: str = "Tender Terbatas"
    jenis_kontrak: str = "Gabungan Harga Satuan & Lumpsum"
    prebid_tanggal: str = "Senin, 08 Desember 2025"
    prebid_waktu: str = "10.00 WITA"
    prebid_tempat: str = "Microsoft Teams Meeting dengan link yang disampaikan melalui email Undangan Prebid Meeting"
    pemasukan_mulai: str = "Senin, 08 Desember 2025"
    pemasukan_selesai: str = "Senin, 15 Desember 2025"
    context_summary: Optional[str] = ""
    boq_items: Optional[List[Dict[str, Any]]] = None
    output_filename: Optional[str] = ""


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Pertamina Tender Generator API",
        "version": "1.0.0"
    }


@app.get("/api/tender/recent-rks")
def get_recent_rks():
    """Lists recently converted DOCX files in the output directory that can be used as RKS context."""
    if not OUTPUT_DIR.exists():
        return {"files": []}

    docx_files = []
    for f in sorted(OUTPUT_DIR.glob("*.docx"), key=os.path.getmtime, reverse=True):
        if not f.name.startswith("Dokumen_Tender"):
            docx_files.append({
                "filename": f.name,
                "filepath": str(f.resolve()),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "modified": f.stat().st_mtime
            })
    return {"files": docx_files[:10]}


@app.post("/api/tender/extract-context")
async def extract_context(
    rks_file: Optional[UploadFile] = File(None),
    rks_filepath: Optional[str] = Form(None),
    boq_file: Optional[UploadFile] = File(None)
):
    """
    Extracts project metadata, CSMS risk, scope of work, and HPS from RKS and/or BOQ files.
    """
    rks_data: Dict[str, Any] = {}
    boq_data: Dict[str, Any] = {}

    # 1. Process RKS
    if rks_file and rks_file.filename:
        content = await rks_file.read()
        rks_data = extract_rks_info(content, filename=rks_file.filename)
    elif rks_filepath and os.path.exists(rks_filepath):
        rks_data = extract_rks_info(rks_filepath)

    # 2. Process BOQ
    if boq_file and boq_file.filename:
        content = await boq_file.read()
        boq_data = extract_boq_info(content, filename=boq_file.filename)

    # Merge context summaries
    context_parts = []
    if rks_data.get("context_summary"):
        context_parts.append(rks_data["context_summary"])
    if boq_data.get("summary"):
        context_parts.append(boq_data["summary"])

    return {
        "status": "success",
        "nama_pengadaan": rks_data.get("nama_pengadaan") or "",
        "resiko_csms": rks_data.get("resiko_csms") or "Tinggi",
        "prime_cost": boq_data.get("prime_cost", 0.0),
        "total_dengan_kr": boq_data.get("total_dengan_kr", 0.0),
        "boq_items": boq_data.get("items", []),
        "combined_context_summary": "\n\n".join(context_parts)
    }


@app.post("/api/tender/generate")
def generate_tender(payload: TenderGenerateRequest):
    """
    Generates Dokumen Tender JSON via LLM and renders it into a formal Pertamina DOCX file.
    """
    try:
        # Convert request model to kwargs dictionary
        kwargs = payload.model_dump()

        # 1. Generate tender document draft via LLM
        msg = generate_tender_document.invoke(kwargs)
        if "Error" in msg:
            raise HTTPException(status_code=500, detail=msg)

        # 2. Inject BOQ items into Lampiran 5B if provided
        draft = _active_tender_store.get("current_draft")
        if draft and payload.boq_items:
            draft["lampiran_5b_boq_items"] = payload.boq_items

        # 3. Export to DOCX
        output_filename = payload.output_filename or ""
        export_msg = export_tender_to_docx.invoke({"output_filename": output_filename})

        if "Error" in export_msg:
            raise HTTPException(status_code=500, detail=export_msg)

        # Extract file path
        file_path = export_msg.replace("📄 File: ", "").strip()
        filename = os.path.basename(file_path)

        return {
            "status": "success",
            "message": "Dokumen Tender berhasil dibuat secara lengkap!",
            "filename": filename,
            "filepath": file_path,
            "download_url": f"/api/tender/download/{filename}",
            "details": {
                "nama_pengadaan": payload.nama_pengadaan,
                "nomor_tender": payload.nomor_tender,
                "resiko_csms": payload.resiko_csms,
                "kriteria_teknis_count": len(draft.get("lampiran_2a_evaluasi_teknis", [])) if draft else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tender/download/{filename}")
def download_tender_docx(filename: str):
    """
    Serves the generated DOCX file for download.
    """
    safe_filename = os.path.basename(filename)
    file_path = OUTPUT_DIR / safe_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {safe_filename} tidak ditemukan.")

    return FileResponse(
        path=str(file_path),
        filename=safe_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Pertamina Tender Generator API on http://{HOST}:{PORT}")
    uvicorn.run("api.main:app", host=HOST, port=PORT, reload=True)

