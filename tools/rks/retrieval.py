"""Page-aware hybrid evidence retrieval for RKS; never generates missing facts."""
from __future__ import annotations

import logging
import hashlib
import re
import os
import socket
from pathlib import Path

import pymupdf

import config
from .catalog import tokens
from .extraction import heading_level
from rag.source_reader import source_chunks


def _chunks(text: str, size: int, overlap: int):
    size = max(100, size)
    overlap = min(max(0, overlap), size - 1)
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        yield text[start:end]
        if end == len(text):
            break
        start = end - overlap


def _metadata(source: dict, page: int | None = None) -> dict:
    filename = source["filename"]
    year = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", filename)
    version = re.search(r"\b(?:rev(?:isi)?|versi|v)[ ._-]*(\d+)\b", filename, re.I)
    return {"source_id": source["source_id"], "filename": filename, "page": page,
            "source_sha256": source.get("sha256"), "file_format": source.get("file_format", Path(source["filename"]).suffix.lstrip(".")),
            "document_type": "RKS" if re.search(r"\bRKS\b", filename, re.I) else None,
            "year": int(year.group()) if year else None,
            "version": version.group(1) if version else None}


def _allowed(metadata: dict, filters: dict) -> bool:
    return all(metadata.get(key) == value for key, value in filters.items() if value is not None)


def search_evidence(query: str, sources: list[dict], *, filters: dict | None = None,
                    top_k: int | None = None, score_threshold: float | None = None,
                    semantic_store=None, use_semantic: bool | None = None) -> dict:
    """Return ranked chunks with page/source identity; semantic failure degrades to keyword.

    `semantic_store` may be injected in tests; otherwise the existing PGVector
    collection is used lazily. Scores are local ranking signals, not probabilities.
    """
    filters = {"document_type": "RKS", **(filters or {})}
    top_k = max(1, top_k if top_k is not None else config.RKS_SEARCH_TOP_K)
    threshold = score_threshold if score_threshold is not None else config.RKS_SEARCH_SCORE_THRESHOLD
    if not 0 <= threshold <= 1:
        raise ValueError("score_threshold harus di antara 0 dan 1")
    if not 0 <= config.RKS_SEARCH_KEYWORD_WEIGHT <= 1 or not 0 <= config.RKS_SEARCH_SEMANTIC_WEIGHT <= 1:
        raise ValueError("Bobot pencarian harus di antara 0 dan 1")
    wanted = tokens(query)
    if not wanted:
        return {"status": "sumber tidak ditemukan", "results": [], "semantic_status": "tidak dijalankan"}
    source_filters = {k: v for k, v in filters.items() if k != "section"}
    eligible = [s for s in sources if _allowed(_metadata(s), source_filters)]
    results: dict[tuple[str, int | None, str], dict] = {}
    for source in eligible:
        try:
            for chunk, block_meta in source_chunks(source):
                page_meta = {**_metadata(source, block_meta.get("page")), **block_meta}
                if not _allowed(page_meta, filters):
                    continue
                found = wanted & tokens(chunk)
                if not found:
                    continue
                score = len(found) / len(wanted)
                key = (source["source_id"], block_meta["location"], hashlib.sha256(chunk.encode()).hexdigest())
                results[key] = {**page_meta, "content": chunk,
                                "keyword_score": round(score, 4), "semantic_score": None,
                                "matched_terms": sorted(found)}
        except (OSError, ValueError, RuntimeError):
            logging.getLogger(__name__).exception("Cannot read RKS source %s", source["filename"])
    semantic_status = "dinonaktifkan"
    if (config.RKS_SEARCH_SEMANTIC_ENABLED if use_semantic is None else use_semantic) and eligible:
        try:
            if semantic_store is None:
                # Check the local PGVector service before loading a large model.
                host = os.getenv("PGVECTOR_HOST", "127.0.0.1")
                port = int(os.getenv("PGVECTOR_PORT", "5432"))
                with socket.create_connection((host, port), timeout=0.5):
                    pass
                from rag.vector_store import _get_vector_store
                semantic_store = _get_vector_store()
            raw = semantic_store.similarity_search_with_relevance_scores(query, k=max(top_k * 3, 12))
            by_name = {s["filename"].casefold(): s for s in eligible}
            for doc, score in raw:
                source = by_name.get(Path(doc.metadata.get("file_name", "")).name.casefold())
                if source is None:
                    continue
                indexed_hash = doc.metadata.get("source_sha256")
                if indexed_hash and indexed_hash != source.get("sha256"):
                    continue
                if source.get("file_format") == "docx" and not indexed_hash:
                    continue
                page = doc.metadata.get("page")
                page = int(page) if isinstance(page, int) or str(page).isdigit() else None
                meta = {**_metadata(source, page), "section": doc.metadata.get("section"),
                        "location": doc.metadata.get("location") or (f"halaman {page}" if page else None)}
                if not _allowed(meta, filters):
                    continue
                content = doc.page_content or ""
                key = (source["source_id"], meta["location"], hashlib.sha256(content.encode()).hexdigest())
                matched = wanted & tokens(content)
                item = results.setdefault(key, {**meta, "content": content,
                                                 "keyword_score": round(len(matched) / len(wanted), 4),
                                                 "matched_terms": sorted(matched)})
                item["semantic_score"] = round(max(0.0, min(1.0, float(score))), 4)
            semantic_status = "tersedia"
        except Exception as exc:
            logging.getLogger(__name__).warning("Semantic RKS search unavailable: %s", exc)
            semantic_status = "tidak tersedia"
    ranked = []
    for item in results.values():
        semantic = item.get("semantic_score")
        keyword = item["keyword_score"]
        if semantic is None:
            combined = keyword
        else:
            total = config.RKS_SEARCH_KEYWORD_WEIGHT + config.RKS_SEARCH_SEMANTIC_WEIGHT
            combined = (keyword * config.RKS_SEARCH_KEYWORD_WEIGHT + semantic * config.RKS_SEARCH_SEMANTIC_WEIGHT) / (total or 1)
        item["score"] = round(combined, 4)
        if item["score"] >= threshold:
            ranked.append(item)
    ranked.sort(key=lambda x: (-x["score"], -x["keyword_score"], x["filename"], x["page"] or 0))
    return {"status": "ditemukan" if ranked else "sumber tidak ditemukan",
            "results": ranked[:top_k], "semantic_status": semantic_status}
