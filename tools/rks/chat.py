"""Select the current source/artifact from chat without confusing AI prose with a file."""
import ast
import json
from pathlib import Path

from .catalog import list_sources, search_sources


def payload(content):
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        content = "\n".join(x.get("text", "") for x in content if isinstance(x, dict))
    for decode in (json.loads, ast.literal_eval):
        try:
            result = decode(content)
            if isinstance(result, dict):
                return result
        except (ValueError, SyntaxError, TypeError):
            pass
    return {"full_docs": content if isinstance(content, str) else ""}


def source_path(filename, title):
    name = Path(filename or title).name.casefold()
    exact = next((s for s in list_sources() if s["filename"].casefold() == name), None)
    if exact:
        return exact["path"]
    matches = search_sources(title)
    if matches and (len(matches) == 1 or matches[0]["score"] - matches[1]["score"] >= 3):
        return matches[0]["path"]
    return None


def current_document(messages):
    # A model answer summarizing a tool result must not hide the actual file.
    for message in reversed(messages):
        if getattr(message, "type", None) != "tool":
            continue
        name = getattr(message, "name", "")
        if name == "create_rks_document":
            result = payload(message.content)
            source = result.get("source") or {}
            title = source.get("filename", "Pembuatan RKS")
            return {"source": name, "content": "", "title": title,
                    "source_file": source.get("filename", ""),
                    "pdf_path": source_path(title, title) if source else None,
                    "rks_result": result}
        if name in {"fetch_full_documents", "return_full_docs", "fetch_full_document"}:
            result = payload(message.content)
            text = result.get("full_docs", "")
            if isinstance(text, str) and text.strip():
                title = result.get("title") or result.get("source_file") or "RKS referensi"
                filename = result.get("source_file", "")
                return {"source": name, "content": text, "title": title,
                        "source_file": filename, "pdf_path": source_path(filename, title)}
    return None
