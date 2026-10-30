"""Adapters around the existing root-level agent and document utilities."""

import ast
import json
import logging
import re
from pathlib import Path
from uuid import uuid4

from backend.errors import ApiError
from backend.schemas import DocumentChapter, DocumentDetail, ToolEvent


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


def require_project_cwd() -> None:
    if Path.cwd().resolve() != PROJECT_ROOT:
        raise ApiError(
            500,
            "wrong_working_directory",
            "Jalankan API dari root proyek agar folder data dan output ditemukan.",
        )


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    return str(content) if content is not None else ""


def _tool_payload(content: object) -> dict | None:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return None
    try:
        parsed = json.loads(content)
    except (ValueError, TypeError):
        try:
            parsed = ast.literal_eval(content)
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            return None
    return parsed if isinstance(parsed, dict) else None


class AgentBridge:
    def run(self, thread_id: str, prompt: str) -> tuple[str, list[ToolEvent], dict | None]:
        """Run one turn; imports are lazy so /api/health works without the RAG database."""
        require_project_cwd()
        try:
            from langchain_core.messages import HumanMessage
            from agent import app as agent_app

            events: list[ToolEvent] = []
            document_payload = None
            final_answer = ""
            config = {"configurable": {"thread_id": thread_id}}
            for update in agent_app.stream(
                {"messages": [HumanMessage(content=prompt)]},
                config=config,
                stream_mode="updates",
            ):
                for message in update.get("agent", {}).get("messages", []):
                    for call in getattr(message, "tool_calls", []) or []:
                        events.append(ToolEvent(name=call.get("name", "tool"), status="invoked"))
                    if getattr(message, "content", None):
                        final_answer = _message_text(message.content)
                for message in update.get("tools", {}).get("messages", []):
                    name = getattr(message, "name", None) or "tool"
                    events.append(ToolEvent(name=name, status="completed"))
                    if name in ("fetch_full_documents", "return_full_docs"):
                        parsed = _tool_payload(getattr(message, "content", None))
                        if parsed and not parsed.get("error") and parsed.get("full_docs"):
                            document_payload = parsed
            if not final_answer:
                raise ApiError(502, "empty_agent_response", "Agent tidak mengembalikan jawaban.")
            return final_answer, events, document_payload
        except ApiError:
            raise
        except Exception as exc:
            logger.exception("Agent request failed")
            raise ApiError(
                503,
                "agent_unavailable",
                "Agent atau layanan pendukung belum tersedia. Periksa konfigurasi backend.",
            ) from exc


class DocumentBridge:
    def from_agent_payload(self, payload: dict) -> tuple[DocumentDetail, Path | None]:
        """Build a viewer response without importing the Streamlit UI module."""
        require_project_cwd()
        content = str(payload.get("full_docs") or "")
        title = str(payload.get("title") or "Dokumen RKS")
        source_file = Path(str(payload.get("source_file") or "")).name or None
        if not content.strip():
            raise ApiError(422, "empty_document", "Isi dokumen tidak tersedia.")

        try:
            from tools.docx_exporter import parse_text_to_rks_data

            parsed = parse_text_to_rks_data(content, custom_title=title)
        except Exception:
            logger.exception("Could not parse document outline")
            parsed = {}

        chapters = [
            DocumentChapter(
                number=str(chapter.get("nomor") or ""),
                title=str(chapter.get("judul") or ""),
                sections=[str(section.get("judul") or "") for section in chapter.get("sub_bab", [])],
            )
            for chapter in parsed.get("bab", [])
            if isinstance(chapter, dict)
        ]
        pdf_path = self._find_source_pdf(source_file)
        document_id = str(uuid4())
        detail = DocumentDetail(
            id=document_id,
            title=title,
            source_file=source_file,
            content=content,
            document_number=parsed.get("metadata", {}).get("nomor_dokumen"),
            csms_category=parsed.get("cover_page", {}).get("resiko_csms"),
            chapters=chapters,
            can_convert=pdf_path is not None,
            pdf_url=f"/api/documents/{document_id}/pdf" if pdf_path else None,
        )
        return detail, pdf_path

    @staticmethod
    def _find_source_pdf(source_file: str | None) -> Path | None:
        if not source_file or not source_file.lower().endswith(".pdf"):
            return None
        candidate = DATA_DIR / source_file
        if candidate.is_file() and candidate.resolve().is_relative_to(DATA_DIR.resolve()):
            return candidate.resolve()
        for candidate in DATA_DIR.glob("*.pdf"):
            if candidate.name.casefold() == source_file.casefold():
                return candidate.resolve()
        return None

    def convert(self, source_pdf: Path | None) -> Path:
        require_project_cwd()
        if source_pdf is None or not source_pdf.is_file():
            raise ApiError(404, "source_pdf_not_found", "PDF sumber untuk dokumen ini tidak ditemukan.")
        if not source_pdf.resolve().is_relative_to(DATA_DIR.resolve()):
            raise ApiError(400, "invalid_source_pdf", "PDF sumber berada di luar folder data.")

        safe_stem = re.sub(r"[^\w -]+", "_", source_pdf.stem, flags=re.UNICODE).strip(" _")[:70] or "dokumen"
        output_name = f"{safe_stem}-{uuid4().hex[:10]}.docx"
        try:
            from tools.pdf_converter import convert_pdf_to_docx_layout

            output = Path(convert_pdf_to_docx_layout(str(source_pdf), output_filename=output_name)).resolve()
        except Exception as exc:
            logger.exception("PDF conversion failed")
            raise ApiError(502, "conversion_failed", "Konversi PDF ke DOCX gagal.") from exc
        if not output.is_relative_to(OUTPUT_DIR.resolve()) or output.suffix.lower() != ".docx":
            raise ApiError(502, "invalid_conversion_result", "Hasil konversi tidak valid.")
        return output


agent_bridge = AgentBridge()
document_bridge = DocumentBridge()
