"""Local knowledge-base source selection. No model rewrites source content."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
JOBS = {"overhaul", "restorasi", "pembangunan", "survey", "inspeksi"}
STOP = {"buatkan", "buat", "saya", "dokumen", "rks", "untuk", "pekerjaan", "tolong", "dan", "di", "yang"}


def tokens(text: str) -> set[str]:
    text = text.lower().replace("tanki", "tangki").replace("survei", "survey")
    return set(re.findall(r"[a-z0-9]+", text)) - STOP


def list_sources(data_dir: Path = DATA_DIR) -> list[dict]:
    sources = []
    for path in sorted(data_dir.glob("*.pdf")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            with pymupdf.open(path) as pdf:
                text = "\n".join(pdf[i].get_text() for i in range(min(3, len(pdf))))
                sources.append({
                    "source_id": digest[:24], "sha256": digest, "filename": path.name,
                    "pages": len(pdf), "search_text": text, "path": str(path.resolve()),
                })
        except Exception:
            # Unreadable files cannot become a valid candidate.
            continue
    return sources


def search_sources(query: str, data_dir: Path = DATA_DIR) -> list[dict]:
    wanted = tokens(query)
    if not wanted:
        return []
    wanted_jobs = wanted & JOBS
    identifiers = {x for x in wanted if re.search(r"\d", x)}
    results = []
    for source in list_sources(data_dir):
        name_words = tokens(source["filename"])
        all_words = name_words | tokens(source["search_text"])
        # A work category in a filename is a stronger signal than a passing
        # mention of that category in a specification.
        if wanted_jobs and not wanted_jobs.intersection(name_words):
            continue
        if identifiers and not identifiers.issubset(all_words):
            continue
        overlap = wanted & all_words
        if not overlap or not (wanted & name_words):
            continue
        score = sum(5 if x in name_words else 1 for x in overlap)
        results.append({**source, "score": score, "matched_terms": sorted(overlap)})
    return sorted(results, key=lambda x: (-x["score"], x["filename"]))


def public_source(source: dict) -> dict:
    return {k: v for k, v in source.items() if k not in {"path", "search_text"}}
