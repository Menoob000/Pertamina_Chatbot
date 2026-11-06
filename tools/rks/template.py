"""Neutral RKS skeleton when the knowledge base has no suitable source."""
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .document import _field


SECTIONS = (
    ("1. Informasi pekerjaan", "[Nama pekerjaan, lokasi, pemilik pekerjaan, nomor dokumen, tanggal, dan versi diisi pengguna.]"),
    ("2. Lingkup pekerjaan", "[Uraikan lingkup dan batas pekerjaan berdasarkan data proyek yang disetujui.]"),
    ("3. Persyaratan teknis", "[Isi spesifikasi, standar, material, dan metode kerja dari dokumen acuan yang sah.]"),
    ("4. Keselamatan, kesehatan kerja, dan lingkungan", "[Isi persyaratan K3L/CSMS yang berlaku untuk pekerjaan ini.]"),
    ("5. Jadwal dan pelaksanaan", "[Isi tahapan, durasi, pengendalian mutu, dan kriteria penerimaan.]"),
    ("6. Administrasi dan serah terima", "[Isi dokumen pelaksanaan, laporan, pemeriksaan, dan syarat serah terima.]"),
    ("Lampiran A. Daftar acuan", "[Belum ada sumber knowledge base yang memenuhi ambang kecocokan. Tambahkan dokumen acuan yang benar.]"),
    ("Lampiran B. Bill of Quantity", "[BOQ belum tersedia. Lampirkan BOQ terverifikasi pada tahap dokumen tender.]"),
)


def render_general_template(query: str, output: Path) -> None:
    doc = Document()
    page = doc.sections[0]
    page.page_width, page.page_height = Cm(21), Cm(29.7)
    page.top_margin = page.bottom_margin = Cm(2.5)
    page.left_margin, page.right_margin = Cm(3), Cm(2.5)
    for name in ("Normal", "Title", "Heading 1"):
        doc.styles[name].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_paragraph("RENCANA KERJA DAN SYARAT-SYARAT (RKS)", "Title")
    doc.add_paragraph("TEMPLATE UMUM — BELUM ADA SUMBER KNOWLEDGE BASE YANG SESUAI")
    doc.add_paragraph(f"Permintaan: {query}")
    doc.add_paragraph("[Nama pekerjaan dan identitas proyek diisi pengguna]")
    doc.add_page_break()
    doc.add_paragraph("Daftar isi", "Title")
    _field(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u')
    doc.add_page_break()
    for heading, placeholder in SECTIONS:
        doc.add_paragraph(heading, "Heading 1")
        doc.add_paragraph(placeholder)
    footer = page.footer.paragraphs[0]
    footer.add_run("Template umum — halaman ")
    _field(footer, "PAGE")
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    doc.settings.element.append(update)
    doc.core_properties.title = "Template umum RKS"
    doc.core_properties.comments = "Tidak ada sumber knowledge base yang memenuhi ambang kecocokan. Placeholder bukan fakta proyek."
    doc.save(output)
