"""RKS endpoints shared by Streamlit and future React integration."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import config

from tools.rks.catalog import public_source
from tools.rks.service import (create_document, get_document, artifact_file,
                               search_sources, list_sources, list_documents)
from tools.rks.retrieval import search_evidence

router = APIRouter(prefix="/api/rks", tags=["RKS"])


class RKSRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    source_id: str = Field(default="", max_length=24, pattern=r"^(?:[0-9a-f]{24})?$")


class RKSSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    source_id: str = Field(default="", max_length=24, pattern=r"^(?:[0-9a-f]{24})?$")
    document_type: str = "RKS"
    year: int | None = None
    version: str | None = None
    section: str | None = None
    file_format: str | None = Field(default=None, pattern=r"^(pdf|docx)$")
    top_k: int = Field(default_factory=lambda: config.RKS_SEARCH_TOP_K, ge=1, le=50)
    score_threshold: float = Field(default_factory=lambda: config.RKS_SEARCH_SCORE_THRESHOLD, ge=0, le=1)


@router.get("/sources")
def sources(query: str = Query(min_length=3, max_length=500)):
    return {"sources": [public_source(x) for x in search_sources(query)]}


@router.post("/search")
def search(payload: RKSSearchRequest):
    catalog = list_sources()
    if payload.source_id:
        catalog = [s for s in catalog if s["source_id"] == payload.source_id]
    return search_evidence(payload.query, catalog,
                           filters={"document_type": payload.document_type,
                                    "year": payload.year, "version": payload.version,
                                    "section": payload.section, "file_format": payload.file_format},
                           top_k=payload.top_k, score_threshold=payload.score_threshold)


@router.post("/generate")
def generate(payload: RKSRequest):
    return create_document(payload.query, payload.source_id)


@router.get("/generated")
def generated(limit: int = Query(default=100, ge=1, le=500)):
    return {"documents": list_documents(limit=limit)}


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
