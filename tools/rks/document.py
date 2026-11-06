"""Deterministic DOCX layout for extracted RKS elements."""
from pathlib import Path
import re

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def _field(paragraph, instruction: str):
    run = paragraph.add_run()
    for kind, value in (("begin", None), (None, instruction), ("end", None)):
        node = OxmlElement("w:fldChar" if kind else "w:instrText")
        if kind:
            node.set(qn("w:fldCharType"), kind)
        else:
            node.set(qn("xml:space"), "preserve")
            node.text = value
        run._r.append(node)


def _new_page(doc):
    if doc.paragraphs and not doc.paragraphs[-1].paragraph_format.page_break_before:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.page_break_before = True
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = Pt(1)
        paragraph.add_run().font.size = Pt(1)


def _reflow(text):
    """Reflow PDF line wraps while retaining explicit list-item boundaries."""
    output = ""
    item = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?\s|[a-zA-Z][.)]\s|[•●*-]\s)")
    for line in text.splitlines():
        if not output:
            output = line
        else:
            output += ("\n" if item.match(line.lstrip()) else " ") + line
    return output


def render_document(extracted: dict, output: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2.5)
    section.left_margin, section.right_margin = Cm(3), Cm(2.5)
    for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.color.rgb = RGBColor(0, 0, 0)
        for border in style.element.xpath('.//w:pBdr'):
            border.getparent().remove(border)
        for fonts in style.element.xpath('.//w:rFonts'):
            for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
                fonts.attrib.pop(qn(f"w:{attr}"), None)
    doc.styles["Title"].font.size = Pt(20)
    doc.styles["Normal"].font.size = Pt(10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(6)
    doc.styles["Normal"].paragraph_format.line_spacing = 1.08
    for i, size in enumerate((13, 11, 10), 1):
        doc.styles[f"Heading {i}"].font.size = Pt(size)
        doc.styles[f"Heading {i}"].paragraph_format.keep_with_next = True
    header = section.header.paragraphs[0]
    header.text = "Draf tertata dari RKS referensi"
    header.runs[0].font.size = Pt(8)
    footer = section.footer.paragraphs[0]
    footer.add_run("Halaman ")
    _field(footer, "PAGE")
    # Original cover is transcribed first; do not invent a second project title.
    toc_added = False
    for page in extracted["pages"]:
        if page.get("replaced_toc"):
            if not toc_added:
                _new_page(doc)
                doc.add_paragraph("Daftar isi", "Title")
                _field(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u')
                _new_page(doc)
                toc_added = True
            continue
        if page["page"] == 2 and not toc_added and extracted["heading_count"]:
            _new_page(doc)
            doc.add_paragraph("Daftar isi", "Title")
            _field(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u')
            _new_page(doc)
            toc_added = True
        if page["page"] > 1 and any(e.get("page_fallback") for e in page["elements"]):
            _new_page(doc)
        if page.get("issues"):
            note = doc.add_paragraph(f"[Perlu pemeriksaan terhadap halaman sumber {page['page']}]")
            note.runs[0].font.size = Pt(8)
            note.paragraph_format.keep_with_next = True
        for element in page["elements"]:
            kind = element["kind"]
            if kind in {"paragraph", "heading"}:
                text = element["text"]
                # Only whitespace reflow changes; literals and units are kept.
                if kind == "heading":
                    doc.add_paragraph(text, f"Heading {element['level']}")
                else:
                    paragraph = doc.add_paragraph(_reflow(text))
                    if element.get("source_role") == "margin":
                        for run in paragraph.runs:
                            run.font.size = Pt(7)
            elif kind == "table" and element["editable"]:
                rows = element["rows"]
                if not rows:
                    continue
                table = doc.add_table(rows=0, cols=max(map(len, rows)))
                table.style = "Table Grid"
                table.autofit = False
                for column in table.columns:
                    column.width = Cm(15.5 / len(table.columns))
                for index, values in enumerate(rows):
                    row = table.add_row()
                    # Allow splitting very tall rows; a blanket cantSplit can
                    # create overflows for source tables with long paragraphs.
                    for cell, value in zip(row.cells, values):
                        cell.text = str(value or "")
                        for p in cell.paragraphs:
                            for run in p.runs:
                                run.font.size = Pt(9)
                    if index == 0:
                        repeat = OxmlElement("w:tblHeader")
                        row._tr.get_or_add_trPr().append(repeat)
                doc.add_paragraph()
            else:
                # Scale both axes, preserving aspect ratio and page margins.
                bbox = element["bbox"]
                ratio = (bbox[3] - bbox[1]) / max(1, bbox[2] - bbox[0])
                native_width = (bbox[2] - bbox[0]) / max(1, page.get("width", 595)) * 19
                width = min(15.5, 22.5 / max(ratio, .01), native_width)
                doc.add_picture(element["path"], width=Cm(width))
        if page["page"] < len(extracted["pages"]) and (page["page"] == 1 or any(e.get("page_fallback") for e in page["elements"])):
            _new_page(doc)
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    doc.settings.element.append(update)
    doc.core_properties.title = Path(extracted["source"]["filename"]).stem
    doc.core_properties.comments = f"Sumber: {extracted['source']['filename']}; SHA256: {extracted['source']['sha256']}"
    doc.save(output)
