"""Regression checks for fidelity, source selection and immutable exports."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pymupdf

from api.rks import router
from tools.rks.catalog import list_sources, search_sources
from tools.rks.extraction import extract_document
from tools.rks.service import create_document, artifact_file, get_document
from tools.rks.validation import validate_docx


class RKSTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.output = self.root / "output"

    def pdf(self, name="RKS-overhaul-tangki-001.pdf", scanned=False):
        path = self.data / name
        with pymupdf.open() as pdf:
            cover = pdf.new_page()
            if scanned:
                cover.draw_rect(pymupdf.Rect(60, 60, 200, 200), fill=(0, .2, .5))
            else:
                cover.insert_text((60, 60), "RENCANA KERJA DAN SYARAT-SYARAT")
                cover.insert_text((60, 85), "OVERHAUL TANGKI 001")
                toc = pdf.new_page()
                toc.insert_text((60, 60), "DAFTAR ISI")
                toc.insert_text((60, 90), "LINGKUP .................... 3\nBAHAN .................... 3\nBOQ .................... 3")
                body = pdf.new_page()
                body.insert_text((60, 60), "1. LINGKUP PEKERJAAN")
                body.insert_text((60, 85), "Pertahankan angka 8.500 KL dan satuan mm apa adanya.")
                for y in (120, 145, 170):
                    body.draw_line((60, y), (360, y))
                for x in (60, 210, 360):
                    body.draw_line((x, 120), (x, 170))
                body.insert_text((65, 136), "Uraian")
                body.insert_text((215, 136), "Volume")
                body.insert_text((65, 161), "Pelat 6 mm")
                body.insert_text((215, 161), "12")
            pdf.save(path)
        return path

    def test_ambiguous_sources_require_choice_and_job_filter(self):
        self.pdf()
        self.pdf("RKS-overhaul-tangki-002.pdf")
        self.pdf("RKS-pembangunan-tangki-003.pdf")
        matches = search_sources("buatkan rks overhaul tangki", self.data)
        self.assertEqual(2, len(matches))
        result = create_document("overhaul tangki", data_dir=self.data, output_dir=self.output, render_preview=False)
        self.assertEqual("pilih sumber", result["status"])
        self.assertFalse(self.output.exists())

    def test_transcription_preserves_literals_and_table(self):
        self.pdf()
        result = create_document("overhaul tangki 001", data_dir=self.data, output_dir=self.output, render_preview=False)
        self.assertNotEqual("gagal", result["status"], result)
        document = Document(artifact_file(result["artifact_id"], "docx", self.output))
        body = "\n".join(p.text for p in document.paragraphs)
        self.assertIn("Pertahankan angka 8.500 KL dan satuan mm apa adanya.", body)
        cells = "\n".join(c.text for t in document.tables for row in t.rows for c in row.cells)
        self.assertIn("Pelat 6 mm", cells)
        self.assertIn("12", cells)
        self.assertNotIn("....................", body)
        self.assertIn('TOC \\o', document.element.xml)

    def test_unreadable_page_is_preserved_visually_and_not_complete(self):
        self.pdf(scanned=True)
        source = list_sources(self.data)[0]
        extracted = extract_document(source, self.root / "assets")
        self.assertEqual("perlu pemeriksaan", extracted["status"])
        element = extracted["pages"][0]["elements"][0]
        self.assertTrue(element["page_fallback"])
        self.assertTrue(Path(element["path"]).is_file())

    def test_unknown_source_cannot_fall_back_to_other_project(self):
        self.pdf()
        result = create_document("overhaul tangki", "a" * 24, data_dir=self.data, output_dir=self.output)
        self.assertEqual("gagal", result["status"])

    def test_borderless_columns_keep_their_visual_relationship(self):
        path = self.data / "RKS-overhaul-tangki-004.pdf"
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            for i in range(5):
                page.insert_text((60, 160 + 30 * i), f"Uraian pekerjaan bagian {i}")
                page.insert_text((330, 160 + 30 * i), f"Spesifikasi material {i}")
            pdf.save(path)
        extracted = extract_document(list_sources(self.data)[0], self.root / "assets")
        self.assertEqual("perlu pemeriksaan", extracted["status"])
        self.assertTrue(extracted["pages"][0]["elements"][0]["page_fallback"])

    def test_versions_are_unique_and_modified_artifacts_are_rejected(self):
        self.pdf()
        first = create_document("overhaul tangki 001", data_dir=self.data, output_dir=self.output, render_preview=False)
        second = create_document("overhaul tangki 001", data_dir=self.data, output_dir=self.output, render_preview=False)
        self.assertNotEqual(first["artifact_id"], second["artifact_id"])
        path = artifact_file(first["artifact_id"], "docx", self.output)
        path.write_bytes(b"changed after finalization")
        with self.assertRaises(FileNotFoundError):
            artifact_file(first["artifact_id"], "docx", self.output)
        with self.assertRaises(FileNotFoundError):
            get_document("../outside", self.output)

    def test_hashes_capture_finalized_docx_and_its_pdf(self):
        self.pdf()
        def finalize(path, count):
            doc = Document(path)
            doc.core_properties.subject = "Finalized by renderer"
            doc.save(path)
            with pymupdf.open() as pdf:
                pdf.new_page().insert_text((60, 60), "Preview final")
                pdf.save(path.with_suffix(".pdf"))
            return {"available": True, "toc_verified": True}
        with patch("tools.rks.service.finalize_and_preview", side_effect=finalize):
            result = create_document("overhaul tangki 001", data_dir=self.data, output_dir=self.output)
        for kind in ("docx", "pdf"):
            path = artifact_file(result["artifact_id"], kind, self.output)
            self.assertEqual(result[f"{kind}_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_api_rejects_paths_and_returns_not_found(self):
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            self.assertEqual(422, client.post("/api/rks/generate", json={"query": "overhaul", "source_id": "../data/a.pdf"}).status_code)
            self.assertEqual(404, client.get("/api/rks/invalid/document.docx").status_code)

    def test_office_run_boundaries_are_not_missing_content(self):
        path = self.root / "runs.docx"
        doc = Document()
        p = doc.add_paragraph()
        p.add_run("Pelat ")
        p.add_run("6")
        p.add_run("mm").add_break()
        p.add_run("Volume 12")
        doc.save(path)
        extracted = {"pages": [{"elements": [{"kind": "paragraph", "text": "Pelat 6mm\nVolume 12"}]}]}
        self.assertTrue(validate_docx(extracted, path)["passed"])


if __name__ == "__main__":
    unittest.main()
