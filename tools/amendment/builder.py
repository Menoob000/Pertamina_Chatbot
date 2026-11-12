"""Pure python-docx builder for Pertamina Contract Amendment Documents."""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def angka_ke_terbilang(bilangan: int | float) -> str:
    """Konversi angka ke kalimat terbilang Bahasa Indonesia."""
    satuan = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]
    bilangan = int(bilangan)

    if bilangan < 12:
        return satuan[bilangan]
    elif bilangan < 20:
        return f"{angka_ke_terbilang(bilangan - 10)} belas"
    elif bilangan < 100:
        return f"{angka_ke_terbilang(bilangan // 10)} puluh {angka_ke_terbilang(bilangan % 10)}".strip()
    elif bilangan < 200:
        return f"seratus {angka_ke_terbilang(bilangan - 100)}".strip()
    elif bilangan < 1000:
        return f"{angka_ke_terbilang(bilangan // 100)} ratus {angka_ke_terbilang(bilangan % 100)}".strip()
    elif bilangan < 2000:
        return f"seribu {angka_ke_terbilang(bilangan - 1000)}".strip()
    elif bilangan < 1000000:
        return f"{angka_ke_terbilang(bilangan // 1000)} ribu {angka_ke_terbilang(bilangan % 1000)}".strip()
    elif bilangan < 1000000000:
        return f"{angka_ke_terbilang(bilangan // 1000000)} juta {angka_ke_terbilang(bilangan % 1000000)}".strip()
    elif bilangan < 1000000000000:
        return f"{angka_ke_terbilang(bilangan // 1000000000)} miliar {angka_ke_terbilang(bilangan % 1000000000)}".strip()
    elif bilangan < 1000000000000000:
        return f"{angka_ke_terbilang(bilangan // 1000000000000)} triliun {angka_ke_terbilang(bilangan % 1000000000000)}".strip()
    return str(bilangan)


def format_rupiah_lengkap(nominal: int | float) -> tuple[str, str]:
    """Mengembalikan format nominal angka (Rp...) dan kalimat terbilang (huruf)."""
    nominal_int = int(nominal)
    formatted_angka = f"Rp{nominal_int:,}".replace(",", ".") + ",-"
    terbilang_str = f"({angka_ke_terbilang(nominal_int)} rupiah)"
    return formatted_angka, terbilang_str


def set_cell_border(cell, **kwargs):
    """Set cell borders; kwargs: top, bottom, left, right with values like {'sz': 12, 'val': 'single', 'color': 'FF0000'}"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for border_name, border_props in kwargs.items():
        border = OxmlElement(f'w:{border_name}')
        for key, val in border_props.items():
            border.set(qn(f'w:{key}'), str(val))
        tcBorders.append(border)
    tcPr.append(tcBorders)


def clear_cell_borders(cell):
    """Menghapus semua garis batas cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_el = OxmlElement(f'w:{edge}')
        edge_el.set(qn('w:val'), 'none')
        tcBorders.append(edge_el)
    tcPr.append(tcBorders)


def build_amendment_docx(params: Dict[str, Any]) -> bytes:
    """
    Generate dokumen amandemen kontrak lengkap berbasis python-docx.
    Struktur dan tata letak 100% mengikuti standar resmi contoh PDF IKN.
    """
    doc = Document()

    # 1. Page Margins Setup
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

        # Running Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        amendment_level = params.get("amendment_level", "AMENDEMEN II").upper()
        project_name = params.get("project_name", "Pembangunan DPPU Nusantara Ibu Kota Negara (IKN) – Penajam Paser Utara")
        hrun = hp.add_run(f"{amendment_level} {project_name}")
        hrun.font.name = "Arial"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(100, 100, 100)

        # Running Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        frun = fp.add_run(f"{amendment_level} {project_name}")
        frun.font.name = "Arial"
        frun.font.size = Pt(8)
        frun.font.color.rgb = RGBColor(120, 120, 120)

    # 2. Main Title Section
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    r = title_p.add_run("POKOK-POKOK KONTRAK\n")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(11)

    r2 = title_p.add_run(f"{project_name.upper()}\n")
    r2.bold = True
    r2.font.name = "Arial"
    r2.font.size = Pt(11)

    company_name = params.get("company_name", "PT PERTAMINA PATRA NIAGA")
    contractor_name = params.get("contractor_name", "PT PGAS SOLUTION")

    r3 = title_p.add_run("ANTARA\n")
    r3.bold = True
    r3.font.name = "Arial"
    r3.font.size = Pt(10)

    r4 = title_p.add_run(f"{company_name.upper()}\n")
    r4.bold = True
    r4.font.name = "Arial"
    r4.font.size = Pt(11)

    r5 = title_p.add_run("DENGAN\n")
    r5.bold = True
    r5.font.name = "Arial"
    r5.font.size = Pt(10)

    r6 = title_p.add_run(f"{contractor_name.upper()}\n")
    r6.bold = True
    r6.font.name = "Arial"
    r6.font.size = Pt(11)

    contract_ref = params.get("contract_ref", "SP-068/PND900000/2024-S0")
    r7 = title_p.add_run(f"Ref. Kontrak No.{contract_ref}")
    r7.font.name = "Arial"
    r7.font.size = Pt(10.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # 3. Preamble Paragraph
    tanggal_amendemen = params.get("tanggal_amendemen", "TANGGAL AMENDEMEN II")
    p_intro = doc.add_paragraph()
    p_intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_intro.paragraph_format.space_after = Pt(8)
    p_intro.paragraph_format.line_spacing = 1.15

    r = p_intro.add_run(f"{amendment_level} {project_name} (“")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_intro.add_run("AMENDEMEN")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_intro.add_run(f"”) ini dibuat dan ditandatangani pada {tanggal_amendemen}, oleh dan antara:\n")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # Party I - PERUSAHAAN
    company_office = params.get("company_office", "Jakarta Selatan dan berkantor pusat di Gedung Wisma Tugu II Lantai 2, Jalan HR. Rasuna Said Kav. C7-9, Kota Administrasi Jakarta Selatan, Provinsi DKI Jakarta")
    company_rep = params.get("company_rep_name", "Riki Madyanto")
    company_rep_title = params.get("company_rep_title", "Sr. Manager Opt. & Maint. Kalimantan")

    p_part1 = doc.add_paragraph()
    p_part1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_part1.paragraph_format.left_indent = Inches(0.4)
    p_part1.paragraph_format.space_after = Pt(6)
    p_part1.paragraph_format.line_spacing = 1.15
    r = p_part1.add_run("I.  ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run(f"{company_name}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run(f", suatu perusahaan yang didirikan berdasarkan hukum Indonesia, berkedudukan di {company_office}, dalam hal ini diwakili oleh ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run(f"{company_rep}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run(f" selaku ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run(f"{company_rep_title}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run(f", dengan demikian berwenang bertindak untuk dan atas nama {company_name}, untuk selanjutnya dalam {amendment_level} ini disebut ”")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run("PERUSAHAAN")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part1.add_run("”, dan")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # Party II - KONTRAKTOR
    contractor_office = params.get("contractor_office", "Jakarta Pusat dan berkantor pusat di Jakarta")
    contractor_rep = params.get("contractor_rep_name", "Heru Indriatno")
    contractor_rep_title = params.get("contractor_rep_title", "Direktur Teknik dan Pengembangan")

    p_part2 = doc.add_paragraph()
    p_part2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_part2.paragraph_format.left_indent = Inches(0.4)
    p_part2.paragraph_format.space_after = Pt(8)
    p_part2.paragraph_format.line_spacing = 1.15
    r = p_part2.add_run("II. ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run(f"{contractor_name}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run(f", suatu perusahaan yang didirikan berdasarkan hukum Indonesia, berkedudukan di {contractor_office}, dalam hal ini diwakili oleh ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run(f"{contractor_rep}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run(f" selaku ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run(f"{contractor_rep_title}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run(f", dengan demikian berwenang bertindak untuk dan atas nama {contractor_name} untuk selanjutnya dalam {amendment_level} ini disebut “")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run("KONTRAKTOR")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_part2.add_run("”.")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    p_pihak = doc.add_paragraph()
    p_pihak.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_pihak.paragraph_format.space_after = Pt(10)
    r = p_pihak.add_run("Selanjutnya ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run("PERUSAHAAN")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run(" dan ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run("KONTRAKTOR")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run(" secara sendiri-sendiri disebut “")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run("PIHAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run("” dan secara bersama-sama disebut “")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run("PARA PIHAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_pihak.add_run("”.")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # 4. BAHWASANYA
    p_bahwa = doc.add_paragraph()
    p_bahwa.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_bahwa.paragraph_format.space_before = Pt(4)
    p_bahwa.paragraph_format.space_after = Pt(6)
    r = p_bahwa.add_run("BAHWASANYA;")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)

    contract_date = params.get("contract_date", "25 April 2024")
    prev_amendment_date = params.get("prev_amendment_date", "15 Agustus 2025")

    # Item 1
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p1.paragraph_format.left_indent = Inches(0.4)
    p1.paragraph_format.space_after = Pt(4)
    r = p1.add_run("1.  ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p1.add_run("PARA PIHAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p1.add_run(f" sebelumnya menandatangani Pokok-Pokok Kontrak {project_name} No. {contract_ref} tanggal {contract_date} (“")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p1.add_run("KONTRAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p1.add_run("”);")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # Item 2 (Previous Amendment if exists)
    if "II" in amendment_level or "III" in amendment_level or "IV" in amendment_level or "KE-2" in amendment_level:
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p2.paragraph_format.left_indent = Inches(0.4)
        p2.paragraph_format.space_after = Pt(4)
        r = p2.add_run("2.  ")
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r = p2.add_run("PARA PIHAK")
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r = p2.add_run(f" sebelumnya menandatangani Amendemen Pokok-Pokok Kontrak {project_name} No. {contract_ref} tanggal {prev_amendment_date} (“")
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r = p2.add_run("AMENDEMEN")
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r = p2.add_run("”);")
        r.font.name = "Arial"
        r.font.size = Pt(10)

    # Item 3: Basis of amendment
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p3.paragraph_format.left_indent = Inches(0.4)
    p3.paragraph_format.space_after = Pt(4)
    idx_num = "3" if ("II" in amendment_level or "III" in amendment_level or "KE-2" in amendment_level) else "2"
    r = p3.add_run(f"{idx_num}.  ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p3.add_run("PARA PIHAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p3.add_run(" bermaksud untuk melakukan perubahan ketentuan dalam ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p3.add_run("KONTRAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p3.add_run(" berdasarkan dokumen-dokumen sebagai berikut:")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # Basis documents (a, b, c, d)
    dasar_dokumen = params.get("dasar_dokumen", [
        f"Surat KONTRAKTOR kepada PERUSAHAAN No.10150.S/DPPU-IKN/PGAS/XI/2025 tanggal 21 November 2025 perihal Revisi Penawaran Harga dan Waktu pada {project_name};",
        f"Notulen Rapat No.NR-794/PND95C000/2025-S5 tanggal 13 Oktober 2025 perihal War Room dan Pembahasan Pengajuan Amendemen Pekerjaan {project_name};",
        f"Notulen Rapat No.NR-950/PND95C000/2025-S5 tanggal 18 November 2025 perihal Pembahasan Pengajuan Amendemen Pekerjaan {project_name};",
        "Berita Acara Klarifikasi dan Negosiasi Amendemen Waktu dan Biaya No.951/PND95C000/2025-S5 tanggal 02 Desember 2025."
    ])
    letters = ["a", "b", "c", "d", "e", "f"]
    for i, doc_item in enumerate(dasar_dokumen):
        let = letters[i] if i < len(letters) else f"{i+1}"
        pd = doc.add_paragraph()
        pd.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pd.paragraph_format.left_indent = Inches(0.8)
        pd.paragraph_format.space_after = Pt(3)
        pd.paragraph_format.line_spacing = 1.15
        r = pd.add_run(f"{let}.  {doc_item}")
        r.font.name = "Arial"
        r.font.size = Pt(9.5)

    # 5. Kesepakatan Perubahan Preamble
    p_agree = doc.add_paragraph()
    p_agree.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_agree.paragraph_format.space_before = Pt(8)
    p_agree.paragraph_format.space_after = Pt(4)
    p_agree.paragraph_format.line_spacing = 1.15
    r = p_agree.add_run("Berdasarkan hal-hal tersebut di atas, ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_agree.add_run("PARA PIHAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_agree.add_run(f" sepakat untuk mengubah ketentuan dalam ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_agree.add_run("KONTRAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_agree.add_run(f", AMENDEMEN dan mengikatkan diri dalam {amendment_level} ini, dengan ketentuan dan syarat-syarat sebagai berikut:")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    p_def = doc.add_paragraph()
    p_def.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_def.paragraph_format.space_after = Pt(4)
    r = p_def.add_run(f"Segala istilah yang diawali dengan huruf kapital dalam {amendment_level} ini mempunyai pengertian sebagaimana dimaksud dalam ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_def.add_run("KONTRAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_def.add_run(".")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    p_atas = doc.add_paragraph()
    p_atas.paragraph_format.space_after = Pt(6)
    r = p_atas.add_run("Atas ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_atas.add_run("KONTRAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_atas.add_run(" tersebut, ")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_atas.add_run("PARA PIHAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_atas.add_run(" sepakat untuk melakukan perubahan sebagai berikut:")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # 6. BUTIR-BUTIR PERUBAHAN ROMAWI
    # I. Perubahan Lampiran
    p_i = doc.add_paragraph()
    p_i.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_i.paragraph_format.left_indent = Inches(0.4)
    p_i.paragraph_format.space_after = Pt(6)
    r = p_i.add_run("I.   Mengubah butir 1 POKOK-POKOK KONTRAK sebagai berikut:\n")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    klausul_lampiran = params.get(
        "klausul_lampiran",
        f"Mengubah beberapa ketetuan dalam Lampiran B KONTRAK, Lampiran C KONTRAK, Lampiran D KONTRAK, Lampiran G KONTRAK, Lampiran D-I AMENDEMEN dan Lampiran G-I AMENDEMEN dengan perubahan yang masing-masing terdapat dalam Lampiran B-I {amendment_level}, Lampiran C-I {amendment_level}, Lampiran D-II {amendment_level}, dan Lampiran G-II {amendment_level}."
    )
    r = p_i.add_run(klausul_lampiran)
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # II. Perubahan Lingkup Pekerjaan
    p_ii = doc.add_paragraph()
    p_ii.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ii.paragraph_format.left_indent = Inches(0.4)
    p_ii.paragraph_format.space_after = Pt(6)
    r = p_ii.add_run("II.  Mengubah butir 2 POKOK-POKOK KONTRAK sebagai berikut:\n")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    lingkup_pekerjaan = params.get(
        "lingkup_pekerjaan",
        f"2. Pekerjaan yang harus dilaksanakan oleh KONTRAKTOR adalah {project_name} dengan ruang lingkup sebagaimana diuraikan dalam Lampiran B-I {amendment_level}."
    )
    r = p_ii.add_run(lingkup_pekerjaan)
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # III. Tambahan Spesifik Pekerjaan (jika ada)
    tambahan_pekerjaan = params.get("tambahan_pekerjaan", None)
    if tambahan_pekerjaan:
        p_iii = doc.add_paragraph()
        p_iii.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_iii.paragraph_format.left_indent = Inches(0.4)
        p_iii.paragraph_format.space_after = Pt(6)
        r = p_iii.add_run("III. Mengubah butir 3 POKOK-POKOK KONTRAK sebagai berikut:\n")
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r = p_iii.add_run(tambahan_pekerjaan)
        r.font.name = "Arial"
        r.font.size = Pt(9.5)

    # IV. Perubahan Nilai Pekerjaan / Harga Kontrak
    nilai_angka = params.get("nilai_pekerjaan_baru", 28642900000)
    str_angka, str_terbilang = format_rupiah_lengkap(nilai_angka)
    p_iv = doc.add_paragraph()
    p_iv.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_iv.paragraph_format.left_indent = Inches(0.4)
    p_iv.paragraph_format.space_after = Pt(6)
    idx_rom_iv = "IV" if tambahan_pekerjaan else "III"
    r = p_iv.add_run(f"{idx_rom_iv}. Mengubah butir 4 Pokok – Pokok Kontrak sebagai berikut:\n")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_iv.add_run(f"4. Nilai PEKERJAAN yang harus dibayar oleh PERUSAHAAN adalah sebesar {str_angka} {str_terbilang} belum termasuk Pajak Pertambahan Nilai (PPN) sesuai ketentuan yang berlaku dengan tata cara pembayaran sebagaimana diuraikan dalam Lampiran C KONTRAK (“")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)
    r = p_iv.add_run("HARGA KONTRAK")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(9.5)
    r = p_iv.add_run("”)")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # V. Perubahan Jangka Waktu Pelaksanaan / SP3MK
    tanggal_sp3mk = params.get("tanggal_sp3mk", "14 Maret 2024")
    nomor_sp3mk = params.get("nomor_sp3mk", "SP3MK-007/PND900000/2024-S0")
    durasi_mpp = params.get("durasi_bulan_pemeliharaan", 6)
    p_v = doc.add_paragraph()
    p_v.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_v.paragraph_format.left_indent = Inches(0.4)
    p_v.paragraph_format.space_after = Pt(6)
    idx_rom_v = "V" if tambahan_pekerjaan else "IV"
    r = p_v.add_run(f"{idx_rom_v}.  Mengubah butir 5 Pokok – Pokok Kontrak sebagai berikut:\n")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p_v.add_run(f"5. KONTRAK ini mulai berlaku pada tanggal pada {tanggal_sp3mk} TANGGAL SP3MK No.{nomor_sp3mk} dan akan tetap berlaku sampai dengan {durasi_mpp} ({angka_ke_terbilang(durasi_mpp)}) BULAN setelah berakhirnya MASA PENYELESAIAN PEKERJAAN (MPP) dan MASA PEMELIHARAAN (untuk penyelesaian pembayaran tagihan KONTRAKTOR) sebagaimana diuraikan dalam Lampiran D-II {amendment_level}, kecuali diakhiri lebih awal sesuai dengan ketentuan KONTRAK ini.")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # VI. Ketentuan yang Tidak Diubah Tetap Berlaku
    p_vi = doc.add_paragraph()
    p_vi.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_vi.paragraph_format.left_indent = Inches(0.4)
    p_vi.paragraph_format.space_after = Pt(6)
    idx_rom_vi = "VI" if tambahan_pekerjaan else "V"
    r = p_vi.add_run(f"{idx_rom_vi}. Semua ketentuan dalam KONTRAK dan Lampiran-lampiran yang tidak diubah dengan {amendment_level} dinyatakan tetap berlaku dan mengikat PARA PIHAK.")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # VII. Satu Kesatuan Tak Terpisahkan
    tanggal_berlaku = params.get("tanggal_berlaku_amendemen", "04 September 2025")
    p_vii = doc.add_paragraph()
    p_vii.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_vii.paragraph_format.left_indent = Inches(0.4)
    p_vii.paragraph_format.space_after = Pt(6)
    idx_rom_vii = "VII" if tambahan_pekerjaan else "VI"
    r = p_vii.add_run(f"{idx_rom_vii}. {amendment_level} ini merupakan satu kesatuan yang tidak terpisahkan dari KONTRAK dan AMENDEMEN dan berlaku sejak {tanggal_berlaku}.")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # VIII. Penandatanganan Elektronik & Portal Autentifikasi
    p_viii = doc.add_paragraph()
    p_viii.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_viii.paragraph_format.left_indent = Inches(0.4)
    p_viii.paragraph_format.space_after = Pt(6)
    idx_rom_viii = "VIII" if tambahan_pekerjaan else "VII"
    r = p_viii.add_run(f"{idx_rom_viii}. PARA PIHAK telah menyepakati bahwa {amendment_level} ini ditandatangani melalui secara elektronik sesuai dengan ketentuan perundang-undangan yang berlaku, dan PARA PIHAK menyatakan dan menjamin bahwa penandatanganan secara elektronik oleh masing-masing PIHAK adalah sah dan dapat diverifikasi keabsahannya melalui PORTAL AUTENTIFIKASI.")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # IX. Definisi Tanggal Amendemen
    p_ix = doc.add_paragraph()
    p_ix.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ix.paragraph_format.left_indent = Inches(0.4)
    p_ix.paragraph_format.space_after = Pt(6)
    idx_rom_ix = "IX" if tambahan_pekerjaan else "VIII"
    r = p_ix.add_run(f"{idx_rom_ix}. TANGGAL {amendment_level} adalah tanggal, bulan, dan tahun ditandatanganinya {amendment_level} ini oleh penandatangan terakhir, sebagaimana dapat diverifikasi melalui rekam jejak audit pada PORTAL AUTENTIFIKASI.")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # X. Tautan Portal Autentifikasi
    portal_link = params.get("portal_autentifikasi", "https://tte.komdigi.go.id/verifyPDF")
    p_x = doc.add_paragraph()
    p_x.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_x.paragraph_format.left_indent = Inches(0.4)
    p_x.paragraph_format.space_after = Pt(12)
    idx_rom_x = "X" if tambahan_pekerjaan else "IX"
    r = p_x.add_run(f"{idx_rom_x}.  PORTAL AUTENTIFIKASI adalah situs web penyelenggara sertifikasi elektronik indonesia pada tautan berikut {portal_link}.")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # 7. Penutup
    p_close = doc.add_paragraph()
    p_close.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_close.paragraph_format.space_after = Pt(16)
    p_close.paragraph_format.line_spacing = 1.15
    r = p_close.add_run(f"{amendment_level} ini dibuat dan ditandatangani oleh PARA PIHAK secara elektronik dengan menggunakan sertifikat elektronik yang diterbitkan oleh penyelenggara sertifikasi elektronik Indonesia, menggunakan meterai elektronik yang cukup, sebagaimana disimpan pada sistem penyimpanan dokumen elektronik yang berada di PERUSAHAAN.")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # 8. Tabel Tanda Tangan Para Pihak (2 Kolom)
    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Widths
    col_widths = [Inches(3.2), Inches(3.2)]
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width
            clear_cell_borders(row.cells[idx])

    # Row 0: Labels
    c0 = table.rows[0].cells[0].paragraphs[0]
    r = c0.add_run("PERUSAHAAN")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)

    c1 = table.rows[0].cells[1].paragraphs[0]
    r = c1.add_run("KONTRAKTOR")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # Row 1: Space for e-signature / materai
    table.rows[1].cells[0].paragraphs[0].paragraph_format.space_before = Pt(45)
    table.rows[1].cells[1].paragraphs[0].paragraph_format.space_before = Pt(45)

    # Row 2: Nama
    p_name_corp = table.rows[2].cells[0].paragraphs[0]
    r = p_name_corp.add_run(f"Nama  : {company_rep}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    p_name_kont = table.rows[2].cells[1].paragraphs[0]
    r = p_name_kont.add_run(f"Nama  : {contractor_rep}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # Row 3: Jabatan
    p_title_corp = table.rows[3].cells[0].paragraphs[0]
    r = p_title_corp.add_run(f"Jabatan: {company_rep_title}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    p_title_kont = table.rows[3].cells[1].paragraphs[0]
    r = p_title_kont.add_run(f"Jabatan: {contractor_rep_title}")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(9.5)

    # Save to buffer
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()
