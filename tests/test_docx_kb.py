import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from rag.docx_source import read_docx
from rag.source_reader import source_chunks
from tools.rks.catalog import list_sources
from tools.rks.retrieval import search_evidence
from tools.rks.service import create_document, artifact_file


def make_source(path):
    """Explicit demonstration fixture; its values are not facts from a real project."""
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.4)
    for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3"):
        doc.styles[name].font.name = "Arial"
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
        for border in doc.styles[name].element.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    doc.styles["Normal"].font.size = Pt(11)
    doc.styles["Normal"].paragraph_format.space_after = Pt(6)
    doc.add_paragraph("RKS Demonstrasi Dukungan DOCX", "Title")
    doc.add_paragraph("Overhaul tangki UNIT-UJI")
    doc.add_paragraph("Sumber uji struktur dokumen. Bukan data atau ketentuan proyek nyata.")
    doc.add_paragraph("Contoh ini memuat heading, penomoran otomatis, tabel BOQ, dan sel gabungan.")
    logo = Path("assets/logo_pertamina.png")
    if logo.is_file():
        doc.add_picture(str(logo), width=Cm(3.4))
    doc.add_page_break()
    doc.add_heading("1. Lingkup Pekerjaan", 1)
    doc.add_paragraph("Seluruh teks pada contoh ini digunakan untuk memeriksa pembacaan knowledge base DOCX tanpa parafrase.")
    doc.add_heading("1.1 Persiapan", 2)
    root = doc.part.numbering_part.element
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), "70")
    for level, kind, text in ((0, "decimal", "%1."), (1, "lowerLetter", "%2."), (2, "lowerRoman", "%3.")):
        node = OxmlElement("w:lvl")
        node.set(qn("w:ilvl"), str(level))
        for tag, value in (("start", "1"), ("numFmt", kind), ("lvlText", text)):
            child = OxmlElement("w:" + tag)
            child.set(qn("w:val"), value)
            node.append(child)
        props = OxmlElement("w:pPr")
        indent = OxmlElement("w:ind")
        indent.set(qn("w:left"), str(420 + level * 420))
        indent.set(qn("w:hanging"), "300")
        props.append(indent)
        node.append(props)
        abstract.append(node)
    root.append(abstract)
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), "70")
    abstract_id = OxmlElement("w:abstractNumId")
    abstract_id.set(qn("w:val"), "70")
    num.append(abstract_id)
    root.append(num)
    for level, text in ((0, "Periksa kelengkapan dokumen sumber."),
                        (1, "Pertahankan istilah dan isi sumber."),
                        (2, "Catat lokasi paragraf dan bagian."),
                        (2, "Catat lokasi baris tabel."),
                        (1, "Tinjau kembali hasil pemformatan."),
                        (0, "Simpan hasil sebagai draf untuk diperiksa.")):
        p = doc.add_paragraph(text)
        np = OxmlElement("w:numPr")
        for tag, value in (("ilvl", str(level)), ("numId", "70")):
            child = OxmlElement("w:" + tag)
            child.set(qn("w:val"), value)
            np.append(child)
        p._p.get_or_add_pPr().append(np)
    doc.add_heading("2. Bill of Quantity", 1)
    doc.add_paragraph("Nilai tabel berikut adalah data uji pembacaan, bukan perhitungan biaya pekerjaan.")
    table = doc.add_table(rows=4, cols=4)
    table.style = "Table Grid"
    table.autofit = False
    for column, width in zip(table.columns, (1.0, 9.0, 2.0, 2.2)):
        column.width = Cm(width)
    for row in table.rows:
        for cell, width in zip(row.cells, (1.0, 9.0, 2.0, 2.2)):
            cell.width = Cm(width)
    table.rows[0].cells[0].merge(table.rows[0].cells[3]).text = "BOQ DATA UJI"
    for cell, value in zip(table.rows[1].cells, ("No", "Uraian", "Volume", "Satuan")):
        cell.text = value
        cell.paragraphs[0].runs[0].bold = True
    header = OxmlElement("w:tblHeader")
    table.rows[1]._tr.get_or_add_trPr().append(header)
    for row, values in zip(table.rows[2:], (("1", "Contoh pemeriksaan pelat 6 mm", "12", "unit"),
                                          ("2", "Contoh dokumentasi pemeriksaan", "1", "paket"))):
        for cell, value in zip(row.cells, values):
            cell.text = value
    doc.add_heading("3. Penanggung Jawab", 1)
    doc.add_paragraph("Nama Pejabat Procurement: Nama Uji")
    doc.add_paragraph("Jabatan Pejabat Procurement: Jabatan Uji")
    doc.add_paragraph("Kolom ini hanya untuk pemeriksaan alur sumber dan tidak menunjuk pejabat proyek nyata.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


class DocxKnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        self.data.mkdir()
        self.path = make_source(self.data / "RKS-overhaul-tangki-UNIT-UJI-2026-rev-1.docx")

    def test_order_numbering_headings_and_merge(self):
        result = read_docx(self.path)
        labels = [b["number_label"] for b in result["blocks"] if b.get("number_label")]
        self.assertEqual(["1.", "a.", "i.", "ii.", "b.", "2."], labels)
        table = next(b for b in result["blocks"] if b["kind"] == "table")
        self.assertEqual(4, table["cells"][0]["colspan"])
        self.assertIsNone(table["page"])
        self.assertIn("1.1 Persiapan", next(b["section"] for b in result["blocks"] if b.get("number_label")))

    def test_search_filters_threshold_source_location_and_empty(self):
        source = list_sources(self.data)[0]
        self.assertEqual("docx", source["file_format"])
        self.assertIsNone(source["pages"])
        hit = search_evidence("pelat 6 mm", [source], use_semantic=False)
        self.assertEqual("ditemukan", hit["status"])
        self.assertIn("tabel", hit["results"][0]["location"])
        self.assertIsNone(hit["results"][0]["page"])
        self.assertEqual([], search_evidence("pelat", [source], filters={"file_format": "pdf"}, use_semantic=False)["results"])
        self.assertEqual([], search_evidence("tidakada", [source], use_semantic=False)["results"])
        self.assertEqual([], search_evidence("pelat tidakada tidakada2", [source], score_threshold=.99, use_semantic=False)["results"])
        chunks = list(source_chunks(source))
        self.assertTrue(all("BOQ DATA UJI" in text for text, meta in chunks if meta["element_type"] == "table"))

    def test_hybrid_requires_current_docx_hash(self):
        source = list_sources(self.data)[0]
        doc = SimpleNamespace(metadata={"file_name": source["filename"], "source_sha256": source["sha256"],
                                       "location": "paragraf 1"}, page_content="pemeriksaan khusus")
        store = SimpleNamespace(similarity_search_with_relevance_scores=lambda query, k: [(doc, .9)])
        result = search_evidence("pemeriksaan khusus", [source], semantic_store=store, score_threshold=.1, use_semantic=True)
        self.assertTrue(any(b.get("semantic_score") for b in result["results"]))
        doc.metadata["source_sha256"] = "stale"
        result = search_evidence("pemeriksaan khusus", [source], semantic_store=store, score_threshold=.1, use_semantic=True)
        self.assertFalse(any(b.get("semantic_score") for b in result["results"]))

    def test_generation_preserves_word_numbering_and_merged_tables(self):
        output = Path(self.temp.name) / "output"
        with patch("config.RKS_SEARCH_SEMANTIC_ENABLED", False), patch("tools.rks.service.assess_csms", return_value={}):
            result = create_document("overhaul tangki", data_dir=self.data, output_dir=output, render_preview=False)
        self.assertNotEqual("gagal", result["status"], result)
        self.assertTrue(result["verification"]["passed"], result.get("verification"))
        self.assertIsNone(result["source_pages"])
        generated = Document(artifact_file(result["artifact_id"], "docx", output))
        self.assertEqual(4, len(generated.tables[0].rows[0].cells))
        self.assertEqual(generated.tables[0].cell(0, 0)._tc, generated.tables[0].cell(0, 3)._tc)
        self.assertTrue(generated.element.xpath('.//w:numPr'))

    def test_corrupt_file_does_not_hide_valid_sources_and_hash_changes(self):
        (self.data / "bad.docx").write_bytes(b"not a zip")
        self.assertEqual(1, len(list_sources(self.data)))
        before = list_sources(self.data)[0]["source_id"]
        document = Document(self.path)
        document.add_paragraph("Perubahan versi untuk uji.")
        document.save(self.path)
        self.assertNotEqual(before, list_sources(self.data)[0]["source_id"])

    def test_vertical_merge_maps_the_cell_once(self):
        doc = Document(self.path)
        table = doc.tables[0]
        table.cell(2, 0).merge(table.cell(3, 0)).text = "Kelompok A"
        doc.save(self.path)
        extracted = read_docx(self.path)
        block = next(b for b in extracted["blocks"] if b["kind"] == "table")
        self.assertEqual(1, block["text"].count("Kelompok A"))
        self.assertEqual("restart", next(c["vertical_merge"] for c in block["cells"] if c["text"] == "Kelompok A"))


if __name__ == "__main__":
    unittest.main()
