"""Editable text extraction for RKS PDFs with a searchable text layer.

Graphics are intentionally omitted. Unreadable glyphs become explicit markers;
the result is never presented as a lossless copy of the source PDF.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .extraction import heading_level


def _clean(text: str) -> tuple[str, bool]:
    damaged = any(c == "\ufffd" or c == "\x00" or 0xE000 <= ord(c) <= 0xF8FF for c in text)
    text = "".join("[simbol tidak terbaca]" if c == "\x00" or c == "\ufffd" or 0xE000 <= ord(c) <= 0xF8FF
                   else c for c in text)
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " ")).strip(), damaged


def _lines(page) -> list[dict]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            spans = line["spans"]
            if not spans:
                continue
            text, damaged = _clean("".join(s["text"] for s in spans))
            if text:
                lines.append({"text": text, "bbox": list(line["bbox"]),
                              "bold": any(s["flags"] & 16 for s in spans),
                              "damaged": damaged})
    return sorted(lines, key=lambda x: (round(x["bbox"][1] / 3), x["bbox"][0]))


def _source_footer(line: dict, height: float) -> bool:
    text = line["text"]
    return (line["bbox"][1] > height * .84 and
            (re.match(r"^(?:Page|Hal(?:aman)?)\s*\d+\b", text, re.I) or
             text.startswith("<") or text == ">" or
             text in {"PARAF/TANDA TANGAN", "KONTRAKTOR"}))


def _rows(lines: list[dict]) -> list[dict]:
    """Keep side-by-side cells on one editable row without changing literals."""
    rows = []
    for line in lines:
        if rows and abs(rows[-1]["bbox"][1] - line["bbox"][1]) < 3 and \
                line["bbox"][0] > rows[-1]["bbox"][2] - 3:
            row = rows[-1]
            row["text"] += "\t" + line["text"]
            row["bbox"][2] = max(row["bbox"][2], line["bbox"][2])
            row["bbox"][3] = max(row["bbox"][3], line["bbox"][3])
            row["bold"] = row["bold"] and line["bold"]
            row["damaged"] |= line["damaged"]
        else:
            rows.append(dict(line))
    return rows


def _merge_continuations(elements: list[dict]) -> list[dict]:
    merged = []
    item = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?\s|[a-zA-Z][.)]\s|[•*-]\s|\[simbol tidak terbaca\])")
    for element in elements:
        if (merged and element["kind"] == "paragraph" and
                merged[-1]["kind"] in {"paragraph", "heading"} and
                element.get("source_role") == "body" and merged[-1].get("source_role") == "body"):
            previous = merged[-1]
            gap = element["bbox"][1] - previous["bbox"][3]
            x_shift = abs(element["bbox"][0] - previous["bbox"][0])
            join_without_hyphen = _is_wrapped_word(previous["text"], element["text"], gap, x_shift)
            number_only = bool(re.fullmatch(r"\d+(?:\.\d+)+\.?", previous["text"].strip()))
            punctuation_only = bool(re.fullmatch(r"[.,;!?]+", element["text"].strip()))
            punctuation_overlay = (punctuation_only and
                                   previous["bbox"][0] <= element["bbox"][0] <= previous["bbox"][2] + 12 and
                                   element["bbox"][1] <= previous["bbox"][3] and
                                   element["bbox"][3] >= previous["bbox"][1])
            can_join = (gap <= 7 and x_shift <= 38 and "\t" not in previous["text"] and
                        "\t" not in element["text"] and not item.match(element["text"]) and
                        not element.get("value_line"))
            if join_without_hyphen:
                can_join = "\t" not in previous["text"] and "\t" not in element["text"]
            elif number_only:
                # A number on a line by itself is a visual wrap in the source,
                # not a complete paragraph. Keep its first sentence inline.
                can_join = gap <= 13 and x_shift <= 70 and "\t" not in element["text"]
            elif punctuation_only:
                # Some PDF text layers place a terminal punctuation mark in a
                # separate text object on the next visual line or overlaid on
                # the final source line rather than appended to its text run.
                can_join = ((gap <= 15 and x_shift <= 90) or punctuation_overlay) and \
                           "\t" not in previous["text"]
            if previous["kind"] == "heading":
                can_join &= element["text"].startswith("(") and len(previous["text"]) < 145
            else:
                can_join &= not previous["text"].rstrip().endswith((".", ":", ";"))
            if can_join:
                if join_without_hyphen:
                    previous["text"] = previous["text"].rstrip()[:-1] + element["text"].lstrip()
                elif punctuation_only:
                    previous["text"] = previous["text"].rstrip() + element["text"].strip()
                else:
                    previous["text"] += " " + element["text"]
                previous["bbox"][2] = max(previous["bbox"][2], element["bbox"][2])
                previous["bbox"][3] = element["bbox"][3]
                continue
        merged.append(element)
    return merged


def _is_wrapped_word(previous: str, current: str, gap: float, x_shift: float) -> bool:
    """Identify a PDF line-wrap hyphen without changing normal compound terms."""
    match = re.search(r"([A-Za-z]+)-\s*$", previous)
    if not match or not re.match(r"^[a-z]", current.lstrip()):
        return False
    if match.group(1).casefold() in {"anti", "multi", "non", "post", "pre", "semi", "sub", "well"}:
        return False
    return gap <= 11 and x_shift <= 60


def _inside(line: dict, rect) -> bool:
    x0, y0, x1, y1 = line["bbox"]
    return rect.x0 <= (x0 + x1) / 2 <= rect.x1 and rect.y0 <= (y0 + y1) / 2 <= rect.y1


def _clean_cell(value) -> str:
    value, _ = _clean(str(value or ""))
    return value


def _tables(page) -> list[dict]:
    """Extract ruled PDF tables as editable Word-table data and geometry."""
    try:
        detected = page.find_tables(strategy="lines_strict").tables
    except Exception:
        return []
    tables = []
    for found in detected:
        rows = [[_clean_cell(cell) for cell in row] for row in found.extract()]
        if len(rows) < 2 or not any(any(cell for cell in row) for row in rows):
            continue
        tables.append({"kind": "table", "rows": rows, "bbox": list(found.bbox),
                       "editable": True, "source_role": "table"})
    return tables


def _promote_tabular_rows(elements: list[dict]) -> list[dict]:
    """Preserve borderless, aligned PDF rows as Word tables when unambiguous.

    Some RKS sources use visually aligned columns without drawing table borders.
    A run of two or more rows with the same tab-separated geometry is safer to
    represent as a table than as unrelated paragraphs.
    """
    promoted, position = [], 0
    while position < len(elements):
        current = elements[position]
        cells = current.get("text", "").split("\t")
        is_tabular = current.get("kind") == "paragraph" and len(cells) >= 2
        if not is_tabular:
            promoted.append(current)
            position += 1
            continue

        group = [current]
        columns = len(cells)
        next_position = position + 1
        while next_position < len(elements):
            candidate = elements[next_position]
            candidate_cells = candidate.get("text", "").split("\t")
            if candidate.get("kind") != "paragraph" or len(candidate_cells) != columns:
                break
            group.append(candidate)
            next_position += 1

        if len(group) >= 2:
            promoted.append({
                "kind": "table",
                "rows": [item["text"].split("\t") for item in group],
                "bbox": [min(item["bbox"][0] for item in group),
                         min(item["bbox"][1] for item in group),
                         max(item["bbox"][2] for item in group),
                         max(item["bbox"][3] for item in group)],
                "editable": True,
                "source_role": "aligned_table",
            })
        else:
            promoted.extend(group)
        position = next_position
    return promoted


def _number_depth(text: str) -> int:
    match = re.match(r"^(\d+(?:\.\d+)+)\.?(?:\s+|$)", text)
    return len(match.group(1).split(".")) if match else 0


def _is_layout_label(text: str) -> bool:
    """Keep signature and approval labels out of surrounding prose."""
    label = re.sub(r"\s+", " ", text).strip().upper()
    return label in {
        "KONTRAKTOR", "PERUSAHAAN", "PENYEDIA", "PEMILIK PEKERJAAN",
        "PARAF", "TANDA TANGAN", "PARAF/TANDA TANGAN", "DISETUJUI OLEH",
        "DIPERIKSA OLEH", "DIBUAT OLEH",
    }


def _list_kind(text: str, number_depth: int) -> str:
    if number_depth:
        return "number"
    if re.match(r"^[a-z]\.?\s+", text):
        return "alpha"
    if re.match(r"^(?:[-•*]|\([a-z]\))\s+", text):
        return "bullet"
    return ""


def extract_text_document(source: dict, assets: Path | None = None) -> dict:
    pages, issues = [], []
    in_appendix = False
    with pymupdf.open(source["path"]) as pdf:
        for number, page in enumerate(pdf, 1):
            raw = page.get_text()
            record = {"page": number, "width": page.rect.width, "height": page.rect.height,
                      "source_text": raw, "elements": [], "issues": []}
            if re.search(r"DAFTAR\s+ISI", raw, re.I) and raw.count("...") > 2:
                record["replaced_toc"] = True
                pages.append(record)
                continue
            tables = [] if number == 1 else _tables(page)
            table_rects = [pymupdf.Rect(table["bbox"]) for table in tables]
            lines = [line for line in _lines(page)
                     if not any(_inside(line, rect) for rect in table_rects)]
            lines = [line for line in lines if not _source_footer(line, page.rect.height)]
            # The cover often contains a full-page image and an editable text
            # overlay. Use only its text, eliminating duplicate overlay labels.
            if number == 1:
                unique = []
                seen = set()
                for line in lines:
                    if line["bbox"][1] > page.rect.height * .84:
                        continue
                    key = re.sub(r"\s+", " ", line["text"]).casefold()
                    if key not in seen:
                        unique.append(line)
                        seen.add(key)
                lines = unique
                record["cover"] = True
            if not lines:
                record["issues"].append("Tidak ada lapisan teks yang dapat dipindahkan; konten grafis halaman ini memerlukan transkripsi manual.")
                record["elements"].append({"kind": "paragraph", "text": "[Konten halaman sumber tidak dapat dibaca sebagai teks]",
                                           "bbox": [0, 0, page.rect.width, 20], "source_role": "unreadable"})
            else:
                for line in _rows(lines):
                    value = line["text"]
                    if number == 1:
                        value = value.replace("RESIKOpekerjaan", "RESIKO pekerjaan").replace("\t", "    ")
                    level = heading_level(value, line["bold"]) if number > 1 else 0
                    if number > 1:
                        appendix_start = bool(re.match(r"^10\.?\s+LAMPIRAN\b", value, re.I))
                        if appendix_start:
                            in_appendix = True
                        if appendix_start or re.match(r"^LAMPIRAN\s+[A-Z](?:\b|\.)", value, re.I):
                            level = 1
                        elif in_appendix or level > 2:
                            level = 0
                        elif level == 1 and re.match(r"^\d+\s*\(", value):
                            level = 0
                        elif level == 2:
                            label = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", value)
                            if len(re.findall(r"[A-Za-z]{2,}", label)) < 2:
                                level = 0
                    role = "cover" if number == 1 else "layout_label" if _is_layout_label(value) else "body"
                    depth = _number_depth(value)
                    record["elements"].append({"kind": "heading" if level else "paragraph",
                                               "text": value, "level": level,
                                               "number_depth": depth,
                                               "list_kind": _list_kind(value, depth),
                                               "value_line": bool(re.match(r"^:\s*", value)),
                                               "bbox": line["bbox"], "source_role": role})
                if any(line["damaged"] for line in lines):
                    record["issues"].append("Ada simbol sumber yang tidak terbaca; ditulis sebagai [simbol tidak terbaca].")
            record["elements"].extend(tables)
            if number > 1:
                record["elements"] = _merge_continuations(record["elements"])
                record["elements"].sort(key=lambda element: (element["bbox"][1], element["bbox"][0]))
                record["elements"] = _promote_tabular_rows(record["elements"])
            if page.get_images() or page.get_drawings():
                record["issues"].append("Logo, centang, diagram, atau elemen grafis yang tidak memiliki teks perlu diperiksa pada PDF sumber.")
            pages.append(record)
            issues.extend({"page": number, "message": m} for m in record["issues"])
    headings = sum(e["kind"] == "heading" for page in pages for e in page["elements"])
    if not headings:
        issues.append({"page": None, "message": "Heading sumber belum terdeteksi; daftar isi otomatis kosong."})
    cover_logo = any("BIDDER" in element["text"].upper() or "RESIKO" in element["text"].upper() or
                     "RISIKO" in element["text"].upper() for element in pages[0]["elements"])
    return {"source": {k: v for k, v in source.items() if k != "search_text"},
            "pages": pages, "issues": issues, "heading_count": headings,
            "mode": "editable_layout", "cover_logo": cover_logo,
            "status": "perlu pemeriksaan" if issues else "lengkap"}
