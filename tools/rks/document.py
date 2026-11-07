"""Deterministic DOCX layout for extracted RKS elements."""
from pathlib import Path
import re

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
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


def _set_cell_border(cell, color="000000", size="8"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), size)
        node.set(qn("w:color"), color)


def _set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_page_border(section):
    sect_pr = section._sectPr
    borders = sect_pr.first_child_found_in("w:pgBorders")
    if borders is None:
        borders = OxmlElement("w:pgBorders")
        sect_pr.append(borders)
    borders.set(qn("w:offsetFrom"), "page")
    # The cover is the only RKS page that carries an outer frame.  Word's
    # firstPage display setting keeps all subsequent document pages unboxed.
    borders.set(qn("w:display"), "firstPage")
    for side in ("top", "left", "bottom", "right"):
        edge = OxmlElement(f"w:{side}")
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), "8")
        edge.set(qn("w:space"), "24")
        edge.set(qn("w:color"), "000000")
        borders.append(edge)


def _add_box(doc, text, *, size=10, bold=False, before=0, after=0):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.cell(0, 0)
    _set_cell_border(cell)
    _set_cell_margins(cell, top=70, bottom=70)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    content = cell.paragraphs[0]
    content.alignment = WD_ALIGN_PARAGRAPH.CENTER
    content.paragraph_format.space_after = Pt(0)
    run = content.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    return table


def _checkbox_control(label: str, checked: bool):
    """Create a native Word checkbox content control with a visible fallback."""
    sdt = OxmlElement("w:sdt")
    properties = OxmlElement("w:sdtPr")
    identifier = OxmlElement("w:id")
    identifier.set(qn("w:val"), str(abs(hash(label)) % 2_000_000_000))
    properties.append(identifier)
    alias = OxmlElement("w:alias")
    alias.set(qn("w:val"), f"CSMS {label}")
    properties.append(alias)
    tag = OxmlElement("w:tag")
    tag.set(qn("w:val"), f"csms_{label.casefold()}")
    properties.append(tag)
    checkbox = OxmlElement("w14:checkbox")
    checked_node = OxmlElement("w14:checked")
    checked_node.set(qn("w14:val"), "1" if checked else "0")
    checkbox.append(checked_node)
    checked_state = OxmlElement("w14:checkedState")
    checked_state.set(qn("w14:val"), "2612")
    checked_state.set(qn("w14:font"), "Segoe UI Symbol")
    checkbox.append(checked_state)
    unchecked_state = OxmlElement("w14:uncheckedState")
    unchecked_state.set(qn("w14:val"), "2610")
    unchecked_state.set(qn("w14:font"), "Segoe UI Symbol")
    checkbox.append(unchecked_state)
    properties.append(checkbox)
    sdt.append(properties)
    content = OxmlElement("w:sdtContent")
    run = OxmlElement("w:r")
    run_properties = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), "Segoe UI Symbol")
    fonts.set(qn("w:hAnsi"), "Segoe UI Symbol")
    run_properties.append(fonts)
    run.append(run_properties)
    text = OxmlElement("w:t")
    text.text = "☒" if checked else "☐"
    run.append(text)
    content.append(run)
    sdt.append(content)
    return sdt


def _add_csms_controls(doc, assessment: dict | None):
    """Place editable HIGH/MIDDLE/LOW checkboxes on the RKS cover."""
    selected = (assessment or {}).get("category")
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(0)
    for index, category in enumerate(("HIGH", "MIDDLE", "LOW")):
        paragraph._p.append(_checkbox_control(category, selected == category))
        run = paragraph.add_run(f" {category}")
        run.font.size = Pt(9)
        if index < 2:
            paragraph.add_run("     ")


def _table_widths(rows, columns: int) -> list[float]:
    """Assign compact widths to short fields and space to descriptive fields."""
    longest = [max((len(str(row[index])) if index < len(row) else 0 for row in rows), default=0)
               for index in range(columns)]
    compact = [length <= 12 for length in longest]
    widths = [1.35 if is_compact else 0.0 for is_compact in compact]
    flexible = [index for index in range(columns) if not compact[index]]
    remaining = max(4.0, 16.3 - sum(widths))
    weight_total = sum(max(12, min(longest[index], 65)) for index in flexible) or 1
    for index in flexible:
        weight = max(12, min(longest[index], 65))
        widths[index] = remaining * weight / weight_total
    return widths


def _set_fixed_table_layout(table):
    properties = table._tbl.tblPr
    layout = properties.first_child_found_in("w:tblLayout")
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        properties.append(layout)
    layout.set(qn("w:type"), "fixed")


def _append_table(doc, rows):
    columns = max((len(row) for row in rows), default=0)
    if not columns:
        return
    table = doc.add_table(rows=0, cols=columns)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _set_fixed_table_layout(table)
    widths = _table_widths(rows, columns)
    for index, width in enumerate(widths):
        table.columns[index].width = Cm(width)
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for index, cell in enumerate(cells):
            text = str(values[index] if index < len(values) else "")
            cell.text = text
            cell.width = Cm(widths[index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            _set_cell_border(cell, color="D9D9D9", size="6")
            _set_cell_margins(cell, top=85, bottom=85, start=115, end=115)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                if row_index == 0 or len(text) <= 18:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    # Table cells must wrap naturally. Justification spreads
                    # short extracted fragments across the cell width and
                    # makes RKS evidence tables appear artificially sparse.
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in paragraph.runs:
                    run.font.size = Pt(8.5)
                    if row_index == 0:
                        run.bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _numeric_indent(depth: int) -> Cm:
    """Return an intentional, readable indentation for hierarchical labels."""
    # A heading such as 5.2 stays at the body margin.  Its descendants move
    # right in small, consistent steps, matching conventional RKS formatting.
    return Cm(0.48 + max(0, min(depth - 3, 4)) * 0.34)


def _apply_list_indent(paragraph, indent: Cm, *, marker_indent: Cm | None = None,
                       justify: bool = False) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if justify else WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.left_indent = indent
    paragraph.paragraph_format.first_line_indent = (
        Cm(marker_indent.cm - indent.cm) if marker_indent is not None else Cm(-0.30)
    )
    paragraph.paragraph_format.keep_together = True


def _marker_width(text: str) -> float:
    """Approximate the inline width of a source list marker in the body font."""
    match = re.match(r"^((?:\d+(?:\.\d+)*[.)]?)|(?:[a-z]+\.))\s*", text, re.I)
    if not match:
        return 0.55
    return max(0.72, min(1.65, len(match.group(1)) * 0.155 + 0.12))


def _page_list_origin(page: dict) -> float:
    positions = [element["bbox"][0] for element in page["elements"]
                 if element.get("list_kind") in {"number", "ordinal", "alpha", "roman"}]
    return min(positions) if positions else 0.0


def _source_marker_indent(element: dict, origin: float) -> Cm:
    """Map the source's x-position to a stable hierarchy level in Word."""
    delta = max(0.0, element["bbox"][0] - origin)
    return Cm(min(4.4, 0.20 + delta * 0.028))


def _render_editable_layout(extracted: dict, output: Path, csms_assessment: dict | None = None) -> None:
    """Build an editable cover, Word headings, tables and TOC from PDF geometry."""
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2.2)
    section.left_margin = section.right_margin = Cm(2.2)
    section.different_first_page_header_footer = True
    for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.color.rgb = RGBColor(0, 0, 0)
        for border in style.element.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    normal = doc.styles["Normal"]
    normal.font.size = Pt(9.5)
    normal.paragraph_format.space_after = Pt(1)
    normal.paragraph_format.line_spacing = 1.1
    for level, size in ((1, 12), (2, 10.5), (3, 10)):
        style = doc.styles[f"Heading {level}"]
        style.font.size = Pt(size)
        style.paragraph_format.space_before = Pt(8)
        style.paragraph_format.space_after = Pt(3)
        style.paragraph_format.keep_with_next = True
    header = section.header.paragraphs[0]
    header.text = "Draf tertata dari RKS referensi"
    header.runs[0].font.size = Pt(8)
    footer = section.footer.paragraphs[0]
    footer.add_run("Halaman ")
    _field(footer, "PAGE")

    _set_page_border(section)
    cover = extracted["pages"][0]
    cover_elements = cover["elements"]
    entries = [(element["text"].replace("RESIKOpekerjaan", "RESIKO pekerjaan").replace("\t", "    "),
                element["bbox"][1]) for element in cover_elements]
    title_index = next((index for index, (text, _) in enumerate(entries)
                        if re.search(r"RENCANA\s+KERJA.*(?:SYARAT|RKS)", text, re.I)), None)
    title = entries[title_index][0] if title_index is not None else "RENCANA KERJA DAN SYARAT-SYARAT"
    title = f"{title}\n(RKS)" if "(RKS)" not in title.upper() else title
    omitted = {title, "(RKS)"}
    def contains(*terms):
        return lambda text: any(term in text.upper() for term in terms)
    has_formal_fields = any("BIDDER" in text.upper() or "RESIKO" in text.upper() or "RISIKO" in text.upper()
                            for text, _ in entries)
    first_page_is_body = (not has_formal_fields and
                          any(re.match(r"^(?:BAB|PASAL)\b", text.strip(), re.I) for text, _ in entries))
    work = [text for text, y in entries if .12 * cover["height"] < y < .45 * cover["height"]
            and not contains("RENCANA KERJA", "BIDDER", "RESIKO", "RISIKO", "HIGH", "MIDDLE", "LOW")(text)
            and text not in omitted]
    bidder = next((text for text, _ in entries if "BIDDER" in text.upper()), "Bidder List No: ______________________")
    risk = next((text for text, _ in entries if "RESIKO" in text.upper() or "RISIKO" in text.upper()),
                "RESIKO PEKERJAAN (ASPEK CSMS):")
    options = next((text for text, _ in entries if all(word in text.upper() for word in ("HIGH", "MIDDLE", "LOW"))),
                   "☐ HIGH    ☐ MIDDLE    ☐ LOW")
    company = next((text for text, y in entries if "PT " in text.upper() and y > .5 * cover["height"]),
                   "[Nama perusahaan dari sumber]")
    _add_box(doc, title, size=14, bold=True, before=62, after=16)
    if has_formal_fields:
        _add_box(doc, "\n".join(work) or "[Nama pekerjaan dari sumber]", size=9.5, bold=True, after=18)
        for text, before, bold in ((bidder, 0, False), (risk, 5, False)):
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_before = Pt(before)
            para.paragraph_format.space_after = Pt(0)
            run = para.add_run(text)
            run.bold = bold
            run.font.size = Pt(9)
        _add_csms_controls(doc, csms_assessment)
        logo = Path("assets/logo_pertamina.png")
        if logo.is_file():
            logo_paragraph = doc.add_paragraph()
            logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            logo_paragraph.paragraph_format.space_before = Pt(16)
            logo_paragraph.add_run().add_picture(str(logo), width=Cm(3.4))
        company_paragraph = doc.add_paragraph()
        company_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        company_paragraph.paragraph_format.space_before = Pt(118)
        run = company_paragraph.add_run(company)
        run.bold = True
        run.font.size = Pt(10)
    else:
        after_title = entries[title_index + 1:] if title_index is not None else entries
        project_name = next((text for text, _ in after_title if re.match(r"^NAMA\s+PEKERJAAN\s*:", text, re.I)), None)
        summary = [text for text, _ in after_title if text not in omitted and len(text) <= 120 and
                   not re.match(r"^(?:REV|DATE|DOC\.?\s*NO|SHEET|LOKASI\s*:?|BAB|PASAL|PENDAHULUAN|URAIAN)\b", text, re.I)]
        if first_page_is_body:
            summary = [project_name] if project_name else [Path(extracted["source"]["filename"]).stem]
        summary = summary[:4] or [Path(extracted["source"]["filename"]).stem]
        generic = doc.add_paragraph()
        generic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        generic.paragraph_format.space_before = Pt(32)
        generic.paragraph_format.space_after = Pt(0)
        run = generic.add_run("\n".join(summary))
        run.bold = True
        run.font.size = Pt(10)

    doc.add_page_break()
    doc.add_paragraph("Daftar isi", "Title")
    _field(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u')
    doc.add_page_break()
    last_number_depth = 0
    last_list_indent = None
    body_pages = extracted["pages"] if first_page_is_body else extracted["pages"][1:]
    for page in body_pages:
        if page.get("replaced_toc"):
            continue
        page_list_origin = _page_list_origin(page)
        if any(e.get("source_role") == "unreadable" for e in page["elements"]):
            warning = doc.add_paragraph(f"[Halaman sumber {page['page']} tidak terbaca sebagai teks]")
            warning.runs[0].italic = True
        for element in page["elements"]:
            if element["kind"] == "heading":
                doc.add_paragraph(element["text"], f"Heading {element['level']}")
                last_number_depth = 0
                last_list_indent = None
            elif element["kind"] == "table" and element.get("editable"):
                _append_table(doc, element["rows"])
                last_number_depth = 0
                last_list_indent = None
            elif element.get("source_role") == "layout_label":
                # Signature/approval labels are visual blocks in the source,
                # not continuations of the preceding narrative sentence.
                paragraph = doc.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.left_indent = Cm(0.48)
                paragraph.paragraph_format.space_before = Pt(3)
                paragraph.paragraph_format.space_after = Pt(1)
                run = paragraph.add_run(element["text"])
                run.bold = True
                last_number_depth = 0
                last_list_indent = None
            else:
                paragraph = doc.add_paragraph(element["text"])
                paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                depth = element.get("number_depth", 0)
                list_kind = element.get("list_kind")
                if list_kind in {"number", "ordinal", "alpha", "roman"}:
                    # PDF marker coordinates are preserved here. In RKS they
                    # encode nested list levels more reliably than marker type.
                    marker_indent = _source_marker_indent(element, page_list_origin)
                    indent = Cm(marker_indent.cm + _marker_width(element["text"]))
                    _apply_list_indent(paragraph, indent, marker_indent=marker_indent)
                    last_number_depth = depth if depth else last_number_depth
                    last_list_indent = indent
                elif list_kind == "bullet":
                    marker_indent = last_list_indent or _numeric_indent(last_number_depth)
                    indent = Cm(marker_indent.cm + 0.48)
                    _apply_list_indent(paragraph, indent, marker_indent=marker_indent, justify=True)
                    last_list_indent = indent
                elif element.get("value_line") and last_number_depth:
                    # Values are paired with their immediately preceding
                    # specification label, at the same hierarchy level.
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    paragraph.paragraph_format.left_indent = last_list_indent or _numeric_indent(last_number_depth)
                    paragraph.paragraph_format.first_line_indent = Cm(0)
                elif not element.get("value_line"):
                    # Narrative lines belonging to a numbered or alphabetical
                    # item must never jump back to the page margin.  Unlike a
                    # list marker, they use no hanging indent and may justify.
                    if last_list_indent is not None:
                        paragraph.paragraph_format.left_indent = last_list_indent
                        paragraph.paragraph_format.first_line_indent = Cm(0)
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    doc.settings.element.append(update)
    doc.core_properties.title = Path(extracted["source"]["filename"]).stem
    doc.core_properties.comments = (f"Teks dan tabel dari {extracted['source']['filename']}; SHA256: "
                                    f"{extracted['source']['sha256']}. Elemen grafis perlu pemeriksaan.")
    doc.save(output)


def render_document(extracted: dict, output: Path, csms_assessment: dict | None = None) -> None:
    if extracted.get("mode") in {"text_only", "editable_layout"}:
        return _render_editable_layout(extracted, output, csms_assessment=csms_assessment)
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
