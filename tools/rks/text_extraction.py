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
    """Rebuild visual rows from PDF text fragments in reading order.

    A single source line may be represented by several text objects with tiny
    y-coordinate differences.  This is especially common for inline party
    names such as KONTRAKTOR/PERUSAHAAN.  We group those fragments first and
    use a tab only for a genuinely wide column gap.
    """
    bands: list[list[dict]] = []
    for line in sorted(lines, key=lambda item: ((item["bbox"][1] + item["bbox"][3]) / 2, item["bbox"][0])):
        center = (line["bbox"][1] + line["bbox"][3]) / 2
        if bands:
            band_center = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in bands[-1]) / len(bands[-1])
            if abs(center - band_center) <= 5:
                bands[-1].append(line)
                continue
        bands.append([line])

    rows = []
    for band in bands:
        fragments = sorted(band, key=lambda item: item["bbox"][0])
        row = dict(fragments[0])
        for fragment in fragments[1:]:
            gap = fragment["bbox"][0] - row["bbox"][2]
            row["text"] += ("\t" if gap > 115 else " ") + fragment["text"]
            row["bbox"][2] = max(row["bbox"][2], fragment["bbox"][2])
            row["bbox"][3] = max(row["bbox"][3], fragment["bbox"][3])
            row["bold"] = row["bold"] and fragment["bold"]
            row["damaged"] |= fragment["damaged"]
        rows.append(row)
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


def _tidy_table_cell(text: str) -> str:
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _restore_inline_party_names(text)


def _reconstruct_horizontal_table(page, found) -> list[list[str]]:
    """Recover three-column tables that have horizontal rules only.

    Several RKS PDFs draw row rules but omit vertical rules. PyMuPDF therefore
    returns one wide column even though header text establishes Deliverables,
    Evidence, and Batas Waktu as distinct columns.
    """
    rect = pymupdf.Rect(found.bbox)
    if rect.width < 300:
        return []
    words = page.get_text("words", clip=rect)
    if not words:
        return []

    visual_lines: list[list[tuple]] = []
    for word in sorted(words, key=lambda item: ((item[1] + item[3]) / 2, item[0])):
        center = (word[1] + word[3]) / 2
        if visual_lines:
            previous_center = sum((item[1] + item[3]) / 2 for item in visual_lines[-1]) / len(visual_lines[-1])
            if abs(center - previous_center) <= 3:
                visual_lines[-1].append(word)
                continue
        visual_lines.append([word])
    if len(visual_lines) < 3:
        return []

    # These ratios match the stable three-column RKS layout and are applied
    # only after a horizontal-rule table has already been found.
    edges = (rect.x0, rect.x0 + rect.width * .30, rect.x0 + rect.width * .71, rect.x1)

    def split_columns(line):
        cells = [[] for _ in range(3)]
        for word in sorted(line, key=lambda item: item[0]):
            center = (word[0] + word[2]) / 2
            column = 0 if center < edges[1] else 1 if center < edges[2] else 2
            cells[column].append(word[4])
        return [_tidy_table_cell(" ".join(cell)) for cell in cells]

    split_lines = [split_columns(line) for line in visual_lines]
    header = split_lines[0]
    if sum(bool(cell) for cell in header) < 3:
        return []

    rows = [header]
    current = ["", "", ""]
    last_center = (visual_lines[1][0][1] + visual_lines[1][0][3]) / 2
    for line, cells in zip(visual_lines[1:], split_lines[1:]):
        center = sum((word[1] + word[3]) / 2 for word in line) / len(line)
        # A large blank vertical gap denotes the next table record. Within a
        # record, one cell may wrap over several visual source lines.
        if center - last_center > 21 and any(current):
            rows.append([_tidy_table_cell(cell) for cell in current])
            current = ["", "", ""]
        for index, cell in enumerate(cells):
            if cell:
                current[index] = f"{current[index]} {cell}".strip()
        last_center = center
    if any(current):
        rows.append([_tidy_table_cell(cell) for cell in current])
    return rows if len(rows) >= 2 else []


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
        "PARAF / TANDA TANGAN", "PARAF/TANDA TANGAN", "DISETUJUI OLEH",
        "DIPERIKSA OLEH", "DIBUAT OLEH",
    }


def _restore_inline_party_names(text: str) -> str:
    """Restore spaces where a PDF joins a party-name overlay to nearby text."""
    return re.sub(r"(?<=[a-z])(?=(?:KONTRAKTOR|PERUSAHAAN|PENYEDIA)\b)", " ", text)


def _list_kind(text: str, number_depth: int) -> str:
    if number_depth:
        return "number"
    if re.match(r"^\d+[.)]\s+", text):
        return "ordinal"
    if re.match(r"^[a-z]\.?\s+", text):
        return "alpha"
    if re.match(r"^[ivxlcdm]+\.\s+", text, re.I):
        return "roman"
    if re.match(r"^(?:[-•*]|\([a-z]\))\s+", text):
        return "bullet"
    return ""


def extract_text_document(source: dict, assets: Path | None = None) -> dict:
    if Path(source["path"]).suffix.lower() == ".docx":
        from rag.source_reader import read_source
        structure = read_source(source["path"])
        elements = structure["blocks"]
        issues = [{"page": None, "message": message} for message in structure["issues"]]
        return {"source": {k: v for k, v in source.items() if k != "search_text"},
                "pages": [{"page": None, "source_text": "\n".join(e["text"] for e in elements),
                           "elements": elements, "width": 595, "height": 842}],
                "issues": issues, "heading_count": sum(e["kind"] == "heading" for e in elements),
                "auxiliary": structure["auxiliary"], "source_image_count": structure["image_count"],
                "mode": "docx_structure", "cover_logo": False,
                "status": "perlu pemeriksaan" if issues else "lengkap"}
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
                    value = _restore_inline_party_names(line["text"])
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
