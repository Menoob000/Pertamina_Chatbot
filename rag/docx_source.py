"""Read Word structure, including native numbering and merged table cells."""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn, nsmap
from docx.table import Table
from docx.text.paragraph import Paragraph


def _val(node, xpath, default=None):
    found = node.findall(xpath.replace("w:", "{" + nsmap["w"] + "}")) if node is not None else []
    return found[0].get(qn("w:val"), default) if found else default


def _format_number(number, kind):
    if kind in {"lowerLetter", "upperLetter"}:
        text = ""
        while number > 0:
            number, remainder = divmod(number - 1, 26)
            text = chr(97 + remainder) + text
        return text.upper() if kind == "upperLetter" else text
    if kind in {"lowerRoman", "upperRoman"}:
        text = ""
        for value, symbol in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
                              (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
                              (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
            while number >= value:
                text += symbol
                number -= value
        return text.lower() if kind == "lowerRoman" else text
    return str(number)


class Numbering:
    def __init__(self, document):
        try:
            self.root = document.part.numbering_part.element
        except KeyError:
            self.root = None
        self.counts = {}

    def properties(self, paragraph):
        nodes = [paragraph._p]
        style = paragraph.style
        seen = set()
        while style is not None and style.style_id not in seen:
            seen.add(style.style_id)
            nodes.append(style.element)
            style = style.base_style
        number_id = level = None
        for node in nodes:
            number_id = number_id if number_id is not None else _val(node, "./w:pPr/w:numPr/w:numId")
            level = level if level is not None else _val(node, "./w:pPr/w:numPr/w:ilvl")
        return number_id, int(level or 0)

    def level(self, number_id, level):
        if self.root is None:
            return None, 1
        nums = self.root.xpath(f'./w:num[@w:numId="{number_id}"]')
        if not nums:
            return None, 1
        num = nums[0]
        abstract_id = _val(num, "./w:abstractNumId")
        abstract = self.root.xpath(f'./w:abstractNum[@w:abstractNumId="{abstract_id}"]/w:lvl[@w:ilvl="{level}"]')
        override = num.xpath(f'./w:lvlOverride[@w:ilvl="{level}"]')
        definition = abstract[0] if abstract else None
        start = int(_val(definition, "./w:start", "1"))
        if override:
            levels = override[0].xpath("./w:lvl")
            if levels:
                definition = levels[0]
                start = int(_val(definition, "./w:start", str(start)))
            start = int(_val(override[0], "./w:startOverride", str(start)))
        return definition, start

    def label(self, paragraph):
        number_id, level = self.properties(paragraph)
        if not number_id or number_id == "0":
            return "", None
        definition, start = self.level(number_id, level)
        if definition is None:
            return "", level
        counts = self.counts.setdefault(number_id, {})
        counts[level] = counts.get(level, start - 1) + 1
        for deeper in list(counts):
            if deeper > level:
                del counts[deeper]
        kind = _val(definition, "./w:numFmt", "decimal")
        pattern = _val(definition, "./w:lvlText", "%1.")
        if kind == "bullet":
            return "•", level
        def replace(match):
            index = int(match[1]) - 1
            parent, parent_start = self.level(number_id, index)
            return _format_number(counts.get(index, parent_start), _val(parent, "./w:numFmt", "decimal"))
        return re.sub(r"%(\d)", replace, pattern), level


def read_docx(path: Path) -> dict:
    document = Document(path)
    numbering = Numbering(document)
    blocks, issues, headings = [], [], []
    paragraph_index = table_index = 0

    def paragraph_block(paragraph, location):
        text = paragraph.text.replace("\x00", "").strip()
        if not text:
            return None
        label, list_level = numbering.label(paragraph)
        outline = _val(paragraph._p, "./w:pPr/w:outlineLvl")
        style = paragraph.style
        seen = set()
        while outline is None and style is not None and style.style_id not in seen:
            seen.add(style.style_id)
            outline = _val(style.element, "./w:pPr/w:outlineLvl")
            style = style.base_style
        match = re.search(r"Heading\s*(\d)", paragraph.style.name, re.I)
        level = int(outline) + 1 if outline is not None and int(outline) < 9 else int(match[1]) if match else 0
        if level:
            headings[:] = headings[:level - 1]
            headings.append(text)
        return {"kind": "heading" if level else "paragraph", "text": f"{label} {text}".strip(),
                "literal_text": text, "level": level, "list_level": list_level,
                "number_label": label, "section": " / ".join(headings) or None,
                "location": location, "page": None}

    for element in document.element.body.iterchildren():
        if element.tag == qn("w:p"):
            paragraph_index += 1
            block = paragraph_block(Paragraph(element, document), f"paragraf {paragraph_index}")
            if block:
                blocks.append(block)
        elif element.tag == qn("w:tbl"):
            table_index += 1
            table = Table(element, document)
            rows, cells, origins = [], [], {}
            for row_index, row in enumerate(table.rows):
                values = []
                for column, cell in enumerate(row.cells):
                    if cell._tc in origins:
                        values.append("")
                        continue
                    origins[cell._tc] = (row_index, column)
                    cell_parts = []
                    for paragraph in cell.paragraphs:
                        block = paragraph_block(paragraph, f"tabel {table_index}, baris {row_index + 1}, kolom {column + 1}")
                        if block:
                            cell_parts.append(block["text"])
                    value = "\n".join(cell_parts)
                    values.append(value)
                    props = cell._tc.tcPr
                    cells.append({"row": row_index, "column": column, "text": value,
                                  "colspan": int(_val(props, "./w:gridSpan", "1")),
                                  "vertical_merge": _val(props, "./w:vMerge"),
                                  "literal_text": cell.text})
                rows.append(values)
            blocks.append({"kind": "table", "rows": rows, "cells": cells, "editable": True,
                           "text": "\n".join(" | ".join(row) for row in rows),
                           "literal_text": "\n".join(c["literal_text"] for c in cells),
                           "location": f"tabel {table_index}", "section": " / ".join(headings) or None,
                           "page": None})
    if document.element.xpath('.//w:drawing | .//w:pict'):
        issues.append("Gambar dipertahankan pada DOCX hasil; teks dalam gambar tidak diindeks tanpa OCR.")
    if document.element.xpath('.//w:txbxContent | .//w:del | .//w:ins | .//w:tbl/w:tr/w:tc/w:tbl'):
        issues.append("Text box, tracked changes, atau tabel bersarang perlu diperiksa; pencarian memakai paragraf dan tabel utama.")
    auxiliary = []
    for index, section in enumerate(document.sections, 1):
        for kind, item in (("header", section.header), ("footer", section.footer)):
            text = "\n".join(p.text for p in item.paragraphs if p.text.strip())
            if text:
                auxiliary.append({"kind": kind, "section": index, "text": text})
    return {"blocks": blocks, "issues": issues, "auxiliary": auxiliary,
            "image_count": len(document.inline_shapes), "paragraph_count": paragraph_index,
            "table_count": table_index}
