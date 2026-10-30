"""FastAPI entry point. Run from the repository root: uv run uvicorn backend.app:app --reload."""

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.errors import ApiError
from backend.schemas import (
    ChatRequest, ChatResponse, ConversionResponse, DocumentDetail, HealthResponse,
    ThreadCreate, ThreadDetail, ThreadSummary, ThreadUpdate,
)
from backend.services import (
    DATA_DIR, OUTPUT_DIR, AgentBridge, DocumentBridge, agent_bridge, document_bridge,
)
from backend.store import MemoryStore, store


def get_store() -> MemoryStore:
    return store


def get_agent_bridge() -> AgentBridge:
    return agent_bridge


def get_document_bridge() -> DocumentBridge:
    return document_bridge


def create_app() -> FastAPI:
    application = FastAPI(title="Pertamina Integration API", version="0.1.0")
    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @application.exception_handler(ApiError)
    async def handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message}},
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, _error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": "Data permintaan tidak valid."}},
        )

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @application.post("/api/threads", response_model=ThreadSummary, status_code=201)
    def create_thread(body: ThreadCreate, state: MemoryStore = Depends(get_store)) -> ThreadSummary:
        if not body.title.strip():
            raise ApiError(422, "invalid_title", "Judul percakapan tidak boleh kosong.")
        return state.create_thread(body.title)

    @application.get("/api/threads", response_model=list[ThreadSummary])
    def list_threads(state: MemoryStore = Depends(get_store)) -> list[ThreadSummary]:
        return state.list_threads()

    @application.get("/api/threads/{thread_id}", response_model=ThreadDetail)
    def get_thread(thread_id: str, state: MemoryStore = Depends(get_store)) -> ThreadDetail:
        return state.get_thread(thread_id)

    @application.patch("/api/threads/{thread_id}", response_model=ThreadSummary)
    def rename_thread(thread_id: str, body: ThreadUpdate, state: MemoryStore = Depends(get_store)) -> ThreadSummary:
        if not body.title.strip():
            raise ApiError(422, "invalid_title", "Judul percakapan tidak boleh kosong.")
        return state.rename_thread(thread_id, body.title)

    @application.delete("/api/threads/{thread_id}", status_code=204)
    def delete_thread(thread_id: str, state: MemoryStore = Depends(get_store)) -> None:
        state.delete_thread(thread_id)

    @application.post("/api/threads/{thread_id}/messages", response_model=ChatResponse)
    def send_message(
        thread_id: str,
        body: ChatRequest,
        state: MemoryStore = Depends(get_store),
        agent: AgentBridge = Depends(get_agent_bridge),
        documents: DocumentBridge = Depends(get_document_bridge),
    ) -> ChatResponse:
        prompt = body.message.strip()
        if not prompt:
            raise ApiError(422, "invalid_message", "Pesan tidak boleh kosong.")
        thread = state.get_thread_record(thread_id)
        with thread.run_lock:
            state.add_message(thread_id, "user", prompt)
            answer, tool_events, payload = agent.run(thread_id, prompt)
            document_id = None
            if payload:
                detail, source_pdf = documents.from_agent_payload(payload)
                document_id = state.add_document(thread_id, detail, source_pdf)
            message = state.add_message(thread_id, "assistant", answer, document_id)
        return ChatResponse(
            thread_id=thread_id,
            message=message,
            tool_events=tool_events,
            document_id=document_id,
        )

    @application.get("/api/documents/{document_id}", response_model=DocumentDetail)
    def get_document(document_id: str, state: MemoryStore = Depends(get_store)) -> DocumentDetail:
        return state.get_document(document_id).detail

    @application.get("/api/documents/{document_id}/pdf")
    def view_source_pdf(document_id: str, state: MemoryStore = Depends(get_store)) -> FileResponse:
        source = state.get_document(document_id).source_pdf
        if source is None or not source.is_file() or not source.resolve().is_relative_to(DATA_DIR.resolve()):
            raise ApiError(404, "source_pdf_not_found", "PDF sumber tidak ditemukan.")
        return FileResponse(source, media_type="application/pdf", content_disposition_type="inline")

    @application.post("/api/documents/{document_id}/conversions", response_model=ConversionResponse, status_code=201)
    def convert_document(
        document_id: str,
        state: MemoryStore = Depends(get_store),
        documents: DocumentBridge = Depends(get_document_bridge),
    ) -> ConversionResponse:
        source = state.get_document(document_id).source_pdf
        output = documents.convert(source)
        record = state.add_file(document_id, output)
        return ConversionResponse(
            file_id=record.id,
            filename=record.filename,
            download_url=f"/api/files/{record.id}/download",
        )

    @application.get("/api/files/{file_id}/download")
    def download_file(file_id: str, state: MemoryStore = Depends(get_store)) -> FileResponse:
        record = state.get_file(file_id)
        output = Path(record.path).resolve()
        if not output.is_relative_to(OUTPUT_DIR.resolve()) or output.suffix.lower() != ".docx":
            raise ApiError(404, "file_not_found", "File unduhan tidak ditemukan.")
        if not output.is_file():
            raise ApiError(404, "file_not_found", "File unduhan tidak ditemukan.")
        return FileResponse(output, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=record.filename)

    return application


app = create_app()
