"""Process-local thread, document, and download registry for the first integration stage."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, RLock
from uuid import uuid4

from backend.errors import ApiError
from backend.schemas import ChatMessage, DocumentDetail, ThreadDetail, ThreadSummary


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ThreadRecord:
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = field(default_factory=list)
    document_id: str | None = None
    run_lock: Lock = field(default_factory=Lock, repr=False)


@dataclass
class DocumentRecord:
    detail: DocumentDetail
    thread_id: str
    source_pdf: Path | None


@dataclass
class FileRecord:
    id: str
    filename: str
    path: Path
    document_id: str


class MemoryStore:
    """Single-process state; persistence is deferred to the Docker phase."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._threads: dict[str, ThreadRecord] = {}
        self._documents: dict[str, DocumentRecord] = {}
        self._files: dict[str, FileRecord] = {}

    def create_thread(self, title: str) -> ThreadSummary:
        timestamp = now()
        thread = ThreadRecord(str(uuid4()), title.strip(), timestamp, timestamp)
        with self._lock:
            self._threads[thread.id] = thread
            return self._summary(thread)

    def list_threads(self) -> list[ThreadSummary]:
        with self._lock:
            records = sorted(self._threads.values(), key=lambda item: item.updated_at, reverse=True)
            return [self._summary(item) for item in records]

    def get_thread_record(self, thread_id: str) -> ThreadRecord:
        with self._lock:
            thread = self._threads.get(thread_id)
        if thread is None:
            raise ApiError(404, "thread_not_found", "Percakapan tidak ditemukan.")
        return thread

    def get_thread(self, thread_id: str) -> ThreadDetail:
        with self._lock:
            thread = self.get_thread_record(thread_id)
            return ThreadDetail(**self._summary(thread).model_dump(), messages=list(thread.messages))

    def rename_thread(self, thread_id: str, title: str) -> ThreadSummary:
        with self._lock:
            thread = self.get_thread_record(thread_id)
            thread.title = title.strip()
            thread.updated_at = now()
            return self._summary(thread)

    def delete_thread(self, thread_id: str) -> None:
        with self._lock:
            self.get_thread_record(thread_id)
            del self._threads[thread_id]
            document_ids = [key for key, item in self._documents.items() if item.thread_id == thread_id]
            for document_id in document_ids:
                del self._documents[document_id]
            for file_id, item in list(self._files.items()):
                if item.document_id in document_ids:
                    del self._files[file_id]

    def add_message(self, thread_id: str, role: str, content: str, document_id: str | None = None) -> ChatMessage:
        message = ChatMessage(id=str(uuid4()), role=role, content=content, created_at=now(), document_id=document_id)
        with self._lock:
            thread = self.get_thread_record(thread_id)
            thread.messages.append(message)
            thread.updated_at = message.created_at
            if role == "user" and len(thread.messages) == 1 and thread.title == "Percakapan baru":
                thread.title = content[:60].strip() + ("…" if len(content) > 60 else "")
        return message

    def add_document(self, thread_id: str, detail: DocumentDetail, source_pdf: Path | None) -> str:
        with self._lock:
            thread = self.get_thread_record(thread_id)
            self._documents[detail.id] = DocumentRecord(detail, thread_id, source_pdf)
            thread.document_id = detail.id
            thread.updated_at = now()
        return detail.id

    def get_document(self, document_id: str) -> DocumentRecord:
        with self._lock:
            document = self._documents.get(document_id)
        if document is None:
            raise ApiError(404, "document_not_found", "Dokumen tidak ditemukan.")
        return document

    def add_file(self, document_id: str, path: Path) -> FileRecord:
        record = FileRecord(str(uuid4()), path.name, path, document_id)
        with self._lock:
            self.get_document(document_id)
            self._files[record.id] = record
        return record

    def get_file(self, file_id: str) -> FileRecord:
        with self._lock:
            record = self._files.get(file_id)
        if record is None:
            raise ApiError(404, "file_not_found", "File unduhan tidak ditemukan.")
        return record

    @staticmethod
    def _summary(thread: ThreadRecord) -> ThreadSummary:
        return ThreadSummary(
            id=thread.id,
            title=thread.title,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            message_count=len(thread.messages),
            document_id=thread.document_id,
        )


store = MemoryStore()
