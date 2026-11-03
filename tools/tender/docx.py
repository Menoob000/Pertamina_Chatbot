"""
Pure Python DOCX Generator for Dokumen Tender Pertamina Patra Niaga.
Renders the complete formal tender package:
- Cover page (Pertamina Patra Niaga layout, Confidential banner, Procurement signers, Regional address)
- Bagian A Divider: IKPP
- Daftar Isi (Word dynamic field)
- BAB I: Ketentuan Khusus IKPP (40-point structured table with nested schedules & KBUP)
- BAB II: Ketentuan Umum IKPP (30 Standard Articles, HEA formulas, Arithmetic tables, Sanctions)
- Lampiran IKPP Divider
- Lampiran 1A - 8 (1A-1, 1A-2, 1B, 1C, 1D, 1E, 1F, 2A dynamic, 2B, 3A CSMS matrix, 3B, 4 TKDN, 5A, 5B BoQ, 6, 7, 8)
- Bagian B Divider: Rancangan Kontrak
- Bagian B: Full Draft Contract (Pasal 1 - 18, Pakta Integritas PI-07, Template SP3MK)
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

from tender.static_content import (
    BAB_II_ARTICLES,
    CSMS_MATRIX_DATA,
    CONTRACT_ARTICLES,
)

# ──────────────────────────────────────────────────────────────
# Constants & Colors
# ──────────────────────────────────────────────────────────────

ASSETS_DIR = Path("./assets")
OUTPUT_DIR = Path("./output")
LOGO_PATH = ASSETS_DIR / "logo_pertamina.png"

# Color Palette (Pertamina Corporate theme)
COLOR_NAVY = "002D62"
COLOR_HEADER_BG = "D9E2F3"
COLOR_ALT_BG = "F7F9FC"
COLOR_LIGHT_GRAY = "E0E0E0"
COLOR_BLACK = "000000"
COLOR_WHITE = "FFFFFF"


# ──────────────────────────────────────────────────────────────
# XML Formatting Helpers
# ──────────────────────────────────────────────────────────────

def _set_cell_shading(cell, color_hex: str):
    """Set background fill color for a table cell."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}" w:val="clear"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def _set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    """Set internal padding for a cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{top}" w:type="dxa"/>'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'  <w:left w:w="{left}" w:type="dxa"/>'
        f'  <w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def _set_cell_border(cell, **kwargs):
    """Set cell borders: top, bottom, left, right dicts with {val, sz, color}."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}></w:tcBorders>')

    for edge in ("top", "bottom", "left", "right"):
        if edge in kwargs:
            attrs = kwargs[edge]
            element = parse_xml(
                f'<w:{edge} {nsdecls("w")} w:val="{attrs.get("val", "single")}" '
                f'w:sz="{attrs.get("sz", "4")}" w:space="0" '
                f'w:color="{attrs.get("color", "000000")}"/>'
            )
        else:
            element = parse_xml(f'<w:{edge} {nsdecls("w")} w:val="none"/>')
        tcBorders.append(element)

    tcPr.append(tcBorders)


def _add_page_border(section):
    """Add a formal page border to a section."""
    sectPr = section._sectPr
    pgBorders = parse_xml(
        f'<w:pgBorders {nsdecls("w")} w:offsetFrom="page">'
        f'  <w:top w:val="single" w:sz="12" w:space="24" w:color="000000"/>'
        f'  <w:left w:val="single" w:sz="12" w:space="24" w:color="000000"/>'
        f'  <w:bottom w:val="single" w:sz="12" w:space="24" w:color="000000"/>'
        f'  <w:right w:val="single" w:sz="12" w:space="24" w:color="000000"/>'
        f'</w:pgBorders>'
    )
    sectPr.append(pgBorders)


def _remove_page_border(section):
    """Remove page border from a section."""
    sectPr = section._sectPr
    pgBorders = sectPr.find(qn('w:pgBorders'))
    if pgBorders is not None:
        sectPr.remove(pgBorders)


def _escape_xml(text: Any) -> str:
    """Escape special characters for XML attribute and text values."""
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _add_dropdown_control(paragraph, label: str, options: List[str], current_value: Optional[str] = None):
    """
    Insert a Word Content Control Dropdown List (<w:dropDownList>) into a paragraph.
    Allows users in Microsoft Word to click and select an option from a dropdown list.
    """
    val = current_value if current_value and current_value in options else (options[0] if options else "")
    tag_val = label.lower().replace(" ", "_")
    
    label_esc = _escape_xml(label)
    tag_esc = _escape_xml(tag_val)
    val_esc = _escape_xml(val)
    items_xml = "".join([
        f'<w:listItem w:displayText="{_escape_xml(opt)}" w:value="{_escape_xml(opt)}"/>'
        for opt in options
    ])

    sdt_xml = f'''<w:sdt {nsdecls("w")}>
      <w:sdtPr>
        <w:alias w:val="{label_esc}"/>
        <w:tag w:val="{tag_esc}"/>
        <w:dropDownList>
          {items_xml}
        </w:dropDownList>
      </w:sdtPr>
      <w:sdtContent>
        <w:r>
          <w:rPr>
            <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
            <w:sz w:val="19"/>
            <w:color w:val="002D62"/>
          </w:rPr>
          <w:t>{val_esc}</w:t>
        </w:r>
      </w:sdtContent>
    </w:sdt>'''

    paragraph._p.append(parse_xml(sdt_xml))


def _add_date_picker_control(paragraph, label: str, current_date_str: str = "Senin, 08 Desember 2025"):
    """
    Insert a Word Content Control Date Picker (<w:date>) into a paragraph.
    Allows users in Microsoft Word to click the dropdown arrow to pick a date from an interactive calendar.
    """
    label_esc = _escape_xml(label)
    tag_esc = _escape_xml(label.lower().replace(" ", "_"))
    date_esc = _escape_xml(current_date_str)

    sdt_xml = f'''<w:sdt {nsdecls("w")}>
      <w:sdtPr>
        <w:alias w:val="{label_esc}"/>
        <w:tag w:val="{tag_esc}"/>
        <w:date>
          <w:dateFormat w:val="dddd, dd MMMM yyyy"/>
          <w:lid w:val="id-ID"/>
          <w:storeMappedDataAs w:val="dateTime"/>
          <w:calendar w:val="gregorian"/>
        </w:date>
      </w:sdtPr>
      <w:sdtContent>
        <w:r>
          <w:rPr>
            <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
            <w:sz w:val="18"/>
            <w:color w:val="002D62"/>
          </w:rPr>
          <w:t>{date_esc}</w:t>
        </w:r>
      </w:sdtContent>
    </w:sdt>'''

    paragraph._p.append(parse_xml(sdt_xml))


def _add_paragraph(doc, text: str = "", font_name: str = "Arial", font_size: int = 11,
                   bold: bool = False, italic: bool = False,
                   alignment=WD_ALIGN_PARAGRAPH.LEFT,
                   space_before: int = 0, space_after: int = 4,
                   color_rgb: Optional[RGBColor] = None):
    """Helper to add a cleanly formatted paragraph."""
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if text:
        r = p.add_run(text)
        r.font.name = font_name
        r.font.size = Pt(font_size)
        r.font.bold = bold
        r.font.italic = italic
        if color_rgb:
            r.font.color.rgb = color_rgb
        r._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    return p


# ──────────────────────────────────────────────────────────────
# Headers & Footers
# ──────────────────────────────────────────────────────────────

def _setup_tender_header_footer(section, doc_number: str = ""):
    """Setup Pertamina Patra Niaga tender header and footer."""
    # ── Header ──
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.paragraph_format.space_after = Pt(4)

    if LOGO_PATH.exists():
        run_logo = hp.add_run()
        run_logo.add_picture(str(LOGO_PATH), height=Cm(1.1))
    else:
        run_text = hp.add_run("PERTAMINA PATRA NIAGA")
        run_text.font.name = "Arial"
        run_text.font.size = Pt(10)
        run_text.font.bold = True
        run_text.font.color.rgb = RGBColor(0, 45, 98)

    # ── Footer ──
    footer = section.footer
    footer.is_linked_to_previous = False

    # Disclaimer paragraph
    fp_disc = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp_disc.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fp_disc.paragraph_format.space_after = Pt(2)
    r_disc = fp_disc.add_run(
        "Dilarang menggandakan, menerjemahkan, mengalihkan atau menyebarluaskan Dokumen Tender ini untuk kepentingan komersial apapun atau kepada pihak ketiga dalam bentuk apapun tanpa persetujuan tertulis dari PT Pertamina Patra Niaga."
    )
    r_disc.font.name = "Arial"
    r_disc.font.size = Pt(6.5)
    r_disc.font.italic = True
    r_disc.font.color.rgb = RGBColor(128, 128, 128)

    # Divider bar in footer
    pPr = fp_disc._element.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="6" w:space="2" w:color="002D62"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)

    # Doc version & Page Number paragraph
    fp_page = footer.add_paragraph()
    fp_page.paragraph_format.space_before = Pt(2)
    fp_page.paragraph_format.space_after = Pt(0)
    
    r_left = fp_page.add_run("DOKUMEN TENDER\nVERSI 2.0 – NOVEMBER 2025")
    r_left.font.name = "Arial"
    r_left.font.size = Pt(7.5)
    r_left.font.bold = True

    # Tab spacing to push page numbers to right
    r_tab = fp_page.add_run("\t\t\t\t\t\t\t\tP a g e  ")
    r_tab.font.name = "Arial"
    r_tab.font.size = Pt(8)

    # Dynamic PAGE field
    fld1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
    run_f1 = fp_page.add_run()
    run_f1._element.append(fld1)
    run_f1.font.name = "Arial"
    run_f1.font.size = Pt(8)

    instr1 = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>')
    run_ins1 = fp_page.add_run()
    run_ins1._element.append(instr1)
    run_ins1.font.name = "Arial"
    run_ins1.font.size = Pt(8)

    fld2 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
    run_f2 = fp_page.add_run()
    run_f2._element.append(fld2)
    run_f2.font.name = "Arial"
    run_f2.font.size = Pt(8)


# ──────────────────────────────────────────────────────────────
# 1. Cover Page
# ──────────────────────────────────────────────────────────────

def _render_cover_page(doc: Document, tender_data: dict):
    """Render the official Pertamina Patra Niaga Dokumen Tender cover page."""
    cover = tender_data.get("cover_page") or {}
    pejabat = cover.get("pejabat_procurement") or {}
    regional = cover.get("unit_regional") or {}

    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # Top right "Confidential" header banner
    banner_p = doc.add_paragraph()
    banner_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    banner_run = banner_p.add_run("Confidential  ")
    banner_run.font.name = "Arial"
    banner_run.font.size = Pt(12)
    banner_run.font.bold = True
    banner_run.font.italic = True
    banner_run.font.color.rgb = RGBColor(180, 0, 0)

    # Logo
    if LOGO_PATH.exists():
        logo_p = doc.add_paragraph()
        logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo_p.paragraph_format.space_before = Pt(20)
        logo_p.paragraph_format.space_after = Pt(40)
        logo_run = logo_p.add_run()
        logo_run.add_picture(str(LOGO_PATH), width=Cm(7.5))
    else:
        _add_paragraph(doc, "PERTAMINA PATRA NIAGA", font_size=20, bold=True,
                       alignment=WD_ALIGN_PARAGRAPH.CENTER, space_before=20, space_after=40,
                       color_rgb=RGBColor(0, 45, 98))

    # Boxed title: "DOKUMEN TENDER"
    title_table = doc.add_table(rows=1, cols=1)
    title_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    title_cell = title_table.cell(0, 0)
    title_cell.width = Cm(16.0)
    _set_cell_margins(title_cell, top=200, bottom=200, left=200, right=200)
    _set_cell_border(
        title_cell,
        top={"sz": "16", "val": "single", "color": COLOR_BLACK},
        bottom={"sz": "16", "val": "single", "color": COLOR_BLACK}
    )
    p_title = title_cell.paragraphs[0]
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_title.add_run("DOKUMEN TENDER")
    r_t.font.name = "Arial"
    r_t.font.size = Pt(24)
    r_t.font.bold = True

    # Spacing
    _add_paragraph(doc, space_after=30)

    # NAMA PENGADAAN
    nama_pengadaan = cover.get("nama_pengadaan", "PENGADAAN JASA / BARANG PERTAMINA").upper()
    _add_paragraph(doc, nama_pengadaan, font_size=15, bold=True,
                   alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)

    # Nomor dan Tanggal
    nomor = cover.get("nomor_tender", "No.Project/DT/PND970000/2026-S7")
    tanggal = cover.get("tanggal", "04 Desember 2025")
    _add_paragraph(doc, f"Nomor. {nomor}", font_size=13, bold=True,
                   alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    _add_paragraph(doc, f"Tanggal {tanggal}", font_size=12, bold=False,
                   alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)

    # Signatory box (Fungsi Procurement)
    sig_table = doc.add_table(rows=2, cols=1)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c0 = sig_table.cell(0, 0)
    c0.width = Cm(15.0)
    _set_cell_margins(c0, top=100, bottom=100, left=150, right=150)
    _set_cell_shading(c0, "F0F4F8")
    _set_cell_border(c0, top={"sz": "6", "val": "single", "color": "000000"},
                         left={"sz": "6", "val": "single", "color": "000000"},
                         right={"sz": "6", "val": "single", "color": "000000"},
                         bottom={"sz": "4", "val": "single", "color": "000000"})
    p_sig0 = c0.paragraphs[0]
    p_sig0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r0_1 = p_sig0.add_run(pejabat.get("jabatan_1", "Wkl. Fungsi Procurement (Pengadaan)") + "\n")
    r0_1.font.name = "Arial"
    r0_1.font.size = Pt(10)
    r0_1.font.bold = True
    r0_2 = p_sig0.add_run(pejabat.get("jabatan_2", "Area Manager Procurement Kalimantan"))
    r0_2.font.name = "Arial"
    r0_2.font.size = Pt(10)

    c1 = sig_table.cell(1, 0)
    c1.width = Cm(15.0)
    _set_cell_margins(c1, top=100, bottom=100, left=150, right=150)
    _set_cell_border(c1, bottom={"sz": "6", "val": "single", "color": "000000"},
                         left={"sz": "6", "val": "single", "color": "000000"},
                         right={"sz": "6", "val": "single", "color": "000000"},
                         top={"sz": "4", "val": "single", "color": "000000"})
    p_sig1 = c1.paragraphs[0]
    p_sig1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sig1.paragraph_format.space_before = Pt(40)
    r1 = p_sig1.add_run(pejabat.get("nama", "Rigga Widar Atmagi"))
    r1.font.name = "Arial"
    r1.font.size = Pt(11)
    r1.font.bold = True

    # Spacing to bottom
    _add_paragraph(doc, space_after=30)

    # Unit Regional info at bottom
    _add_paragraph(doc, regional.get("nama_entitas", "PT PERTAMINA PATRA NIAGA REGIONAL KALIMANTAN"),
                   font_size=10, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph(doc, regional.get("fungsi", "PELAKSANA PEMILIHAN PENYEDIA FUNGSI PROCUREMENT KALIMANTAN"),
                   font_size=9, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph(doc, regional.get("alamat", "Jln. Yos Sudarso No. 148 Balikpapan 76123"),
                   font_size=9, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph(doc, f"Telp. {regional.get('telepon', '(0542) 752 4444')}",
                   font_size=9, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph(doc, regional.get("website", "www.pertaminapatraniaga.com"),
                   font_size=9, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)

    # Page break to Divider Bagian A
    doc.add_page_break()


# ──────────────────────────────────────────────────────────────
# 2. Divider Pages
# ──────────────────────────────────────────────────────────────

def _render_divider_page(doc: Document, title_lines: List[str]):
    """Render a standalone divider page with a bold centered box."""
    _add_paragraph(doc, space_after=140)

    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Cm(15.0)
    _set_cell_margins(cell, top=300, bottom=300, left=300, right=300)
    _set_cell_border(
        cell,
        top={"sz": "12", "val": "single", "color": COLOR_BLACK},
        bottom={"sz": "12", "val": "single", "color": COLOR_BLACK},
        left={"sz": "12", "val": "single", "color": COLOR_BLACK},
        right={"sz": "12", "val": "single", "color": COLOR_BLACK},
    )

    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for idx, line in enumerate(title_lines):
        r = p.add_run(line + ("\n\n" if idx < len(title_lines) - 1 else ""))
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(22 if idx == 0 else 14)

    doc.add_page_break()


# ──────────────────────────────────────────────────────────────
# 3. Table of Contents
# ──────────────────────────────────────────────────────────────

def _render_table_of_contents(doc: Document):
    """Render formal Table of Contents placeholder."""
    _add_paragraph(doc, "Daftar Isi", font_size=14, bold=True, space_before=12, space_after=18)

    toc_entries = [
        ("BAB I KETENTUAN KHUSUS IKPP", "3"),
        ("BAB II KETENTUAN UMUM IKPP", "12"),
        ("1.  DEFINISI", "12"),
        ("2.  SYARAT PESERTA", "15"),
        ("3.  PENJELASAN TENDER", "15"),
        ("4.  KETENTUAN DAN TATA CARA PENYAMPAIAN DOKUMEN PENAWARAN", "17"),
        ("5.  PEMBUKAAN DOKUMEN PENAWARAN", "23"),
        ("6.  KETENTUAN EVALUASI DOKUMEN PENAWARAN", "25"),
        ("7.  EVALUASI ADMINISTRASI", "29"),
        ("8.  EVALUASI TEKNIS", "29"),
        ("9.  EVALUASI HSSE PLAN (apabila dipersyaratkan)", "29"),
        ("10. EVALUASI TKDN (apabila dipersyaratkan)", "30"),
        ("11. EVALUASI KOMERSIAL", "32"),
        ("12. PENENTUAN PERINGKAT PESERTA", "32"),
        ("13. METODE EVALUASI", "33"),
        ("14. PEMBERITAHUAN/PENGUMUMAN HASIL EVALUASI", "35"),
        ("15. KETENTUAN KOREKSI ARITMATIKA, EVALUASI KOMERSIAL & HARGA TIMPANG", "35"),
        ("16. KETENTUAN KOREKSI ARITMATIKA", "38"),
        ("17. NEGOSIASI", "41"),
        ("18. PENGUMUMAN CALON PEMENANG", "48"),
        ("19. KETENTUAN SANGGAHAN", "48"),
        ("20. KETENTUAN JAMINAN PENGADAAN", "51"),
        ("21. PENUNJUKAN PEMENANG", "54"),
        ("22. PENERBITAN SP3MK", "54"),
        ("23. KETENTUAN PENERBITAN KONTRAK", "55"),
        ("24. PEMILIHAN PENYEDIA GAGAL", "55"),
        ("25. PEMBATALAN PEMILIHAN PENYEDIA", "55"),
        ("26. PEMILIHAN PENYEDIA MENGGUNAKAN SISTEM DIGITAL", "56"),
        ("27. PENILAIAN KINERJA PADA TAHAP PEMILIHAN PENYEDIA", "57"),
        ("28. BUSINESS CONTINUITY MANAGEMENT SYSTEM (BCMS)", "64"),
        ("29. KEBIJAKAN PENERAPAN ESG", "65"),
        ("30. KETENTUAN LAIN-LAIN", "65"),
        ("LAMPIRAN IKPP", "69"),
        ("BAGIAN B - RANCANGAN KONTRAK", "111")
    ]

    for title, page in toc_entries:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(2)
        r_t = p.add_run(title)
        r_t.font.name = "Arial"
        r_t.font.size = Pt(9.5)
        if title.startswith("BAB") or title.startswith("BAGIAN") or title.startswith("LAMPIRAN"):
            r_t.font.bold = True

        # Dots leader simulation with tab
        r_dots = p.add_run(f" {' .' * 35} ")
        r_dots.font.name = "Arial"
        r_dots.font.size = Pt(8)
        r_dots.font.color.rgb = RGBColor(160, 160, 160)

        r_p = p.add_run(page)
        r_p.font.name = "Arial"
        r_p.font.size = Pt(9.5)
        if title.startswith("BAB") or title.startswith("BAGIAN") or title.startswith("LAMPIRAN"):
            r_p.font.bold = True

    doc.add_page_break()


# ──────────────────────────────────────────────────────────────
# 4. BAB I Ketentuan Khusus IKPP (40 Points Table)
# ──────────────────────────────────────────────────────────────

def _render_bab_i_ketentuan_khusus(doc: Document, tender_data: dict):
    """Render BAB I Ketentuan Khusus IKPP as the official 40-point table."""
    kk = tender_data.get("ketentuan_khusus_ikpp") or {}

    _add_paragraph(doc, "BAB I KETENTUAN KHUSUS IKPP", font_size=13, bold=True, space_before=12, space_after=6)
    
    intro_p = _add_paragraph(
        doc,
        "Hal-hal yang diatur dalam BAB I (Ketentuan Khusus) ini untuk menetapkan dan mendeskripsikan lebih detail hal-hal "
        "yang diatur dalam BAB II (Ketentuan Umum). Apabila terdapat perbedaan antara ketentuan dalam BAB I (Ketentuan Khusus) "
        "dengan BAB II (Ketentuan Umum), maka diberlakukan ketentuan dalam BAB I (Ketentuan Khusus).",
        font_size=9.5, italic=False, space_after=12
    )

    # 40-row table
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_widths = (Cm(5.5), Cm(11.5))

    border_kwargs = {
        "top": {"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY},
        "bottom": {"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY},
        "left": {"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY},
        "right": {"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY},
    }

    def _add_row(no_str: str, label: str, content_val: Any):
        row = table.add_row()
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = col_widths[0]
        c1.width = col_widths[1]
        _set_cell_margins(c0, top=100, bottom=100, left=120, right=120)
        _set_cell_margins(c1, top=100, bottom=100, left=120, right=120)

        # Apply borders
        _set_cell_border(c0, **border_kwargs)
        _set_cell_border(c1, **border_kwargs)

        # Shading for left column
        _set_cell_shading(c0, COLOR_ALT_BG)

        # Label paragraph
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(f"{no_str}. {label}" if no_str else label)
        r0.font.name = "Arial"
        r0.font.size = Pt(9.5)
        r0.font.bold = True

        # Content paragraph
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)

        if isinstance(content_val, str):
            r1 = p1.add_run(content_val)
            r1.font.name = "Arial"
            r1.font.size = Pt(9.5)
        elif isinstance(content_val, list):
            for i, line in enumerate(content_val):
                p = c1.paragraphs[0] if i == 0 else c1.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(2)
                r = p.add_run(str(line))
                r.font.name = "Arial"
                r.font.size = Pt(9.5)
        return c1

    # Row 1 to 6
    _add_row("1", "Penyelenggara Pemilihan Penyedia", kk.get("penyelenggara", "Fungsi Procurement (Pengadaan)"))
    
    # 2. Kategori Pengadaan (Dropdown)
    c2 = _add_row("2", "Kategori Pengadaan", "")
    _add_dropdown_control(
        c2.paragraphs[0],
        label="Kategori Pengadaan",
        options=[
            "Pengadaan dalam Kondisi Normal",
            "Pengadaan dalam Kondisi Urgent",
            "Pengadaan Kondisi Emergency"
        ],
        current_value=kk.get("kategori_pengadaan", "Pengadaan dalam Kondisi Normal")
    )

    # 3. Pemilihan Penyedia (Dropdown)
    c3 = _add_row("3", "Pemilihan Penyedia", "")
    _add_dropdown_control(
        c3.paragraphs[0],
        label="Pemilihan Penyedia",
        options=[
            "Pertama",
            "Kedua",
            "Ketiga"
        ],
        current_value=kk.get("pemilihan_penyedia", "Pertama")
    )

    # 4. Syarat Status Peserta (Dropdown)
    c4 = _add_row("4", "Syarat Status Peserta", "")
    _add_dropdown_control(
        c4.paragraphs[0],
        label="Syarat Status Peserta",
        options=[
            "Tunggal",
            "Konsorsium",
            "Tunggal dan Konsorsium"
        ],
        current_value=kk.get("syarat_status_peserta", "Tunggal")
    )

    _add_row("5", "Syarat Golongan Usaha", f"1. Syarat golongan usaha bagi Peserta Tunggal adalah {kk.get('syarat_golongan_usaha', 'Menengah')}")

    csms_info = kk.get("syarat_kualifikasi_csms") or {}
    _add_row("6", "Syarat Kualifikasi CSMS", [
        f"1. Pekerjaan memiliki risiko {csms_info.get('tingkat_risiko', 'Tinggi')} terkait aspek HSSE",
        f"2. Syarat kualifikasi CSMS bagi Peserta Tunggal adalah {csms_info.get('kualifikasi_minimal', 'Tinggi')}"
    ])

    # Row 7: Syarat KBUP & KBLI
    c7 = _add_row("7", "Syarat Kode Bidang Usaha Pertamina (KBUP)", "1. Syarat KBUP dan KBLI bagi Peserta Tunggal adalah:")
    kbup_list = kk.get("syarat_kbup_kbli") or [
        {"kode": "Q - Jasa Pelaksana Konstruksi", "kode_sub_bidang": "Q.13.09", "deskripsi": "Konstruksi Perpipaan Minyak, Gas, dan Energi"},
        {"kode": "Q - Jasa Pelaksana Konstruksi", "kode_sub_bidang": "Q.13.10", "deskripsi": "Fasilitas Produksi, Perpipaan Minyak dan Gas"}
    ]
    sub_t = c7.add_table(rows=1 + len(kbup_list), cols=3)
    sub_t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx_h, h_text in enumerate(["Kode", "Kode Sub Bidang", "Deskripsi"]):
        c_h = sub_t.cell(0, idx_h)
        _set_cell_shading(c_h, COLOR_HEADER_BG)
        _set_cell_margins(c_h, top=60, bottom=60, left=80, right=80)
        p = c_h.paragraphs[0]
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True
    for idx_r, item in enumerate(kbup_list):
        r_cells = sub_t.rows[idx_r + 1].cells
        for col_i, key in enumerate(["kode", "kode_sub_bidang", "deskripsi"]):
            cell_k = r_cells[col_i]
            _set_cell_margins(cell_k, top=60, bottom=60, left=80, right=80)
            p = cell_k.paragraphs[0]
            r = p.add_run(str(item.get(key, "")))
            r.font.name = "Arial"
            r.font.size = Pt(8)

    # 8. Metode Pemenuhan Kebutuhan (Dropdown)
    c8 = _add_row("8", "Metode Pemenuhan Kebutuhan", "")
    _add_dropdown_control(
        c8.paragraphs[0],
        label="Metode Pemenuhan Kebutuhan",
        options=[
            "Sinergi Pertamina Group dengan Penunjukan kepada EBPG",
            "Sinergi Pertamina Group dengan Penugasan kepada EBPG",
            "Sinergi Pertamina Group dengan Pemilihan Langsung antar EBPG",
            "Tender Terbuka",
            "Tender Terbatas",
            "Pemilihan Langsung",
            "Tender Praktis",
            "Penunjukan Langsung"
        ],
        current_value=kk.get("metode_pemenuhan", "Tender Terbatas")
    )
    _add_row("9", "Pejabat Berwenang", kk.get("pejabat_berwenang", "Sr. Manager Opt. & Maint. Regional Kalimantan"))
    _add_row("10", "Pengawas Pekerjaan/Wakil Perusahaan", kk.get("pengawas_pekerjaan", "Region Manager RPD Regional Kalimantan"))

    # Row 11: Pre-bid meeting with interactive Date Picker Dropdown in table
    prebid = kk.get("jadwal_prebid") or {}
    c11 = _add_row("11", "Tahapan dan tata waktu Penjelasan Pekerjaan", "")
    p_intro = c11.paragraphs[0]
    r_intro = p_intro.add_run("1. Rapat Penjelasan (Pre-Bid Meeting) dilaksanakan dengan jadwal sebagai berikut:")
    r_intro.font.name = "Arial"
    r_intro.font.size = Pt(9.5)
    p_intro.paragraph_format.space_after = Pt(4)

    # Sub-table for Pre-Bid Meeting schedule with interactive Date Picker
    sub_t11 = c11.add_table(rows=2, cols=4)
    sub_t11.alignment = WD_TABLE_ALIGNMENT.CENTER
    sub_t11_headers = ["Tahapan / Kegiatan", "Hari, Tanggal", "Waktu", "Tempat / Media"]
    for idx_h, h_text in enumerate(sub_t11_headers):
        c_h = sub_t11.cell(0, idx_h)
        _set_cell_shading(c_h, COLOR_HEADER_BG)
        _set_cell_margins(c_h, top=60, bottom=60, left=80, right=80)
        _set_cell_border(c_h, **border_kwargs)
        p = c_h.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True

    r1_cells = sub_t11.rows[1].cells
    for c in r1_cells:
        _set_cell_margins(c, top=60, bottom=60, left=80, right=80)
        _set_cell_border(c, **border_kwargs)

    p_act = r1_cells[0].paragraphs[0]
    p_act.paragraph_format.space_before = Pt(0)
    p_act.paragraph_format.space_after = Pt(0)
    r_act = p_act.add_run("Rapat Penjelasan\n(Pre-Bid Meeting)")
    r_act.font.name = "Arial"
    r_act.font.size = Pt(8.5)

    p_date = r1_cells[1].paragraphs[0]
    p_date.paragraph_format.space_before = Pt(0)
    p_date.paragraph_format.space_after = Pt(0)
    _add_date_picker_control(
        p_date,
        label="Pilih Hari Tanggal Pre-Bid",
        current_date_str=prebid.get("hari_tanggal", "Senin, 08 Desember 2025")
    )

    p_time = r1_cells[2].paragraphs[0]
    p_time.paragraph_format.space_before = Pt(0)
    p_time.paragraph_format.space_after = Pt(0)
    r_time = p_time.add_run(prebid.get("waktu", "10.00 WITA"))
    r_time.font.name = "Arial"
    r_time.font.size = Pt(8.5)

    p_place = r1_cells[3].paragraphs[0]
    p_place.paragraph_format.space_before = Pt(0)
    p_place.paragraph_format.space_after = Pt(0)
    r_place = p_place.add_run(prebid.get("tempat", "Microsoft Teams Meeting"))
    r_place.font.name = "Arial"
    r_place.font.size = Pt(8.5)

    p_note = c11.add_paragraph()
    p_note.paragraph_format.space_before = Pt(6)
    p_note.paragraph_format.space_after = Pt(2)
    r_note = p_note.add_run("Catatan:\n1. Undangan disampaikan pada SAPP-SmartGEP.\n2. Jumlah maksimal perwakilan peserta Pre-Bid Meeting adalah 5 (lima) orang.")
    r_note.font.name = "Arial"
    r_note.font.size = Pt(9)
    r_note.font.italic = True

    # Row 12: Pemasukan Penawaran
    pemasukan = kk.get("jadwal_pemasukan") or {}
    _add_row("12", "Tahapan Pemasukan Penawaran", [
        "Penyampaian Dokumen Penawaran dilaksanakan pada:",
        f"Mulai dari   : {pemasukan.get('mulai_hari_tanggal', 'Senin, 08 Desember 2025')} ({pemasukan.get('mulai_waktu', '09.00 WITA')})",
        f"Sampai dengan: {pemasukan.get('selesai_hari_tanggal', 'Senin, 15 Desember 2025')} ({pemasukan.get('selesai_waktu', '16.00 WITA')})",
        f"Tempat/Portal: {pemasukan.get('tempat_portal', 'https://smart.gep.com')}"
    ])

    # Row 13 to 22
    # 13. Masa berlaku Dokumen Penawaran (Dropdown)
    c13 = _add_row("13", "Masa berlaku Dokumen Penawaran", "")
    _add_dropdown_control(
        c13.paragraphs[0],
        label="Masa Berlaku Dokumen Penawaran",
        options=[
            "Penawaran berlaku selama 90 (sembilan puluh) Hari Kalender sejak Pembukaan Dokumen Penawaran",
            "Penawaran berlaku selama 180 (seratus delapan puluh) Hari Kalender sejak Pembukaan Dokumen Penawaran"
        ],
        current_value=kk.get("masa_berlaku_penawaran", "Penawaran berlaku selama 90 (sembilan puluh) Hari Kalender sejak Pembukaan Dokumen Penawaran")
    )

    _add_row("14", "Mekanisme permintaan penjelasan", kk.get("mekanisme_permintaan_penjelasan", "Peserta hanya dapat menyampaikan pertanyaan klarifikasi saat Pre-Bid Meeting."))
    _add_row("15", "Ketentuan Kehadiran saat Penjelasan Pekerjaan", kk.get("ketentuan_kehadiran_penjelasan", "Wajib Hadir (Ketidakhadiran tidak menggugurkan, namun risiko ditanggung Peserta)."))

    # 16. Metode dan Ketentuan Penyampaian Dokumen Penawaran (Dropdown)
    c16 = _add_row("16", "Metode dan Ketentuan Penyampaian Dokumen Penawaran", "")
    _add_dropdown_control(
        c16.paragraphs[0],
        label="Metode Penyampaian Dokumen Penawaran",
        options=[
            "1 (satu) tahap 1 (satu) Sampul",
            "1 (satu) tahap 2 (dua) Sampul",
            "2 (dua) tahap 2 (dua) Sampul"
        ],
        current_value=kk.get("metode_penyampaian_penawaran", "1 (satu) tahap 1 (satu) Sampul")
    )

    _add_row("17", "Syarat dibukanya Penawaran", kk.get("syarat_dibukanya_penawaran", "Terdapat sekurang-kurangnya 2 (dua) Peserta yang menyampaikan penawaran sah."))

    # 18. Ketentuan Kehadiran Pembukaan Dokumen Penawaran (Dropdown)
    c18 = _add_row("18", "Ketentuan Kehadiran Pembukaan Dokumen Penawaran", "")
    _add_dropdown_control(
        c18.paragraphs[0],
        label="Kehadiran Pembukaan Dokumen Penawaran",
        options=[
            "Pembukaan dokumen penawaran tidak perlu dihadiri Peserta",
            "Pembukaan dokumen penawaran diperlukan kehadiran Peserta"
        ],
        current_value=kk.get("ketentuan_kehadiran_pembukaan", "Pembukaan dokumen penawaran tidak perlu dihadiri Peserta")
    )

    # 19. Ketentuan Klarifikasi Dokumen Penawaran (Dropdown)
    c19 = _add_row("19", "Ketentuan Klarifikasi Dokumen Penawaran", "")
    p19_1 = c19.paragraphs[0]
    p19_1.paragraph_format.space_before = Pt(0)
    p19_1.paragraph_format.space_after = Pt(2)
    r19_1 = p19_1.add_run("Media yang digunakan: ")
    r19_1.font.name = "Arial"
    r19_1.font.size = Pt(9.5)
    _add_dropdown_control(
        p19_1,
        label="Media Klarifikasi",
        options=[
            "Discussion Forum SAPP-SmartGEP",
            "Online melalui Microsoft Teams (M-Teams) Meeting",
            "Offline"
        ],
        current_value=(kk.get("ketentuan_klarifikasi") or {}).get("media", "Discussion Forum SAPP-SmartGEP")
    )

    p19_2 = c19.add_paragraph()
    p19_2.paragraph_format.space_before = Pt(0)
    p19_2.paragraph_format.space_after = Pt(2)
    r19_2 = p19_2.add_run("Penambahan dan/atau perubahan dokumen dapat dilaksanakan sebanyak: ")
    r19_2.font.name = "Arial"
    r19_2.font.size = Pt(9.5)
    _add_dropdown_control(
        p19_2,
        label="Maksimal Penambahan Dokumen",
        options=[
            "1 (satu) kali",
            "2 (dua) kali",
            "3 (tiga) kali"
        ],
        current_value=(kk.get("ketentuan_klarifikasi") or {}).get("maks_penambahan", "1 (satu) kali")
    )

    p19_3 = c19.add_paragraph()
    p19_3.paragraph_format.space_before = Pt(0)
    p19_3.paragraph_format.space_after = Pt(0)
    r19_3 = p19_3.add_run("Waktu penyampaian penambahan dan/atau perubahan dokumen: ")
    r19_3.font.name = "Arial"
    r19_3.font.size = Pt(9.5)
    _add_dropdown_control(
        p19_3,
        label="Waktu Penyampaian Perbaikan",
        options=[
            "1 (satu) Hari Kerja",
            "2 (dua) Hari Kerja",
            "3 (tiga) Hari Kerja"
        ],
        current_value=(kk.get("ketentuan_klarifikasi") or {}).get("waktu_penyampaian", "1 (satu) Hari Kerja")
    )

    # 20. Parameter Penetapan Pemenang (Dropdown)
    c20 = _add_row("20", "Parameter Penetapan Pemenang", "")
    _add_dropdown_control(
        c20.paragraphs[0],
        label="Parameter Penetapan Pemenang",
        options=[
            "Komersial Terbaik",
            "HEA Terbaik",
            "Score TCO (Total Cost Ownership)/LCC (Life Cycle Costing) Terbaik",
            "Score terbaik kombinasi teknis dan komersial",
            "Score terbaik kombinasi teknis dan HEA",
            "Teknis Terbaik"
        ],
        current_value=kk.get("parameter_penetapan_pemenang", "HEA Terbaik")
    )

    _add_row("21", "Metode Peringkat Peserta", kk.get("metode_peringkat_peserta", "Peringkat Peserta ditentukan dengan metode HEA Terbaik."))
    _add_row("22", "Evaluasi Administrasi", kk.get("evaluasi_administrasi", "Evaluasi administrasi dilakukan dengan metode non-scoring (sistem gugur)."))

    # Row 23: Evaluasi Teknis
    tek_info = kk.get("evaluasi_teknis") or {}
    _add_row("23", "Evaluasi Teknis", [
        f"1. Metode evaluasi teknis adalah {tek_info.get('metode', 'Scoring')}.",
        f"2. Nilai passing grade ditetapkan {tek_info.get('passing_grade', '80 dari skala 100')}.",
        "3. Kriteria dan parameter evaluasi teknis dirinci pada Lampiran 2A."
    ])

    # 24. Sanggahan atas Pengumuman Hasil Evaluasi Fase I (Dropdown)
    c24 = _add_row("24", "Sanggahan atas Pengumuman Hasil Evaluasi Fase I (Administrasi, Teknis, HSSE Plan)", "")
    _add_dropdown_control(
        c24.paragraphs[0],
        label="Sanggahan Evaluasi Fase I",
        options=[
            "Tidak Dibuka Sanggahan Pengumuman Hasil Evaluasi Fase I",
            "Dibuka Sanggahan Pengumuman Hasil Evaluasi Fase I"
        ],
        current_value=kk.get("sanggahan_fase_1", "Tidak Dibuka Sanggahan Pengumuman Hasil Evaluasi Fase I")
    )

    # Row 25: HSSE Plan
    hsse_info = kk.get("evaluasi_hsse_plan") or {}
    _add_row("25", "Persyaratan dan Evaluasi HSSE Plan", [
        f"1. Penilaian risiko pekerjaan aspek HSSE: {hsse_info.get('tingkat_risiko', 'High Risk')}.",
        f"2. Metode Evaluasi HSSE Plan: {hsse_info.get('metode', 'Scoring')}.",
        f"3. Passing Grade: {hsse_info.get('passing_grade', 'Minimal 80% dalam skala 100%')}."
    ])

    # Row 26: TKDN (Dropdown on Item 3)
    tkdn_info = kk.get("evaluasi_tkdn") or {}
    c26 = _add_row("26", "Evaluasi TKDN", "")
    p26_1 = c26.paragraphs[0]
    p26_1.paragraph_format.space_before = Pt(0)
    p26_1.paragraph_format.space_after = Pt(2)
    r26_1 = p26_1.add_run(f"1. Paket Pengadaan ini mempersyaratkan komitmen TKDN Minimal sebesar {tkdn_info.get('minimal_persen', 20.12)}%.")
    r26_1.font.name = "Arial"
    r26_1.font.size = Pt(9.5)

    p26_2 = c26.add_paragraph()
    p26_2.paragraph_format.space_before = Pt(0)
    p26_2.paragraph_format.space_after = Pt(2)
    r26_2 = p26_2.add_run("2. Wajib melampirkan sertifikat TKDN Kemenperin yang masih berlaku untuk komponen barang utama.")
    r26_2.font.name = "Arial"
    r26_2.font.size = Pt(9.5)

    p26_3 = c26.add_paragraph()
    p26_3.paragraph_format.space_before = Pt(0)
    p26_3.paragraph_format.space_after = Pt(0)
    r26_3 = p26_3.add_run("3. Ketentuan preferensi harga: ")
    r26_3.font.name = "Arial"
    r26_3.font.size = Pt(9.5)
    _add_dropdown_control(
        p26_3,
        label="Ketentuan Preferensi Harga",
        options=[
            "Diberikan preferensi",
            "Tidak diberikan preferensi"
        ],
        current_value="Diberikan preferensi" if "Diberikan" in tkdn_info.get("preferensi_harga", "Diberikan") else "Tidak diberikan preferensi"
    )

    # 27. Jenis Kontrak (Dropdown)
    c27 = _add_row("27", "Jenis Kontrak", "")
    _add_dropdown_control(
        c27.paragraphs[0],
        label="Jenis Kontrak",
        options=[
            "Gabungan Harga Satuan & Lumpsum",
            "Harga Lumpsum",
            "Harga Satuan",
            "Harga Satuan (setiap item tidak saling terkait)",
            "Harga Satuan (setiap item tidak saling terkait, untuk kebutuhan security of supply)"
        ],
        current_value=kk.get("jenis_kontrak", "Gabungan Harga Satuan & Lumpsum")
    )

    # 28. Jumlah Pemenang (Dropdown)
    c28 = _add_row("28", "Jumlah Pemenang", "")
    _add_dropdown_control(
        c28.paragraphs[0],
        label="Jumlah Pemenang",
        options=[
            "Single Winner",
            "Multi Winner"
        ],
        current_value=kk.get("jumlah_pemenang", "Single Winner")
    )

    # Row 29: HPS/OE (Dropdown for tipe kontrak)
    hps = kk.get("hps_oe") or {}
    c29 = _add_row("29", "Informasi Nilai HPS/OE", "")
    p29_intro = c29.paragraphs[0]
    p29_intro.paragraph_format.space_before = Pt(0)
    p29_intro.paragraph_format.space_after = Pt(4)
    r29_intro = p29_intro.add_run("Untuk : ")
    r29_intro.font.name = "Arial"
    r29_intro.font.size = Pt(9.5)
    _add_dropdown_control(
        p29_intro,
        label="Tipe Kontrak HPS",
        options=[
            "Gabungan Harga Satuan & Lumpsum",
            "Harga Lumpsum",
            "Harga Satuan"
        ],
        current_value="Gabungan Harga Satuan & Lumpsum"
    )
    r29_col = p29_intro.add_run(" :")
    r29_col.font.name = "Arial"
    r29_col.font.size = Pt(9.5)

    sub_hps = c29.add_table(rows=3, cols=3)
    sub_hps.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx_h, h_text in enumerate(["No.", "Jenis", "Nilai"]):
        c_h = sub_hps.cell(0, idx_h)
        _set_cell_shading(c_h, COLOR_HEADER_BG)
        _set_cell_margins(c_h, top=60, bottom=60, left=80, right=80)
        p = c_h.paragraphs[0]
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True
    
    hps_rows = [
        ("1", "Total nilai Prime Cost", hps.get("prime_cost_str", "Rp13.283.434.534,00")),
        ("2", "Total nilai Prime Cost + Keuntungan & Risiko", hps.get("total_dengan_kr_str", "Rp14.346.100.000,00"))
    ]
    for row_idx, (no, jns, val) in enumerate(hps_rows, start=1):
        for col_idx, text_v in enumerate([no, jns, val]):
            cell_v = sub_hps.cell(row_idx, col_idx)
            _set_cell_margins(cell_v, top=60, bottom=60, left=80, right=80)
            p = cell_v.paragraphs[0]
            r = p.add_run(text_v)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)

    _add_row("30", "Tata Cara Evaluasi Komersial", kk.get("tata_cara_evaluasi_komersial", "Item harga satuan & item harga lumpsum dievaluasi secara Total."))

    # 31. Mekanisme Koreksi Aritmatika (Dropdown)
    c31 = _add_row("31", "Mekanisme Koreksi Aritmatika", "")
    _add_dropdown_control(
        c31.paragraphs[0],
        label="Mekanisme Koreksi Aritmatika",
        options=[
            "Mekanisme 1",
            "Mekanisme 2",
            "Mekanisme 3",
            "Mekanisme 4"
        ],
        current_value=kk.get("mekanisme_koreksi_aritmatika", "Mekanisme 1")
    )

    # Row 32: Negosiasi
    nego = kk.get("ketentuan_negosiasi") or {}
    _add_row("32", "Ketentuan Negosiasi", [
        f"Tata Cara Negosiasi: {nego.get('tata_cara', 'e-Reverse Auction (e-RA)')}",
        f"1. Mekanisme Negosiasi: {nego.get('mekanisme', 'Mekanisme A opsi 1')}",
        f"2. Media Negosiasi: {nego.get('media', 'SAPP - SmartGEP')}"
    ])

    # 33. Sanggahan Pengumuman Hasil Pemilihan Penyedia (Dropdown)
    c33 = _add_row("33", "Sanggahan Pengumuman Hasil Pemilihan Penyedia", "")
    _add_dropdown_control(
        c33.paragraphs[0],
        label="Sanggahan Pengumuman Hasil Pemilihan",
        options=[
            "Tidak dibuka sanggahan Pengumuman Hasil Pemilihan Penyedia",
            "Dibuka sanggahan Pengumuman Hasil Pemilihan Penyedia"
        ],
        current_value="Dibuka sanggahan Pengumuman Hasil Pemilihan Penyedia" if "Dibuka" in str(kk.get("sanggahan_hasil_pemilihan", "")) else "Tidak dibuka sanggahan Pengumuman Hasil Pemilihan Penyedia"
    )

    _add_row("34", "Ketentuan Pemilihan Dinyatakan Gagal", kk.get("ketentuan_tambahan_gagal", "Proses pemilihan dapat dilanjutkan apabila jumlah penawar yang lulus kuorum minimal 2 peserta."))
    _add_row("35", "Eksepsi Rancangan Kontrak", kk.get("eksepsi_rancangan_kontrak", "Tidak diperbolehkan menyampaikan eksepsi atas Rancangan Kontrak."))

    # Row 36: Jaminan (Dropdown on status only)
    c36 = _add_row("36", "Ketentuan Jaminan", "")
    jaminan_items = [
        ("1. ", " Jaminan Sanggahan (2 permil dari penawaran, maks Rp 100 Juta)", "Dipersyaratkan"),
        ("2. ", " Jaminan Pelaksanaan (5% Nilai Kontrak)", "Dipersyaratkan"),
        ("3. ", " Jaminan Uang Muka", "Tidak Dipersyaratkan"),
        ("4. ", " Jaminan Pemeliharaan (5% Nilai Kontrak)", "Dipersyaratkan"),
        ("5. ", " Jaminan Komitmen TKDN", "Dipersyaratkan")
    ]
    for idx_j, (prefix, suffix, default_opt) in enumerate(jaminan_items):
        p_j = c36.paragraphs[0] if idx_j == 0 else c36.add_paragraph()
        p_j.paragraph_format.space_before = Pt(0)
        p_j.paragraph_format.space_after = Pt(2)
        r_pre = p_j.add_run(prefix)
        r_pre.font.name = "Arial"
        r_pre.font.size = Pt(9.5)

        _add_dropdown_control(
            p_j,
            label=f"Status Jaminan {idx_j + 1}",
            options=["Dipersyaratkan", "Tidak Dipersyaratkan"],
            current_value=default_opt
        )

        r_suf = p_j.add_run(suffix)
        r_suf.font.name = "Arial"
        r_suf.font.size = Pt(9.5)

    _add_row("37", "Ketentuan Denda", kk.get("ketentuan_denda", "Diatur sebagaimana Rancangan Kontrak (1 permil per hari keterlambatan, maksimal 5%)."))

    # Row 38: Lampiran IKPP (Dropdown on rows 1, 6, 9, 11, 12)
    lamp_items = [
        ("1A", "Surat Penawaran"),
        ("1B", "Pakta Integritas Peserta (PI-06)"),
        ("1C", "Surat Pernyataan Penyedia Barang/Jasa"),
        ("1D", "Surat Pernyataan Persetujuan Rancangan Kontrak"),
        ("1E", "Surat Pernyataan Kesanggupan Memenuhi Nilai Minimal TKDN"),
        ("1F", "Surat Pernyataan Status Perusahaan"),
        ("2A", "Syarat dan Kriteria Evaluasi Teknis"),
        ("2B", "Dokumen Penawaran Teknis oleh Peserta"),
        ("3A", "Syarat dan Ketentuan Evaluasi HSSE Plan"),
        ("3B", "Penawaran Dokumen HSSE Plan oleh Peserta"),
        ("4",  "Pernyataan Komitmen TKDN"),
        ("5A", "Surat Penawaran Komersial"),
        ("5B", "Rincian Penawaran Harga / Bill of Quantity (BoQ)"),
        ("6",  "Surat Penegasan Harga"),
        ("7",  "Roadmap Komitmen TKDN (Form A6)"),
        ("8",  "Surat Kuasa")
    ]
    c38 = _add_row("38", "Lampiran IKPP", "Daftar Lampiran yang dipergunakan dalam Pemilihan:")
    sub_lamp = c38.add_table(rows=1 + len(lamp_items), cols=3)
    sub_lamp.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx_h, h_text in enumerate(["No", "Jenis Lampiran", "Keterangan"]):
        c_h = sub_lamp.cell(0, idx_h)
        _set_cell_shading(c_h, COLOR_HEADER_BG)
        _set_cell_margins(c_h, top=60, bottom=60, left=80, right=80)
        p = c_h.paragraphs[0]
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True

    lamp_dropdowns = {
        1: [
            "Digunakan 1A-1: Surat Penawaran. Fom 1A-2 tidak perlu disampaikan",
            "Digunakan 1A-2: Surat Penawaran Sampul 1. Fom 1A-1 tidak perlu disampaikan"
        ],
        6: [
            "SKUP MIGAS yang masih berlaku atau Surat Pernyataan Status Perusahaan",
            "SKUP MIGAS atau Surat Pernyataan Status Perusahaan tidak perlu disampaikan"
        ],
        9: [
            "Syarat dan Ketentuan Evaluasi HSSE Plan",
            "Syarat dan Ketentuan Evaluasi HSSE Plan Tidak digunakan"
        ],
        11: [
            "Digunakan Form A3 (Pernyataan Komitmen TKDN dalam Penawaran Barang). Form A4 dan A5 tidak perlu disampaikan",
            "Digunakan Form A4 (Pernyataan Komitmen TKDN dalam Penawaran Jasa). Form A3 dan A5 tidak perlu disampaikan",
            "Digunakan Form A5 (Pernyataan Komitmen TKDN dalam Penawaran Gabungan Barang dan Jasa). Form A3 dan A4 tidak perlu disampaikan",
            "Form A3, A4, dan A5 tidak perlu disampaikan"
        ],
        12: [
            "Surat Penawaran Komersial tidak perlu disampaikan",
            "Surat Penawaran Komersial (khusus untuk metode 2 Sampul)"
        ]
    }

    for idx_l, (no_l, ket_l) in enumerate(lamp_items, start=1):
        r_cells = sub_lamp.rows[idx_l].cells
        for col_i in range(3):
            cell_v = r_cells[col_i]
            _set_cell_margins(cell_v, top=60, bottom=60, left=80, right=80)
            p = cell_v.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if col_i == 0:
                r = p.add_run(str(idx_l))
                r.font.name = "Arial"
                r.font.size = Pt(8)
            elif col_i == 1:
                r = p.add_run(no_l)
                r.font.name = "Arial"
                r.font.size = Pt(8)
            else:
                # Column 2: Keterangan
                if idx_l in lamp_dropdowns:
                    _add_dropdown_control(
                        p,
                        label=f"Lampiran {no_l}",
                        options=lamp_dropdowns[idx_l],
                        current_value=lamp_dropdowns[idx_l][0]
                    )
                else:
                    r = p.add_run(ket_l)
                    r.font.name = "Arial"
                    r.font.size = Pt(8)

    _add_row("39", "Koordinasi Pemilihan", kk.get("koordinasi_pemilihan", "Discussion Forum SAPP-SmartGEP / Chatbot Spartan Procurement: https://ptm.id/spartan"))
    _add_row("40", "Lain-lain (TTE & e-Meterai)", kk.get("lain_lain", "Seluruh Dokumen Penawaran dan Kontrak wajib dibubuhi e-meterai dan Tanda Tangan Elektronik (TTE) tersertifikasi PSrE."))

    doc.add_page_break()


# ──────────────────────────────────────────────────────────────
# 5. BAB II Ketentuan Umum IKPP (30 Articles)
# ──────────────────────────────────────────────────────────────

def _render_bab_ii_ketentuan_umum(doc: Document):
    """Render the 30 standard articles of BAB II Ketentuan Umum IKPP."""
    _add_paragraph(doc, "BAB II KETENTUAN UMUM IKPP", font_size=13, bold=True, space_before=12, space_after=12)

    for art in BAB_II_ARTICLES:
        nomor = art.get("nomor", 1)
        judul = art.get("judul", "")

        # Article heading
        _add_paragraph(doc, f"{nomor}. {judul}", font_size=11, bold=True, space_before=10, space_after=4)

        # Optional intro paragraph
        if "paragraf_intro" in art:
            _add_paragraph(doc, art["paragraf_intro"], font_size=9.5, space_after=4)

        # Definitions list for Article 1
        if "poin" in art:
            for p_num, p_term, p_def in art["poin"]:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.6)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(2)
                r_num = p.add_run(f"{p_num}. ")
                r_num.font.name = "Arial"
                r_num.font.size = Pt(9)
                r_term = p.add_run(f"{p_term} ")
                r_term.font.name = "Arial"
                r_term.font.size = Pt(9)
                r_term.font.bold = True
                r_def = p.add_run(f"adalah {p_def}")
                r_def.font.name = "Arial"
                r_def.font.size = Pt(9)

        # Regular list items
        if "isi" in art:
            for item_text in art["isi"]:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.6)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(2)
                r = p.add_run(item_text)
                r.font.name = "Arial"
                r.font.size = Pt(9.5)

    doc.add_page_break()


# ──────────────────────────────────────────────────────────────
# 6. Lampiran IKPP Renderer
# ──────────────────────────────────────────────────────────────

def _add_kop_surat_banner(doc: Document):
    """Add formal 'DIBUAT PADA KOP SURAT PERUSAHAAN' blue banner."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Cm(16.0)
    _set_cell_shading(cell, "2B547E")
    _set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("DIBUAT PADA KOP SURAT PERUSAHAAN")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.italic = True
    r.font.color.rgb = RGBColor(255, 255, 255)
    _add_paragraph(doc, space_after=8)


def _add_signature_block(doc: Document):
    """Add standard dual TTE PSrE & e-Meterai signature block."""
    _add_paragraph(doc, space_before=12, space_after=6)
    
    table = doc.add_table(rows=3, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_left, c_right = table.cell(0, 0), table.cell(0, 1)
    c_left.width = Cm(8.0)
    c_right.width = Cm(8.0)

    # City & Date
    p_date = c_right.paragraphs[0]
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_d = p_date.add_run("[Kota], ………………………… 20…\n[Nama Perusahaan]\n[Jabatan Penandatangan]")
    r_d.font.name = "Arial"
    r_d.font.size = Pt(9.5)

    # Boxes row (TTE and e-Meterai)
    c_tte = table.cell(1, 1)
    p_box = c_tte.paragraphs[0]
    p_box.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_box.paragraph_format.space_before = Pt(8)
    p_box.paragraph_format.space_after = Pt(8)
    r_box = p_box.add_run("┌───────────────┐     ┌───────────────┐\n│   TTE PSrE    │     │   e-Meterai   │\n└───────────────┘     └───────────────┘")
    r_box.font.name = "Courier New"
    r_box.font.size = Pt(9)
    r_box.font.color.rgb = RGBColor(100, 100, 100)

    # Signer name row
    c_name = table.cell(2, 1)
    p_name = c_name.paragraphs[0]
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_n = p_name.add_run("_______________________________\n(Nama Jelas Penandatangan)")
    r_n.font.name = "Arial"
    r_n.font.size = Pt(9.5)
    r_n.font.bold = True


def _render_lampiran_ikpp(doc: Document, tender_data: dict):
    """Render all formal Lampiran IKPP (1A to 8)."""
    # ── Divider Lampiran ──
    _render_divider_page(doc, ["LAMPIRAN IKPP"])

    # ── Lampiran 1A-1: Surat Penawaran (1 Sampul) ──
    _add_paragraph(doc, "LAMPIRAN 1A-1 (KHUSUS METODE 1 SAMPUL)", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "SURAT PENAWARAN", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    
    surat_p1 = (
        "[Kota], …………………………………\n"
        "Nomor  : ………………………\n"
        "Perihal: Penawaran Pekerjaan Pengadaan\n\n"
        "Kepada Yth,\n"
        "Penyelenggara Pemilihan Penyedia\n"
        "PT Pertamina Patra Niaga\n\n"
        "Menunjuk Dokumen Tender No. : ……………………… Tgl. ……………………\n"
        "Untuk Pekerjaan : …………………………………………………………………\n\n"
        "Yang bertanda tangan di bawah ini:\n"
        "Nama Perusahaan    : …………………………………………………………………\n"
        "Alamat Perusahaan  : …………………………………………………………………\n"
        "Diwakili oleh      : …………………………………………………………………\n"
        "Jabatan            : …………………………………………………………………\n"
        "Akte Notaris No.   : ……………………… Tanggal …………… di ………………\n\n"
        "Menyatakan:\n"
        "1. Setelah membaca dan mempelajari dengan teliti seluruh Dokumen Tender beserta perubahannya dalam Berita Acara Rapat Penjelasan, dengan ini kami menyatakan sanggup melaksanakan pekerjaan dengan nilai total penawaran sebesar:\n"
        "   Rp. ………………………,- (Angka)\n"
        "   Terbilang: ……………………………………………………………………………………………… Rupiah, belum termasuk PPN.\n"
        "2. Harga penawaran tersebut mengikat dan berlaku selama 90 hari kalender sejak pembukaan penawaran.\n"
        "3. Kami tunduk dan mematuhi seluruh Pedoman Pengadaan Barang/Jasa PT Pertamina Patra Niaga No. A03-001/PNG200000/2024-S9 Revisi ke-1."
    )
    _add_paragraph(doc, surat_p1, font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 1B: Pakta Integritas (PI-06) ──
    _add_paragraph(doc, "LAMPIRAN 1B – FORMULIR PI-06", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "PAKTA INTEGRITAS PESERTA", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    pi_text = (
        "Sehubungan dengan keikutsertaan kami dalam proses Pemilihan Penyedia Barang/Jasa di lingkungan PT Pertamina Patra Niaga, dengan ini kami menyatakan:\n\n"
        "1. Semua informasi dan dokumen yang kami sampaikan adalah benar, sah, dan dapat dipertanggungjawabkan.\n"
        "2. Jaminan Kewajaran Harga: Harga yang kami tawarkan adalah wajar, telah mencakup keuntungan, biaya pelaksanaan, dan seluruh pajak yang berlaku (di luar PPN).\n"
        "3. Tidak memiliki benturan kepentingan (conflict of interest) dengan pejabat atau pekerja PT Pertamina Patra Niaga.\n"
        "4. Menjunjung tinggi etika bisnis, mematuhi peraturan Anti-Korupsi, Anti-Penyuapan (ABC/FCPA), dan bersedia dilakukan compliance due diligence sewaktu-waktu.\n"
        "5. Tidak melakukan kecurangan (fraud), persekongkolan tender (kolusi/pinjam bendera), dan bersedia dikenakan sanksi daftar hitam serta sanksi pidana apabila terbukti melanggar."
    )
    _add_paragraph(doc, pi_text, font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 1C: Surat Pernyataan Penyedia ──
    _add_paragraph(doc, "LAMPIRAN 1C", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "SURAT PERNYATAAN PENYEDIA BARANG / JASA", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    sp_text = (
        "Dengan ini menyatakan hal-hal sebagai berikut:\n"
        "1. Bersedia mematuhi seluruh Pedoman Pengadaan Barang/Jasa PT Pertamina Patra Niaga.\n"
        "2. Tidak dalam pengawasan pengadilan, tidak bangkrut/pailit, dan kegiatan usaha tidak sedang dihentikan.\n"
        "3. Direksi dan pengurus perusahaan tidak sedang menjalani sanksi pidana hukum.\n"
        "4. Tidak sedang dalam proses sengketa di peradilan/arbitrase dengan Pertamina Grup.\n"
        "5. Menjaga kerahasiaan seluruh dokumen tender dan tidak menyebarluaskan kepada pihak manapun tanpa izin tertulis Pertamina."
    )
    _add_paragraph(doc, sp_text, font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 1D: Persetujuan Rancangan Kontrak ──
    _add_paragraph(doc, "LAMPIRAN 1D", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "SURAT PERNYATAAN PERSETUJUAN RANCANGAN KONTRAK", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    _add_paragraph(doc, "Dengan ini menyatakan telah membaca, mengerti, memahami, dan menyetujui seluruh klausul dalam Rancangan Kontrak (Bagian B) tanpa eksepsi/persyaratan tambahan apapun.", font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 1E: Kesanggupan TKDN ──
    _add_paragraph(doc, "LAMPIRAN 1E", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "SURAT PERNYATAAN KESANGGUPAN MEMENUHI NILAI MINIMAL TKDN", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    min_tkdn = (tender_data.get("ketentuan_khusus_ikpp") or {}).get("evaluasi_tkdn", {}).get("minimal_persen", 20.12)
    _add_paragraph(doc, f"Dengan ini menyatakan sanggup memenuhi komitmen capaian Tingkat Komponen Dalam Negeri (TKDN) sekurang-kurangnya sebesar {min_tkdn}% sesuai Form A3/A4/A5 yang kami sampaikan.", font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 1F: Status Perusahaan ──
    _add_paragraph(doc, "LAMPIRAN 1F", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "SURAT PERNYATAAN STATUS PERUSAHAAN DALAM NEGERI", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    _add_paragraph(doc, "Dengan ini menyatakan bahwa status perusahaan kami adalah Perusahaan Dalam Negeri yang dibuktikan dengan kepemilikan SKUP Migas / Akta Pendirian Republik Indonesia.", font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 2A: Dynamic Syarat & Kriteria Evaluasi Teknis ──
    _add_paragraph(doc, "LAMPIRAN 2A", font_size=11, bold=True, space_after=4)
    _add_paragraph(doc, "SYARAT DAN KRITERIA EVALUASI TEKNIS", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    _add_paragraph(doc, "Instruksi: Evaluasi teknis dilaksanakan menggunakan metode Scoring (Passing Grade 80 dari skala 100).", font_size=9.5, italic=True, space_after=8)

    tek_items = tender_data.get("lampiran_2a_evaluasi_teknis") or [
        {"no": 1, "kriteria": "Metode Kerja & Rencana Pelaksanaan", "dokumen_diperlukan": "Dokumen Metode Kerja dan Construction Schedule", "parameter_evaluasi": "Kesesuaian tahapan kerja dengan lingkup proyek dan kurva S realistis", "bobot": 25},
        {"no": 2, "kriteria": "Kualifikasi Tenaga Ahli Utama", "dokumen_diperlukan": "Curriculum Vitae, Ijazah, dan Sertifikat Keahlian (SKA)", "parameter_evaluasi": "Memenuhi syarat kompetensi Project Manager, HSE Officer, dan Site Engineer", "bobot": 25},
        {"no": 3, "kriteria": "Ketersediaan Peralatan Kerja Utama", "dokumen_diperlukan": "Daftar Kepemilikan/Sewa Alat dan Sertifikat Kelaikan (SILO)", "parameter_evaluasi": "Peralatan utama laik operasi dan memenuhi spesifikasi teknis lapangan", "bobot": 25},
        {"no": 4, "kriteria": "Jadwal Pelaksanaan & Mobilisasi", "dokumen_diperlukan": "Barchart jadwal mobilisasi personel, alat, dan material", "parameter_evaluasi": "Waktu mobilisasi tidak melebihi jangka waktu yang dipersyaratkan", "bobot": 25}
    ]

    t2a = doc.add_table(rows=1 + len(tek_items), cols=5)
    t2a.alignment = WD_TABLE_ALIGNMENT.CENTER
    t2a_widths = (Cm(1.2), Cm(4.0), Cm(4.5), Cm(5.5), Cm(1.5))
    headers_2a = ["No", "Kriteria Evaluasi", "Dokumen yang Diperlukan", "Parameter Evaluasi", "Bobot"]
    
    for idx_h, h_text in enumerate(headers_2a):
        cell_h = t2a.cell(0, idx_h)
        cell_h.width = t2a_widths[idx_h]
        _set_cell_shading(cell_h, COLOR_HEADER_BG)
        _set_cell_margins(cell_h, top=80, bottom=80, left=100, right=100)
        p = cell_h.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True

    for row_idx, item in enumerate(tek_items, start=1):
        row_cells = t2a.rows[row_idx].cells
        for col_idx, (w, val) in enumerate(zip(t2a_widths, [
            str(item.get("no", row_idx)),
            str(item.get("kriteria", "")),
            str(item.get("dokumen_diperlukan", "")),
            str(item.get("parameter_evaluasi", "")),
            f"{item.get('bobot', '')}%" if item.get('bobot') else "-"
        ])):
            c = row_cells[col_idx]
            c.width = w
            _set_cell_margins(c, top=80, bottom=80, left=100, right=100)
            _set_cell_border(c, top={"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY},
                                bottom={"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY},
                                left={"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY},
                                right={"sz": "4", "val": "single", "color": COLOR_LIGHT_GRAY})
            p = c.paragraphs[0]
            if col_idx in (0, 4):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)

    doc.add_page_break()

    # ── Lampiran 3A: Syarat & Ketentuan Evaluasi HSSE Plan (CSMS Matrix) ──
    _add_paragraph(doc, "LAMPIRAN 3A", font_size=11, bold=True, space_after=4)
    _add_paragraph(doc, "SYARAT DAN KETENTUAN EVALUASI HSSE PLAN (MATRIKS CSMS)", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    _add_paragraph(doc, "Ambang Batas / Passing Grade kelulusan evaluasi HSSE Plan adalah minimal skor 80 dari 100 (Total Bobot 292 poin dinormalisasi).", font_size=9.5, italic=True, space_after=8)

    csms_table = doc.add_table(rows=1, cols=4)
    csms_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    csms_widths = (Cm(1.2), Cm(10.5), Cm(2.2), Cm(2.5))
    for idx_h, h_text in enumerate(["No", "Komponen Penilaian HSSE Plan", "Bobot", "Pencapaian"]):
        c_h = csms_table.cell(0, idx_h)
        c_h.width = csms_widths[idx_h]
        _set_cell_shading(c_h, COLOR_HEADER_BG)
        _set_cell_margins(c_h, top=80, bottom=80, left=100, right=100)
        p = c_h.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True

    for sec in CSMS_MATRIX_DATA:
        # Header for section
        r_sec = csms_table.add_row()
        c_sec = r_sec.cells[0]
        _set_cell_shading(c_sec, "E8EFF7")
        p_sec = c_sec.paragraphs[0]
        r = p_sec.add_run(sec["section"])
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True
        
        # Merge across columns
        c_sec.merge(r_sec.cells[1])
        c_bobot = r_sec.cells[2]
        _set_cell_shading(c_bobot, "E8EFF7")
        p_b = c_bobot.paragraphs[0]
        p_b.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_b = p_b.add_run(str(sec["sub_total_bobot"]))
        r_b.font.name = "Arial"
        r_b.font.size = Pt(8.5)
        r_b.font.bold = True

        for idx_it, it in enumerate(sec["items"], start=1):
            r_it = csms_table.add_row()
            r_it.cells[0].width = csms_widths[0]
            r_it.cells[1].width = csms_widths[1]
            r_it.cells[2].width = csms_widths[2]
            r_it.cells[3].width = csms_widths[3]
            
            p0 = r_it.cells[0].paragraphs[0]
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r0 = p0.add_run(str(idx_it))
            r0.font.name = "Arial"
            r0.font.size = Pt(8)

            p1 = r_it.cells[1].paragraphs[0]
            r1 = p1.add_run(it)
            r1.font.name = "Arial"
            r1.font.size = Pt(8)

    doc.add_page_break()

    # ── Lampiran 4: Form A3 / A4 / A5 (TKDN Tables) ──
    _add_paragraph(doc, "LAMPIRAN 4", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "FORM A5: PERNYATAAN KOMITMEN TKDN GABUNGAN BARANG DAN JASA", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

    tkdn_table = doc.add_table(rows=7, cols=5)
    tkdn_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tkdn_widths = (Cm(1.2), Cm(6.5), Cm(3.0), Cm(3.0), Cm(2.5))
    tkdn_headers = ["No", "Komponen Biaya", "KDN (Rupiah)", "KLN (Rupiah)", "% TKDN"]
    for idx_h, h_text in enumerate(tkdn_headers):
        c_h = tkdn_table.cell(0, idx_h)
        c_h.width = tkdn_widths[idx_h]
        _set_cell_shading(c_h, COLOR_HEADER_BG)
        _set_cell_margins(c_h, top=80, bottom=80, left=100, right=100)
        p = c_h.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True

    tkdn_rows = [
        ("I", "Komponen Barang (Material Langsung + Peralatan Jadi)", "", "", ""),
        ("II", "Komponen Jasa (Manajemen Proyek + Tenaga Ahli + Alat Kerja)", "", "", ""),
        ("III", "Total Biaya Barang + Jasa", "", "", ""),
        ("IV", "Komponen Bukan Biaya (Keuntungan & Overhead)", "-", "-", "-"),
        ("V", "TOTAL NILAI PENAWARAN", "", "", "")
    ]
    for idx_r, (no, kom, kdn, kln, pct) in enumerate(tkdn_rows, start=1):
        for col_i, text_v in enumerate([no, kom, kdn, kln, pct]):
            cell_v = tkdn_table.cell(idx_r, col_i)
            cell_v.width = tkdn_widths[col_i]
            _set_cell_margins(cell_v, top=80, bottom=80, left=100, right=100)
            p = cell_v.paragraphs[0]
            if col_i in (0, 4):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(text_v)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)
            if idx_r in (3, 5):
                r.font.bold = True

    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 5B: BoQ Template ──
    _add_paragraph(doc, "LAMPIRAN 5B", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "RINCIAN PENAWARAN HARGA / BILL OF QUANTITY (BoQ)", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    _add_paragraph(doc, "Instruksi: Peserta wajib mengisi dan melampirkan rincian penawaran harga sesuai format BoQ dalam format Scan PDF dan Microsoft Excel.", font_size=9.5, italic=True, space_after=12)

    boq_table = doc.add_table(rows=6, cols=6)
    boq_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    boq_widths = (Cm(1.0), Cm(6.5), Cm(1.5), Cm(1.8), Cm(3.0), Cm(3.0))
    for idx_h, h_text in enumerate(["No", "Uraian Pekerjaan", "Vol", "Satuan", "Harga Satuan (Rp)", "Total Harga (Rp)"]):
        c_h = boq_table.cell(0, idx_h)
        c_h.width = boq_widths[idx_h]
        _set_cell_shading(c_h, COLOR_HEADER_BG)
        _set_cell_margins(c_h, top=80, bottom=80, left=100, right=100)
        p = c_h.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True

    boq_items = [
        ("1", "Pekerjaan Persiapan, Mobilisasi & Demobilisasi", "1", "LS", "...", "..."),
        ("2", "Pekerjaan Implementasi HSSE & Safety Equipment", "1", "LS", "...", "..."),
        ("3", "Pekerjaan Utama Teknis Konstruksi / Instalasi", "1", "Paket", "...", "..."),
        ("4", "Pekerjaan Testing, Commissioning & Pelaporan", "1", "LS", "...", "..."),
        ("", "TOTAL NILAI PENAWARAN (Belum termasuk PPN)", "", "", "", "...")
    ]
    for idx_r, row_data in enumerate(boq_items, start=1):
        for col_i, text_v in enumerate(row_data):
            cell_v = boq_table.cell(idx_r, col_i)
            cell_v.width = boq_widths[col_i]
            _set_cell_margins(cell_v, top=80, bottom=80, left=100, right=100)
            p = cell_v.paragraphs[0]
            if col_i in (0, 2, 3):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif col_i in (4, 5):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = p.add_run(text_v)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)
            if idx_r == 5:
                r.font.bold = True

    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 6: Surat Penegasan Harga ──
    _add_paragraph(doc, "LAMPIRAN 6", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "SURAT PENEGASAN HARGA", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    _add_paragraph(doc, "Dibuat oleh Peserta yang menjadi Calon Pemenang setelah pelaksanaan negosiasi harga atau klarifikasi harga timpang.", font_size=9.5, italic=True, space_after=8)
    sph_text = (
        "Sehubungan dengan hasil negosiasi harga pelaksanaan pekerjaan, dengan ini kami menegaskan bahwa harga final penawaran kami adalah:\n\n"
        "Nilai Pekerjaan: Rp. ………………………,- (belum termasuk PPN)\n"
        "Terbilang      : ……………………………………………………………………………………………………………… Rupiah.\n\n"
        "Harga tersebut adalah wajar, mengikat, dan apabila kami ditunjuk sebagai Pemenang, kami siap menandatangani Kontrak dan melaksanakan seluruh pekerjaan sesuai spesifikasi teknis Dokumen Tender."
    )
    _add_paragraph(doc, sph_text, font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Lampiran 8: Surat Kuasa ──
    _add_paragraph(doc, "LAMPIRAN 8", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "SURAT KUASA KHUSUS", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    sk_text = (
        "Yang bertanda tangan di bawah ini Direktur Utama/Pimpinan Perusahaan memberi kuasa penuh kepada:\n\n"
        "Nama      : ………………………………………………………\n"
        "Jabatan   : ………………………………………………………\n"
        "No. KTP   : ………………………………………………………\n\n"
        "Untuk bertindak mewakili Perusahaan dalam menghadiri Rapat Penjelasan (Pre-bid meeting), pembukaan penawaran, klarifikasi teknis, negosiasi harga (e-RA), dan menandatangani dokumen penawaran."
    )
    _add_paragraph(doc, sk_text, font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()


# ──────────────────────────────────────────────────────────────
# 7. BAGIAN B: Rancangan Kontrak (Full Draft Contract)
# ──────────────────────────────────────────────────────────────

def _render_bagian_b_rancangan_kontrak(doc: Document, tender_data: dict):
    """Render BAGIAN B: Full Draft Contract (Pasal 1 - 18, PI-07, SP3MK)."""
    # ── Divider Bagian B ──
    _render_divider_page(doc, [
        "BAGIAN B",
        "RANCANGAN KONTRAK",
        "Pakta Integritas Pelaksana Kontrak (PI-07)",
        "Template SP3MK"
    ])

    cover = tender_data.get("cover_page") or {}
    rk_data = tender_data.get("rancangan_kontrak") or {}
    hps = (tender_data.get("ketentuan_khusus_ikpp") or {}).get("hps_oe") or {}

    judul_kontrak = rk_data.get("judul_pekerjaan", cover.get("nama_pengadaan", "PENGADAAN JASA / BARANG")).upper()
    nomor_kontrak = rk_data.get("nomor_kontrak", "KTR-001/PND970000/2026-S7")

    # Contract Title Header
    _add_paragraph(doc, "PERJANJIAN PELAKSANAAN PEKERJAAN", font_size=14, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=2)
    _add_paragraph(doc, f"TENTANG\n{judul_kontrak}", font_size=13, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _add_paragraph(doc, f"NOMOR: {nomor_kontrak}", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

    # Opening Comparison / Parties
    komparisi = (
        "Pada hari ini, ……………… tanggal ………… bulan ………… tahun Dua Ribu Dua Puluh Enam, bertempat di Balikpapan, "
        "yang bertanda tangan di bawah ini:\n\n"
        "I. PT PERTAMINA PATRA NIAGA, suatu perseroan terbatas yang didirikan berdasarkan hukum Republik Indonesia, "
        "berkedudukan di Jakarta, dalam hal ini diwakili oleh Senior Manager / General Manager yang bertindak berdasarkan "
        "Surat Kuasa Direksi, selanjutnya disebut \"PERTAMINA\".\n\n"
        "II. [NAMA PENYEDIA PEMENANG], suatu badan usaha yang berkedudukan di [Alamat Perusahaan], dalam hal ini diwakili oleh "
        "[Nama Direktur Utama] bertindak dalam kedudukannya selaku Direktur Utama, selanjutnya disebut \"PELAKSANA KONTRAK\".\n\n"
        "PERTAMINA dan PELAKSANA KONTRAK secara bersama-sama selanjutnya disebut \"PARA PIHAK\"."
    )
    _add_paragraph(doc, komparisi, font_size=9.5, space_after=12)

    # Recitals / Premis
    premis = (
        "MENIMBANG:\n"
        f"a. Bahwa PERTAMINA telah menyelenggarakan proses Pemilihan Penyedia untuk pekerjaan {judul_kontrak} berdasarkan Dokumen Tender Nomor {cover.get('nomor_tender', '...')};\n"
        "b. Bahwa PELAKSANA KONTRAK telah dinyatakan sebagai Pemenang Pemilihan Penyedia berdasarkan Surat Penunjukan Penyedia Barang/Jasa (SPPBJ);\n"
        "c. Bahwa PELAKSANA KONTRAK telah menyerahkan Jaminan Pelaksanaan yang sah dan dapat diterima oleh PERTAMINA;\n\n"
        "MAKA OLEH KARENA ITU, PARA PIHAK sepakat untuk membuat dan menandatangani Perjanjian ini dengan syarat-syarat dan ketentuan sebagai berikut:"
    )
    _add_paragraph(doc, premis, font_size=9.5, space_after=14)

    # Render Articles 1 to 18
    for art in CONTRACT_ARTICLES:
        p_no = art["pasal"]
        p_jud = art["judul"]
        _add_paragraph(doc, f"PASAL {p_no}\n{p_jud}", font_size=11, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_before=10, space_after=4)

        for line in art["isi"]:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(line)
            r.font.name = "Arial"
            r.font.size = Pt(9.5)

    # Closing Signature Area for Bagian B Contract
    _add_paragraph(doc, space_before=16, space_after=6)
    sig_tab = doc.add_table(rows=3, cols=2)
    sig_tab.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_p1, c_p2 = sig_tab.cell(0, 0), sig_tab.cell(0, 1)
    c_p1.width = Cm(8.0)
    c_p2.width = Cm(8.0)

    p1 = c_p1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p1.add_run("Untuk dan atas nama\nPT PERTAMINA PATRA NIAGA")
    r1.font.name = "Arial"
    r1.font.size = Pt(10)
    r1.font.bold = True

    p2 = c_p2.paragraphs[0]
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("Untuk dan atas nama\nPELAKSANA KONTRAK")
    r2.font.name = "Arial"
    r2.font.size = Pt(10)
    r2.font.bold = True

    # Spacing for signature
    sig_tab.cell(1, 0).paragraphs[0].paragraph_format.space_before = Pt(50)
    sig_tab.cell(1, 1).paragraphs[0].paragraph_format.space_before = Pt(50)

    # Names
    pn1 = sig_tab.cell(2, 0).paragraphs[0]
    pn1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rn1 = pn1.add_run("_______________________________\nPejabat Berwenang Pertamina")
    rn1.font.name = "Arial"
    rn1.font.size = Pt(10)
    rn1.font.bold = True

    pn2 = sig_tab.cell(2, 1).paragraphs[0]
    pn2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rn2 = pn2.add_run("_______________________________\nDirektur Utama")
    rn2.font.name = "Arial"
    rn2.font.size = Pt(10)
    rn2.font.bold = True

    doc.add_page_break()

    # ── Pakta Integritas Pelaksana Kontrak (PI-07) ──
    _add_paragraph(doc, "LAMPIRAN KONTRAK I: PAKTA INTEGRITAS PELAKSANA KONTRAK (PI-07)", font_size=11, bold=True, space_after=4)
    _add_kop_surat_banner(doc)
    _add_paragraph(doc, "PAKTA INTEGRITAS PELAKSANA KONTRAK", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    pi07_text = (
        "Sehubungan dengan pelaksanaan Perjanjian Pengadaan Barang/Jasa, Pelaksana Kontrak menyatakan:\n\n"
        "1. Menjamin bahwa seluruh barang/jasa yang diserahkan memenuhi spesifikasi teknis, standar mutu, dan dalam kondisi 100% baru serta laik operasi.\n"
        "2. Mematuhi standar keselamatan kerja CSMS, Corporate Life Saving Rules Pertamina, dan mencegah terjadinya kecelakaan kerja maupun pencemaran lingkungan.\n"
        "3. Mematuhi komitmen capaian TKDN sesuai kontrak dan bersedia diaudit oleh surveyor independen.\n"
        "4. Menolak segala bentuk suap, gratifikasi, atau pemberian apapun kepada pekerja Pertamina, serta mematuhi ketentuan Good Corporate Governance."
    )
    _add_paragraph(doc, pi07_text, font_size=9.5, space_after=8)
    _add_signature_block(doc)
    doc.add_page_break()

    # ── Template SP3MK ──
    _add_paragraph(doc, "LAMPIRAN KONTRAK II: TEMPLATE SP3MK", font_size=11, bold=True, space_after=4)
    _add_paragraph(doc, "SURAT PERINTAH PELAKSANAAN PEKERJAAN MENDAHULUI KONTRAK (SP3MK)", font_size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    sp3mk_text = (
        "Nomor: SP3MK-……/PND970000/2026-S7\n\n"
        "Kepada: [Nama Penyedia Pemenang]\n"
        "Alamat: [Alamat Penyedia]\n\n"
        "Berdasarkan Surat Penunjukan Pemenang Pengadaan dan mempertimbangkan urgensi penyelesaian operasional lapangan, "
        "dengan ini PERTAMINA memerintahkan PELAKSANA KONTRAK untuk segera memulai pelaksanaan pekerjaan:\n\n"
        f"Pekerjaan : {judul_kontrak}\n"
        f"Lokasi    : Sebagaimana diatur dalam Dokumen Tender\n"
        "Waktu     : Terhitung sejak tanggal diterbitkannya SP3MK ini.\n\n"
        "Ketentuan yang mengikat Para Pihak selama berlakunya SP3MK ini adalah seluruh persyaratan yang tercantum dalam "
        "Dokumen Tender dan Berita Acara Klarifikasi/Negosiasi sampai dengan penandatanganan Perjanjian Kontrak definitif."
    )
    _add_paragraph(doc, sp3mk_text, font_size=9.5, space_after=16)

    # Signer for SP3MK
    sp_tab = doc.add_table(rows=2, cols=1)
    sp_tab.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_sp = sp_tab.cell(0, 0)
    cell_sp.width = Cm(8.0)
    p_sp = cell_sp.paragraphs[0]
    p_sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sp = p_sp.add_run("PT PERTAMINA PATRA NIAGA\nPejabat Berwenang\n\n\n\n\n_______________________________")
    r_sp.font.name = "Arial"
    r_sp.font.size = Pt(10)
    r_sp.font.bold = True


# ──────────────────────────────────────────────────────────────
# Main Render Function
# ──────────────────────────────────────────────────────────────

def render_tender_to_docx(tender_data: dict, output_filename: str = "") -> str:
    """
    Render the complete Dokumen Tender Pertamina Patra Niaga into a professionally
    formatted .docx file using pure python-docx without requiring a pre-existing template file.

    Args:
        tender_data: Complete tender dictionary conforming to DokumenTenderData schema
        output_filename: Optional output filename (auto-generated if empty)

    Returns:
        str: Absolute path to the generated .docx file
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()

    # ── Page Setup: Margins ──
    for section in doc.sections:
        section.top_margin = Cm(3.0)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.5)

    # ── Default Styles ──
    style = doc.styles['Normal']
    font = style.font
    font.name = "Arial"
    font.size = Pt(10)

    # ── 1. Cover Page ──
    _render_cover_page(doc, tender_data)

    # ── 2. Bagian A Divider ──
    _render_divider_page(doc, [
        "BAGIAN A",
        "INSTRUKSI DAN KETENTUAN",
        "PELAKSANAAN PEMILIHAN (IKPP)"
    ])

    # ── Setup Headers & Footers for Content Section ──
    # New section for body pages to have official header & footer
    body_section = doc.add_section()
    body_section.top_margin = Cm(2.5)
    body_section.bottom_margin = Cm(2.5)
    body_section.left_margin = Cm(2.5)
    body_section.right_margin = Cm(2.5)
    _remove_page_border(body_section)

    nomor_tender = (tender_data.get("cover_page") or {}).get("nomor_tender", "")
    _setup_tender_header_footer(body_section, doc_number=nomor_tender)

    # ── 3. Table of Contents ──
    _render_table_of_contents(doc)

    # ── 4. BAB I Ketentuan Khusus IKPP (40 Points) ──
    _render_bab_i_ketentuan_khusus(doc, tender_data)

    # ── 5. BAB II Ketentuan Umum IKPP (30 Articles) ──
    _render_bab_ii_ketentuan_umum(doc)

    # ── 6. Lampiran IKPP (1A to 8) ──
    _render_lampiran_ikpp(doc, tender_data)

    # ── 7. BAGIAN B: Rancangan Kontrak (Pasal 1 - 18, PI-07, SP3MK) ──
    _render_bagian_b_rancangan_kontrak(doc, tender_data)

    # ── Determine output filename ──
    if not output_filename:
        nama_pengadaan = (tender_data.get("cover_page") or {}).get("nama_pengadaan", "Dokumen_Tender")
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_"
            for c in nama_pengadaan
        )[:50].strip()
        output_filename = f"Dokumen_Tender_{safe_name}.docx"

    if not output_filename.endswith(".docx"):
        output_filename += ".docx"

    output_path = OUTPUT_DIR / output_filename
    doc.save(str(output_path))

    return str(output_path.resolve())