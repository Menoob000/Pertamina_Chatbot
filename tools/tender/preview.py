"""Prepare a page preview and its matching finalized tender DOCX."""
from __future__ import annotations

import hashlib
from pathlib import Path

from tools.rks.preview import finalize_and_preview


PREVIEW_DIR = Path(__file__).resolve().parents[2] / "output" / "tender_previews"


def preview_key(docx_data: bytes) -> str:
    return hashlib.sha256(docx_data).hexdigest()


def prepare_tender_preview(docx_data: bytes, *, output_dir: Path = PREVIEW_DIR) -> dict:
    """Cache a rendered copy by source bytes; never modify the generated file."""
    key = preview_key(docx_data)
    folder = output_dir / key
    docx_path = folder / "Tender.docx"
    pdf_path = folder / "Tender.pdf"
    complete = folder / "complete"
    if complete.is_file() and docx_path.is_file() and pdf_path.is_file() and pdf_path.stat().st_size > 0:
        return {"available": True, "docx": docx_path, "pdf": pdf_path, "key": key}

    folder.mkdir(parents=True, exist_ok=True)
    docx_path.write_bytes(docx_data)
    result = finalize_and_preview(docx_path, heading_count=0)
    if not result.get("available") or not pdf_path.is_file() or not pdf_path.stat().st_size:
        return {"available": False, "message": result.get("message") or "Preview PDF gagal dibuat.",
                "key": key}
    complete.write_text(key, encoding="ascii")
    return {"available": True, "docx": docx_path, "pdf": pdf_path, "key": key}
