"""Public API shapes shared by the backend routes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ThreadCreate(BaseModel):
    title: str = Field(default="Percakapan baru", min_length=1, max_length=120)


class ThreadUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ThreadSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    document_id: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    document_id: str | None = None


class ToolEvent(BaseModel):
    name: str
    status: Literal["invoked", "completed"]


class ThreadDetail(ThreadSummary):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    thread_id: str
    message: ChatMessage
    tool_events: list[ToolEvent]
    document_id: str | None = None


class DocumentChapter(BaseModel):
    number: str
    title: str
    sections: list[str]


class DocumentDetail(BaseModel):
    id: str
    title: str
    source_file: str | None = None
    content: str
    document_number: str | None = None
    csms_category: str | None = None
    chapters: list[DocumentChapter]
    can_convert: bool
    pdf_url: str | None = None


class ConversionResponse(BaseModel):
    file_id: str
    filename: str
    download_url: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
