"""RKS endpoints shared by Streamlit and future React integration."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from tools.rks.catalog import public_source
from tools.rks.service import create_document, get_document, artifact_file, search_sources

router = APIRouter(prefix="/api/rks", tags=["RKS"])


class RKSRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    source_id: str = Field(default="", max_length=24, pattern=r"^(?:[0-9a-f]{24})?$")


@router.get("/sources")
def sources(query: str = Query(min_length=3, max_length=500)):
    return {"sources": [public_source(x) for x in search_sources(query)]}


@router.post("/generate")
def generate(payload: RKSRequest):
    return create_document(payload.query, payload.source_id)


@router.get("/{artifact_id}")
def detail(artifact_id: str):
    try:
        return get_document(artifact_id)
    except (OSError, ValueError):
        raise HTTPException(404, "Dokumen RKS tidak ditemukan.")


def _file(artifact_id: str, kind: str):
    try:
        path = artifact_file(artifact_id, kind)
    except (OSError, ValueError):
        raise HTTPException(404, "File RKS tidak tersedia atau telah berubah.")
    return FileResponse(path, media_type="application/pdf" if kind == "pdf" else
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        filename=f"RKS-{artifact_id[:8]}.{kind}",
                        content_disposition_type="inline" if kind == "pdf" else "attachment")


@router.get("/{artifact_id}/document.docx")
def document(artifact_id: str):
    return _file(artifact_id, "docx")


@router.get("/{artifact_id}/preview.pdf")
def preview(artifact_id: str):
    return _file(artifact_id, "pdf")
