"""Shared source blocks and chunks for PDF/DOCX ingestion and retrieval."""
from pathlib import Path
import re

import pymupdf
import config

from .docx_source import read_docx


def read_source(path) -> dict:
    path = Path(path)
    if path.suffix.lower() == ".docx":
        return {**read_docx(path), "format": "docx", "pages": None}
    if path.suffix.lower() != ".pdf":
        raise ValueError("Format sumber harus PDF atau DOCX.")
    blocks = []
    with pymupdf.open(path) as pdf:
        page_count = len(pdf)
        for number, page in enumerate(pdf, 1):
            text = page.get_text().replace("\x00", "").strip()
            if text:
                heading = next((line.strip() for line in text.splitlines()
                                if re.match(r"^(?:BAB\s+[IVXLC\d]+|\d+(?:\.\d+)*[.)]?\s+)", line.strip(), re.I)), None)
                blocks.append({"kind": "paragraph", "text": text, "page": number,
                               "section": heading, "location": f"halaman {number}"})
    return {"blocks": blocks, "format": "pdf", "pages": page_count,
            "issues": [] if blocks else ["PDF tidak memiliki teks; OCR belum tersedia."], "auxiliary": []}


def split_text(text, size, overlap):
    size = max(100, size)
    overlap = min(max(0, overlap), size - 1)
    start = 0
    while start < len(text):
        yield text[start:start + size]
        if start + size >= len(text):
            break
        start += size - overlap


def source_chunks(source: dict, structure: dict | None = None):
    structure = structure or read_source(source["path"])
    for block in structure["blocks"]:
        metadata = {"page": block.get("page"), "section": block.get("section"),
                    "location": block["location"], "element_type": block["kind"],
                    "file_format": structure["format"]}
        if block["kind"] == "table":
            rows = block["rows"]
            header_count = 1
            if len(rows) > 1 and sum(bool(cell.strip()) for cell in rows[0]) == 1:
                header_count = 2
            header = "\n".join(" | ".join(row) for row in rows[:header_count])
            for index, row in enumerate(rows[header_count:], header_count + 1):
                body_size = max(100, config.RKS_SEARCH_CHUNK_SIZE - len(header) - 1)
                for chunk in split_text(" | ".join(row), body_size, config.RKS_SEARCH_CHUNK_OVERLAP):
                    yield header + "\n" + chunk, {**metadata, "location": f"{block['location']}, baris {index}", "row": index}
            if len(rows) <= header_count:
                yield header, metadata
        else:
            for chunk in split_text(block["text"], config.RKS_SEARCH_CHUNK_SIZE, config.RKS_SEARCH_CHUNK_OVERLAP):
                yield chunk, metadata
