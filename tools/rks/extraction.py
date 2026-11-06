"""Geometry-aware extraction with explicit visual fallbacks and provenance."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

import pymupdf


def word_bag(text: str) -> Counter:
    return Counter(re.findall(r"\S+", text.replace("\x00", "")))


def heading_level(text: str, bold: bool = False) -> int:
    text = text.strip()
    if len(text) > 160 or "...." in text:
        return 0
    if re.match(r"^(BAB\s+[IVXLC\d]+|LAMPIRAN\s+[A-Z0-9]+)\b", text, re.I):
        return 1
    match = re.match(r"^(\d+(?:\.\d+){0,3})[.)]?\s+\S", text)
    if match and match[1].count(".") <= 2 and len(text.split()) <= 18 and (bold or text.isupper()):
        return min(3, match[1].count(".") + 1)
    return 0


def _inside(rect, outer) -> bool:
    return outer.contains(pymupdf.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2))


def _snapshot(page, assets: Path, name: str, rect=None) -> str:
    path = assets / f"{name}.png"
    page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6), clip=rect, alpha=False).save(path)
    return str(path)


def extract_document(source: dict, assets: Path) -> dict:
    assets.mkdir(parents=True, exist_ok=True)
    pages, issues = [], []
    with pymupdf.open(source["path"]) as pdf:
        for number, page in enumerate(pdf, 1):
            raw = page.get_text()
            bounds = page.rect
            record = {"page": number, "width": bounds.width, "height": bounds.height,
                      "source_text": raw, "elements": [], "issues": []}
            # The original TOC is a layout aid. Rebuild it using the actual
            # headings and pagination of the output, keeping its source text.
            if re.search(r"DAFTAR\s+ISI", raw, re.I) and (raw.count("...") > 2):
                record["replaced_toc"] = True
                pages.append(record)
                continue
            suspect = "\ufffd" in raw or any(ord(c) < 32 and c not in "\n\r\t" for c in raw)
            if len(raw.strip()) < 30 or suspect:
                try:
                    ocr = page.get_textpage_ocr(language="eng", dpi=200, full=True)
                    raw_ocr = page.get_text(textpage=ocr, sort=True)
                    record["ocr_text"] = raw_ocr
                    record["issues"].append("OCR memerlukan pemeriksaan terhadap halaman sumber.")
                except Exception:
                    record["issues"].append("Lapisan teks kosong/rusak; halaman dipertahankan sebagai gambar.")
                record["elements"] = [{"kind": "image", "path": _snapshot(page, assets, f"page-{number}"),
                                        "bbox": list(bounds), "text": raw, "page_fallback": True}]
                pages.append(record)
                issues.extend({"page": number, "message": m} for m in record["issues"])
                continue

            elements, occupied = [], []
            page_fallback = False
            try:
                tables = page.find_tables(strategy="lines_strict").tables
            except Exception as exc:
                tables = []
                record["issues"].append(f"Deteksi tabel tidak berhasil: {type(exc).__name__}.")
            for idx, table in enumerate(tables):
                rect = pymupdf.Rect(table.bbox)
                if rect.width < 40 or rect.height < 12:
                    continue
                rows = table.extract()
                original = page.get_textbox(rect)
                table_text = "\n".join(str(c or "") for row in rows for c in row)
                merged = any(c is None for row in rows for c in row)
                editable = bool(rows) and not merged and word_bag(original) == word_bag(table_text)
                element = {"kind": "table", "rows": rows, "bbox": list(rect), "text": original,
                           "editable": editable}
                if not editable:
                    element["path"] = _snapshot(page, assets, f"p{number}-table-{idx}", rect)
                    record["issues"].append(f"Tabel {idx + 1} dipertahankan sebagai gambar karena struktur sel belum pasti.")
                elements.append(element)
                occupied.append(rect)

            blocks = page.get_text("dict")["blocks"]
            # Images and non-table vector clusters are preserved as source
            # crops; no model redraws a diagram, formula or checkbox.
            visuals = [pymupdf.Rect(b["bbox"]) for b in blocks if b["type"] == 1]
            try:
                for rect in page.cluster_drawings():
                    if rect.width > 12 and rect.height > 12 and rect.get_area() < bounds.get_area() * .8:
                        visuals.append(rect)
            except Exception:
                record["issues"].append("Inventaris gambar vektor memerlukan pemeriksaan.")
            kept_visuals = []
            for idx, rect in enumerate(visuals):
                rect = rect & bounds
                if rect.is_empty or any(_inside(rect, r) for r in occupied + kept_visuals):
                    continue
                # A drawing crossing another element cannot be reconstructed
                # safely by independent crops: retain the whole source page.
                if any(rect.intersects(r) for r in occupied):
                    record["issues"].append("Elemen visual bertumpang tindih dengan tabel; halaman memerlukan pemeriksaan.")
                    page_fallback = True
                    continue
                # Include complete labels that extend slightly beyond drawing
                # strokes, otherwise table headers/diagram labels get clipped.
                for block in blocks:
                    if block["type"] == 0:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                sr = pymupdf.Rect(span["bbox"])
                                if _inside(sr, rect):
                                    rect |= sr
                rect = pymupdf.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2) & bounds
                kept_visuals.append(rect)
                elements.append({"kind": "image", "path": _snapshot(page, assets, f"p{number}-visual-{idx}", rect),
                                 "bbox": list(rect), "text": page.get_textbox(rect)})
            occupied.extend(kept_visuals)

            # Borderless tables and parallel text columns are not safe to
            # flatten into a paragraph. Keep their source page until a cell
            # mapping has been verified, rather than losing label/value links.
            line_rects = []
            for block in blocks:
                if block["type"] == 0:
                    for line in block["lines"]:
                        rect = pymupdf.Rect(line["bbox"])
                        if (rect.width > 70 and bounds.height * .05 < rect.y0 < bounds.height * .9
                                and not any(_inside(rect, r) for r in occupied)):
                            line_rects.append(rect)
            parallel_rows = set()
            for i, first in enumerate(line_rects):
                for second in line_rects[i + 1:]:
                    y_overlap = min(first.y1, second.y1) - max(first.y0, second.y0)
                    if y_overlap > min(first.height, second.height) * .5 and (
                        first.x1 + 8 < second.x0 or second.x1 + 8 < first.x0
                    ):
                        parallel_rows.add(round(first.y0 / 6))
            if len(parallel_rows) >= 3:
                page_fallback = True
                record["issues"].append("Tabel tanpa garis atau beberapa kolom belum dapat dipetakan dengan yakin; hubungan kolom dipertahankan pada gambar sumber.")

            for block in blocks:
                if block["type"] != 0:
                    continue
                lines = []
                for line in block["lines"]:
                    spans = [s for s in line["spans"] if not any(_inside(pymupdf.Rect(s["bbox"]), r) for r in occupied)]
                    if not spans:
                        continue
                    text = "".join(s["text"] for s in spans)
                    rect = pymupdf.Rect(spans[0]["bbox"])
                    for span in spans[1:]:
                        rect |= pymupdf.Rect(span["bbox"])
                    # Replace page numbering; preserve the rest of the source
                    # header/footer in the document and provenance inventory.
                    if re.fullmatch(r"\s*(?:Page|Hal\.?|Halaman)?\s*\d+\s*(?:(?:of|dari)\s*\d+)?\s*", text, re.I) and rect.y0 > bounds.height * .9:
                        record.setdefault("pagination", []).append(text)
                        continue
                    lines.append((text, rect, any(s["flags"] & 16 for s in spans)))
                if lines:
                    paragraph = []
                    def flush():
                        if paragraph:
                            rect = pymupdf.Rect(paragraph[0][1])
                            for _, box, _ in paragraph[1:]:
                                rect |= box
                            elements.append({"kind": "paragraph", "text": "\n".join(x[0] for x in paragraph),
                                             "bbox": list(rect), "source_role": "margin" if
                                             rect.height < 60 and (rect.y1 < bounds.height * .06 or
                                                                  rect.y0 > bounds.height * .9) else "body"})
                            paragraph.clear()
                    for text, rect, bold in lines:
                        level = heading_level(text, bold) if bounds.height * .05 < rect.y0 < bounds.height * .9 else 0
                        if level:
                            flush()
                            elements.append({"kind": "heading", "text": text, "level": level, "bbox": list(rect)})
                        else:
                            paragraph.append((text, rect, bold))
                    flush()

            elements.sort(key=lambda e: (e["bbox"][1], e["bbox"][0]))
            rendered_text = "\n".join(e.get("text", "") for e in elements)
            malformed = any((ord(c) < 32 and c not in "\r\n\t") or c == "\ufffd" or
                            0xE000 <= ord(c) <= 0xF8FF for c in rendered_text)
            if malformed:
                record["issues"].append("Karakter rusak atau glyph khusus dipertahankan melalui gambar halaman sumber.")
            expected = word_bag(raw)
            for text in record.get("pagination", []):
                expected.subtract(word_bag(text))
            missing = sum((+expected - word_bag(rendered_text)).values())
            coverage = 1 - missing / max(1, sum((+expected).values()))
            record["text_coverage"] = round(coverage, 4)
            if missing or page_fallback or malformed:
                # Never silently drop content when a crop or table mapping is
                # uncertain. Full-page fallback preserves everything visually.
                record["issues"].append("Halaman disertakan utuh sebagai gambar agar isi tidak hilang; tata letak asli masih terlihat.")
                elements = [{"kind": "image", "path": _snapshot(page, assets, f"page-{number}"),
                             "bbox": list(bounds), "text": raw, "page_fallback": True}]
            record["elements"] = elements
            pages.append(record)
            issues.extend({"page": number, "message": m} for m in record["issues"])
    headings = sum(e["kind"] == "heading" for p in pages for e in p["elements"])
    if not headings:
        issues.append({"page": None, "message": "Heading belum dikenali; daftar isi otomatis perlu pemeriksaan."})
    return {"source": {k: v for k, v in source.items() if k != "search_text"}, "pages": pages,
            "issues": issues, "heading_count": headings,
            "status": "perlu pemeriksaan" if issues else "lengkap"}
