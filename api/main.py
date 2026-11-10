"""
FastAPI Backend for Pertamina Dokumen Tender Generation.
Provides RESTful endpoints to extract context from RKS/BOQ and generate formal Dokumen Tender DOCX files.
"""

import os
import io
import hashlib
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
from tools.tender.docx import render_contract_to_docx_bytes
from tools.tender.contract_archive import ContractArchive
from api.rks import router as rks_router

load_dotenv()

HOST = os.getenv("FASTAPI_HOST", "127.0.0.1")
PORT = int(os.getenv("FASTAPI_PORT", "8000"))

app = FastAPI(
    title="Pertamina Tender Generator API",
    description="Dedicated API service to generate formal Dokumen Tender and Contract Amendments based on Pertamina Procurement Guidelines.",
    version="1.0.0",
)
app.include_router(rks_router)

# Enable CORS for Streamlit / Frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # This API does not use cookie-based authentication. Browsers reject
    # wildcard origins when credentialed requests are enabled.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TenderGenerateRequest(BaseModel):
    nama_pengadaan: str = Field(min_length=1)
    nomor_tender: str = ""
    tanggal: str = ""
    prime_cost: Optional[float] = Field(default=None, ge=0)
    total_dengan_kr: Optional[float] = Field(default=None, ge=0)
    resiko_csms: str = Field(default="", pattern="^(|Tinggi|Sedang|Rendah)$")
    tkdn_minimal: float = Field(ge=0, le=100)
    pejabat_procurement_nama: str = ""
    pejabat_procurement_jabatan: str = ""
    pejabat_berwenang: str = ""
    pengawas_pekerjaan: str = ""
    officials: Optional[Dict[str, Dict[str, Any]]] = None
    metode_pemenuhan: str = ""
    jenis_kontrak: str = ""
    prebid_tanggal: str = ""
    prebid_waktu: str = ""
    prebid_tempat: str = ""
    pemasukan_mulai: str = ""
    pemasukan_selesai: str = ""
    context_summary: Optional[str] = ""
    boq_items: Optional[List[Dict[str, Any]]] = None
    rks_artifact_id: Optional[str] = None
    output_filename: Optional[str] = ""


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Pertamina Tender Generator API",
        "version": "1.0.0",
        "features": {"contract_archive": True},
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
    boq_file: Optional[UploadFile] = File(None),
    rks_artifact_id: Optional[str] = Form(None),
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
    if rks_artifact_id and rks_data:
        from tools.rks.service import artifact_file, get_document
        try:
            manifest = get_document(rks_artifact_id)
            artifact_docx = artifact_file(rks_artifact_id, "docx")
            if not rks_file or hashlib.sha256(content).hexdigest() != hashlib.sha256(artifact_docx.read_bytes()).hexdigest():
                rks_data.setdefault("issues", []).append("Berkas RKS tidak cocok dengan artifact; CSMS manifest diabaikan.")
            else:
                rks_data["officials_project_key"] = f"rks:{rks_artifact_id}"
                category = (manifest.get("csms_assessment") or {}).get("category")
                if category in {"HIGH", "MIDDLE", "LOW"}:
                    rks_data["resiko_csms"] = {"HIGH": "Tinggi", "MIDDLE": "Sedang", "LOW": "Rendah"}[category]
                    rks_data.setdefault("sources", {})["resiko_csms"] = {
                        "filename": f"RKS-{rks_artifact_id[:8]}", "location": "manifest RKS, penilaian CSMS"}
                else:
                    rks_data["resiko_csms"] = None
                    rks_data.setdefault("sources", {}).pop("resiko_csms", None)
                    rks_data.setdefault("issues", []).append("Penilaian CSMS artifact belum pasti; isi manual.")
        except (OSError, ValueError, KeyError):
            rks_data.setdefault("issues", []).append("Manifest RKS tidak tersedia untuk verifikasi CSMS.")

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
        "resiko_csms": rks_data.get("resiko_csms"),
        "officials": rks_data.get("officials", {}),
        "officials_project_key": rks_data.get("officials_project_key"),
        "prime_cost": boq_data.get("prime_cost"),
        "total_dengan_kr": boq_data.get("total_dengan_kr"),
        "boq_items": boq_data.get("items", []),
        "combined_context_summary": "\n\n".join(context_parts),
        "sources": {**rks_data.get("sources", {}), **boq_data.get("sources", {})},
        "issues": rks_data.get("issues", []) + boq_data.get("issues", []),
    }


@app.post("/api/tender/generate")
def generate_tender(payload: TenderGenerateRequest):
    """
    Generates Dokumen Tender JSON via LLM and renders it into a formal Pertamina DOCX file.
    """
    try:
        requested_filename = (payload.output_filename or "").strip()
        if (
            requested_filename in {".", ".."}
            or "/" in requested_filename
            or "\\" in requested_filename
        ):
            raise HTTPException(
                status_code=422,
                detail="output_filename harus berupa nama file tanpa path.",
            )

        # Convert request model to kwargs dictionary
        kwargs = payload.model_dump()
        optional_fields = {
            "HPS Prime Cost": payload.prime_cost,
            "Total HPS": payload.total_dengan_kr,
            "Nomor tender": payload.nomor_tender,
            "Tanggal dokumen": payload.tanggal,
            "Metode pemenuhan": payload.metode_pemenuhan,
            "Jenis kontrak": payload.jenis_kontrak,
            "Risiko CSMS": payload.resiko_csms,
        }
        missing_fields = [name for name, value in optional_fields.items()
                          if not value or not str(value).strip()]

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
        contract_id = None
        contract_archive_warning = None
        try:
            rks_artifact_id = payload.rks_artifact_id
            if rks_artifact_id:
                from tools.rks.service import artifact_file
                artifact_file(rks_artifact_id, "docx")
            contract_id = ContractArchive().save(
                project_name=payload.nama_pengadaan,
                tender_filename=filename,
                tender_sha256=hashlib.sha256(Path(file_path).read_bytes()).hexdigest(),
                contract_docx=render_contract_to_docx_bytes(draft),
                rks_artifact_id=rks_artifact_id,
            )
        except Exception as exc:
            contract_archive_warning = f"Tender berhasil dibuat, tetapi rancangan kontrak belum tersimpan di gudang: {exc}"

        return {
            "status": "success",
            "message": ("Draft Dokumen Tender berhasil dibuat dengan placeholder."
                        if missing_fields else "Dokumen Tender berhasil dibuat!"),
            "filename": filename,
            "filepath": file_path,
            "download_url": f"/api/tender/download/{filename}",
            "contract_id": contract_id,
            "contract_archive_warning": contract_archive_warning,
            "details": {
                "nama_pengadaan": payload.nama_pengadaan,
                "nomor_tender": payload.nomor_tender,
                "resiko_csms": payload.resiko_csms,
                "missing_fields": missing_fields,
                "kriteria_teknis_count": len(draft.get("lampiran_2a_evaluasi_teknis", [])) if draft else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


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

