"""Local knowledge-base source selection. No model rewrites source content."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pymupdf
import config
from rag.source_reader import read_source

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
JOBS = {"overhaul", "restorasi", "pembangunan", "survey", "inspeksi"}
STOP = {"buatkan", "buat", "saya", "dokumen", "rks", "untuk", "pekerjaan", "tolong", "dan", "di", "yang"}


def tokens(text: str) -> set[str]:
    text = text.lower().replace("tanki", "tangki").replace("survei", "survey")
    return set(re.findall(r"[a-z0-9]+", text)) - STOP


def list_sources(data_dir: Path = DATA_DIR) -> list[dict]:
    sources = []
    for path in sorted(Path(data_dir).iterdir()) if Path(data_dir).is_dir() else []:
        if path.suffix.lower() not in {".pdf", ".docx"} or path.name.startswith("~$"):
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            structure = read_source(path)
            text = "\n".join(block["text"] for block in structure["blocks"])[:18000]
            if not text.strip() and structure["format"] == "docx":
                continue
            sources.append({
                "source_id": digest[:24], "sha256": digest, "filename": path.name,
                "pages": structure["pages"], "file_format": structure["format"],
                "search_text": text, "path": str(path.resolve()),
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
        coverage = len(overlap) / len(wanted)
        if coverage >= config.RKS_SEARCH_SCORE_THRESHOLD:
            results.append({**source, "score": score, "match_score": round(coverage, 4),
                            "matched_terms": sorted(overlap)})
    return sorted(results, key=lambda x: (-x["match_score"], -x["score"], x["filename"]))[:max(1, config.RKS_SEARCH_TOP_K)]


def public_source(source: dict) -> dict:
    return {k: v for k, v in source.items() if k not in {"path", "search_text"}}
