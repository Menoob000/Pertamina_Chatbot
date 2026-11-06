"""Regression checks for fidelity, source selection and immutable exports."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pymupdf

from api.rks import router
from tools.rks.catalog import list_sources, search_sources
from tools.rks.extraction import extract_document
from tools.rks.text_extraction import extract_text_document
from tools.rks.service import create_document, artifact_file, get_document, latest_document
from tools.rks.validation import validate_docx
from tools.rks.retrieval import search_evidence


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

    def test_generic_query_selects_source_automatically_and_filters_job(self):
        self.pdf()
        self.pdf("RKS-overhaul-tangki-002.pdf")
        self.pdf("RKS-pembangunan-tangki-003.pdf")
        matches = search_sources("buatkan rks overhaul tangki", self.data)
        self.assertEqual(2, len(matches))
        result = create_document("overhaul tangki", data_dir=self.data, output_dir=self.output, render_preview=False)
        self.assertNotEqual("gagal", result["status"], result)
        self.assertEqual(matches[0]["source_id"], result["source"]["source_id"])
        self.assertEqual("peringkat otomatis", result["selection"]["method"])
        self.assertEqual(1, len(result["selection"]["alternatives"]))
        self.assertTrue(result["evidence"])
        self.assertEqual(result["source"]["filename"], result["section_provenance"][0]["filename"])
        self.assertGreaterEqual(result["section_provenance"][0]["page"], 1)

    def test_no_relevant_source_creates_only_general_placeholders(self):
        self.pdf()
        result = create_document("rks jasa katering", data_dir=self.data, output_dir=self.output, render_preview=False)
        self.assertEqual("template umum", result["mode"])
        self.assertIsNone(result["source"])
        body = "\n".join(p.text for p in Document(artifact_file(result["artifact_id"], "docx", self.output)).paragraphs)
        self.assertIn("BELUM ADA SUMBER", body)
        self.assertIn("[BOQ belum tersedia", body)
        self.assertNotIn("OVERHAUL TANGKI 001", body)
        self.assertIsNone(latest_document("a" * 24, self.output))

    def test_page_retrieval_hybrid_metadata_threshold_and_empty(self):
        self.pdf()
        source = list_sources(self.data)[0]
        doc = SimpleNamespace(metadata={"file_name": source["filename"], "page": 3},
                              page_content="Lingkup overhaul tangki dan pelat 6 mm")
        store = SimpleNamespace(similarity_search_with_relevance_scores=lambda query, k: [(doc, .92)])
        found = search_evidence("overhaul tangki pelat", [source], semantic_store=store, score_threshold=.4)
        self.assertEqual("ditemukan", found["status"])
        self.assertEqual(source["filename"], found["results"][0]["filename"])
        self.assertEqual(3, found["results"][0]["page"])
        self.assertIn("score", found["results"][0])
        self.assertEqual("sumber tidak ditemukan", search_evidence(
            "overhaul", [source], filters={"year": 2099}, semantic_store=store)["status"])
        self.assertEqual("sumber tidak ditemukan", search_evidence(
            "kataasing", [source], semantic_store=SimpleNamespace(
                similarity_search_with_relevance_scores=lambda query, k: []))["status"])
        self.assertEqual("sumber tidak ditemukan", search_evidence(
            "overhaul tangki pelat", [source], semantic_store=store, score_threshold=1)["status"])

    def test_semantic_failure_falls_back_to_keyword_without_losing_source(self):
        self.pdf()
        source = list_sources(self.data)[0]
        failing = SimpleNamespace(similarity_search_with_relevance_scores=lambda query, k: 1 / 0)
        result = search_evidence("pelat 6 mm", [source], semantic_store=failing, score_threshold=.4)
        self.assertEqual("ditemukan", result["status"])
        self.assertEqual("tidak tersedia", result["semantic_status"])
        self.assertEqual(3, result["results"][0]["page"])

    def test_editable_layout_preserves_literals_tables_and_headings(self):
        self.pdf()
        result = create_document("overhaul tangki 001", data_dir=self.data, output_dir=self.output, render_preview=False)
        self.assertNotEqual("gagal", result["status"], result)
        document = Document(artifact_file(result["artifact_id"], "docx", self.output))
        body = "\n".join(p.text for p in document.paragraphs)
        self.assertIn("Pertahankan angka 8.500 KL dan satuan mm apa adanya.", body)
        self.assertTrue(document.tables)
        cells = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
        self.assertIn("Pelat 6 mm", cells)
        self.assertIn("12", cells)
        self.assertGreater(sum(p.style.name.startswith("Heading") for p in document.paragraphs), 0)
        self.assertNotIn("....................", body)
        self.assertIn('TOC \\o', document.element.xml)

    def test_damaged_text_stays_editable_and_enters_toc(self):
        path = self.data / "RKS-overhaul-tangki-005.pdf"
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((60, 60), "RENCANA KERJA DAN SYARAT-SYARAT")
            page.insert_text((60, 90), "OVERHAUL TANGKI 005")
            body = pdf.new_page()
            body.insert_text((60, 60), "1. LINGKUP PEKERJAAN")
            body.insert_text((60, 90), "Pekerjaan pelat tangki 6 mm")
            body.draw_rect(pymupdf.Rect(60, 120, 150, 150))
            pdf.save(path)
        source = list_sources(self.data)[0]
        extracted = extract_text_document(source)
        self.assertEqual(0, sum(e["kind"] == "image" for p in extracted["pages"] for e in p["elements"]))
        self.assertTrue(any(e["kind"] == "heading" for e in extracted["pages"][1]["elements"]))
        result = create_document("overhaul tangki 005", data_dir=self.data, output_dir=self.output, render_preview=False)
        doc = Document(artifact_file(result["artifact_id"], "docx", self.output))
        self.assertGreaterEqual(len(doc.inline_shapes), 0)

    def test_real_overhaul_cover_uses_text_layer_instead_of_full_page_image(self):
        real = Path(__file__).resolve().parents[1] / "data" / "RKS-041T304-PEKERJAAN OVERHAUL TANKI.pdf"
        if not real.is_file():
            self.skipTest("PDF sampel tidak tersedia")
        source = next(s for s in list_sources(real.parent) if s["filename"] == real.name)
        extracted = extract_text_document(source)
        self.assertTrue(extracted["pages"][0]["cover"])
        self.assertTrue(any("RENCANA KERJA" in e["text"] for e in extracted["pages"][0]["elements"]))
        self.assertEqual(0, sum(e["kind"] == "image" for p in extracted["pages"] for e in p["elements"]))
        self.assertGreater(extracted["heading_count"], 20)

    def test_cover_uses_dynamic_source_title_when_layout_is_not_formal(self):
        path = self.data / "RKS-survey-pipa-006.pdf"
        with pymupdf.open() as pdf:
            cover = pdf.new_page()
            cover.insert_text((60, 60), "RENCANA KERJA & SYARAT - SYARAT (RKS)")
            cover.insert_text((60, 90), "PEKERJAAN SURVEY JALUR PIPA")
            cover.insert_text((60, 115), "PADALARANG - SUKABUMI")
            body = pdf.new_page()
            body.insert_text((60, 60), "1. LINGKUP PEKERJAAN")
            pdf.save(path)
        source = list_sources(self.data)[0]
        result = create_document("survey pipa 006", source["source_id"], data_dir=self.data,
                                 output_dir=self.output, render_preview=False)
        doc = Document(artifact_file(result["artifact_id"], "docx", self.output))
        self.assertIn("RENCANA KERJA & SYARAT - SYARAT", doc.tables[0].cell(0, 0).text)
        self.assertIn("PEKERJAAN SURVEY JALUR PIPA", "\n".join(p.text for p in doc.paragraphs))
        self.assertEqual(0, len(doc.inline_shapes))

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
        self.assertEqual(result["artifact_id"], latest_document(result["source"]["source_id"], self.output)["artifact_id"])
        self.assertIsNone(latest_document("f" * 24, self.output))
        artifact_file(result["artifact_id"], "pdf", self.output).write_bytes(b"modified PDF")
        self.assertIsNone(latest_document(result["source"]["source_id"], self.output))

    def test_api_rejects_paths_and_returns_not_found(self):
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            self.assertEqual(422, client.post("/api/rks/generate", json={"query": "overhaul", "source_id": "../data/a.pdf"}).status_code)
            self.assertEqual(404, client.get("/api/rks/invalid/document.docx").status_code)

    def test_search_api_passes_metadata_filters_and_limits(self):
        self.pdf()
        source = list_sources(self.data)[0]
        app = FastAPI()
        app.include_router(router)
        with patch("api.rks.list_sources", return_value=[source]), \
             patch("api.rks.search_evidence", return_value={"status": "sumber tidak ditemukan", "results": []}) as search, \
             TestClient(app) as client:
            response = client.post("/api/rks/search", json={"query": "pelat tangki", "source_id": source["source_id"],
                                                           "year": 2025, "version": "2", "top_k": 2,
                                                           "score_threshold": .7})
        self.assertEqual(200, response.status_code)
        self.assertEqual("sumber tidak ditemukan", response.json()["status"])
        self.assertEqual([source], search.call_args.args[1])
        self.assertEqual(2025, search.call_args.kwargs["filters"]["year"])
        self.assertEqual(.7, search.call_args.kwargs["score_threshold"])

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
