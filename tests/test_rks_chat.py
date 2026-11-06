"""Regression for the chat panel showing exported pages instead of raw text."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import sys
from unittest.mock import patch

from docx import Document
import pymupdf
from streamlit.testing.v1 import AppTest

from tools.rks.chat import current_document
from tools.rks.preview import finalize_and_preview


class ChatPreviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / "RKS.pdf"
        self.docx = self.root / "RKS.docx"
        Document().save(self.docx)
        with pymupdf.open() as pdf:
            for index in range(2):
                pdf.new_page().insert_text((60, 60), f"Halaman hasil DOCX {index + 1}")
            pdf.save(self.pdf)
        self.source = {"source_id": "a" * 24, "filename": "RKS-restorasi-tangki.pdf", "path": str(self.pdf)}
        self.result = {"artifact_id": "a" * 32, "status": "lengkap", "source": self.source,
                       "preview": {"available": True}, "issues": []}

    def test_tool_artifact_is_not_hidden_by_model_summary(self):
        tool = SimpleNamespace(type="tool", name="create_rks_document", content=json.dumps(self.result))
        summary = SimpleNamespace(type="ai", content="RENCANA KERJA DAN SYARAT-SYARAT ringkasan")
        with patch("tools.rks.chat.list_sources", return_value=[self.source]):
            result = current_document([tool, summary])
        self.assertEqual(self.result["artifact_id"], result["rks_result"]["artifact_id"])

    @unittest.skipUnless(sys.platform == "win32", "Windows Word preflight")
    def test_full_system_disk_is_reported_without_launching_word(self):
        with patch("tools.rks.preview.shutil.disk_usage", return_value=SimpleNamespace(free=0)), \
             patch("tools.rks.preview.subprocess.run") as run:
            result = finalize_and_preview(self.docx, 1)
        self.assertFalse(result["available"])
        self.assertIn("Ruang drive sistem", result["message"])
        run.assert_not_called()

    def test_failed_generation_does_not_show_an_old_source(self):
        old = SimpleNamespace(type="tool", name="fetch_full_documents", content={"full_docs": "old source", "title": "old"})
        failure = SimpleNamespace(type="tool", name="create_rks_document", content='{"status":"gagal","message":"sumber gagal"}')
        result = current_document([old, failure])
        self.assertEqual("gagal", result["rks_result"]["status"])
        self.assertIsNone(result["pdf_path"])

    def test_fetched_document_displays_pdf_controls_without_regenerating_on_page_change(self):
        code = """import streamlit as st
from tools.rks.streamlit_view import render_chat_preview
render_chat_preview(st.session_state.document, 'test-thread')
"""
        with patch("tools.rks.streamlit_view.list_sources", return_value=[self.source]), \
             patch("tools.rks.streamlit_view.latest_document", return_value=self.result), \
             patch("tools.rks.streamlit_view.artifact_file", side_effect=lambda artifact, kind: self.pdf if kind == "pdf" else self.docx), \
             patch("tools.rks.streamlit_view.create_document") as create:
            app = AppTest.from_string(code)
            app.session_state["document"] = {"pdf_path": str(self.pdf)}
            app.session_state[f"chat-rks-test-thread-{self.source['source_id']}"] = {
                "status": "perlu pemeriksaan", "preview": {"available": False}}
            app.run(timeout=20)
            self.assertEqual([], list(app.exception))
            self.assertEqual(1, app.number_input[0].value)
            self.assertTrue(any("Halaman 1 dari 2" in x.value for x in app.caption))
            self.assertTrue(app.get("imgs") or app.get("image") or app.get("image_list"), str(app))
            app.number_input[0].set_value(2).run(timeout=20)
            self.assertTrue(any("Halaman 2 dari 2" in x.value for x in app.caption))
            create.assert_not_called()

    def test_general_template_preview_needs_no_source_pdf(self):
        code = """import streamlit as st
from tools.rks.streamlit_view import render_result
render_result(st.session_state.result)
"""
        result = {**self.result, "mode": "template umum", "source": None,
                  "message": "Template umum dengan placeholder."}
        with patch("tools.rks.streamlit_view.artifact_file",
                   side_effect=lambda artifact, kind: self.pdf if kind == "pdf" else self.docx):
            app = AppTest.from_string(code)
            app.session_state["result"] = result
            app.run(timeout=20)
        self.assertEqual([], list(app.exception))
        self.assertTrue(any("Tidak ada sumber knowledge base" in x.value for x in app.info))
        self.assertEqual(1, app.number_input[0].value)

    def test_chat_default_tab_is_rendered_preview(self):
        from langchain_core.messages import ToolMessage
        message = ToolMessage(name="fetch_full_documents", tool_call_id="source-test", content=json.dumps({
            "title": self.source["filename"], "source_file": self.source["filename"],
            "full_docs": "RENCANA KERJA DAN SYARAT-SYARAT\nIsi RKS dari sumber."}))
        fake_agent = SimpleNamespace(app=SimpleNamespace(get_state=lambda config: SimpleNamespace(values={"messages": [message]})), tools=[])
        with patch.dict(sys.modules, {"agent": fake_agent}), \
             patch("tools.rks.chat.list_sources", return_value=[self.source]), \
             patch("tools.rks.streamlit_view.list_sources", return_value=[self.source]), \
             patch("tools.rks.streamlit_view.latest_document", return_value=self.result), \
             patch("tools.rks.streamlit_view.artifact_file", side_effect=lambda artifact, kind: self.pdf if kind == "pdf" else self.docx):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py")).run(timeout=40)
            self.assertEqual([], list(app.exception))
            self.assertFalse(any("<style>" in str(x.value) or "Recent Conversations</p>" in str(x.value)
                                 for x in app.markdown))
            self.assertEqual("Pratinjau halaman", app.tabs[0].label)
            self.assertTrue(any(x.label == "Halaman" for x in app.number_input))
            labels = [x.proto.label for x in app.get("download_button")]
            self.assertIn("Unduh DOCX", labels)
            self.assertIn("Unduh PDF yang dipreview", labels)


if __name__ == "__main__":
    unittest.main()
