import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from fastapi.testclient import TestClient

from backend.app import create_app, get_agent_bridge, get_document_bridge, get_store
from backend.schemas import DocumentDetail, ToolEvent
from backend.services import DATA_DIR, AgentBridge, DocumentBridge, _tool_payload
from backend.store import MemoryStore


class FakeAgent:
    def run(self, thread_id, prompt):
        assert thread_id
        assert prompt == "Cari RKS"
        return (
            "Saya menemukan dokumen RKS.",
            [ToolEvent(name="fetch_full_documents", status="completed")],
            {"title": "Contoh RKS", "full_docs": "BAB 1 PENDAHULUAN\nIsi contoh dokumen.", "source_file": "example.pdf"},
        )


class FakeDocuments:
    def from_agent_payload(self, payload):
        assert payload["title"] == "Contoh RKS"
        return DocumentDetail(
            id="document-1",
            title=payload["title"],
            source_file=payload["source_file"],
            content=payload["full_docs"],
            chapters=[],
            can_convert=True,
        ), Path("data/example.pdf")

    def convert(self, source_pdf):
        assert source_pdf == Path("data/example.pdf")
        return Path("output/example.docx")


def make_client():
    app = create_app()
    state = MemoryStore()
    app.dependency_overrides[get_store] = lambda: state
    app.dependency_overrides[get_agent_bridge] = lambda: FakeAgent()
    app.dependency_overrides[get_document_bridge] = lambda: FakeDocuments()
    return TestClient(app)


def test_health_does_not_load_legacy_agent():
    client = make_client()
    assert client.get("/api/health").json() == {"status": "ok"}
    preflight = client.options(
        "/api/threads",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_thread_chat_document_and_conversion_contract():
    client = make_client()
    thread = client.post("/api/threads", json={}).json()
    thread_id = thread["id"]
    assert thread["message_count"] == 0

    response = client.post(f"/api/threads/{thread_id}/messages", json={"message": "Cari RKS"})
    assert response.status_code == 200
    chat = response.json()
    assert chat["message"]["content"] == "Saya menemukan dokumen RKS."
    assert chat["document_id"] == "document-1"
    assert chat["tool_events"] == [{"name": "fetch_full_documents", "status": "completed"}]

    detail = client.get(f"/api/threads/{thread_id}").json()
    assert detail["message_count"] == 2
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert client.get("/api/documents/document-1").json()["title"] == "Contoh RKS"

    conversion = client.post("/api/documents/document-1/conversions")
    assert conversion.status_code == 201
    assert conversion.json()["filename"] == "example.docx"
    assert conversion.json()["download_url"].startswith("/api/files/")

    renamed = client.patch(f"/api/threads/{thread_id}", json={"title": "RKS tangki"})
    assert renamed.json()["title"] == "RKS tangki"
    assert len(client.get("/api/threads").json()) == 1
    assert client.delete(f"/api/threads/{thread_id}").status_code == 204
    assert client.get(f"/api/threads/{thread_id}").status_code == 404
    assert client.get("/api/documents/document-1").status_code == 404


def test_invalid_requests_are_consistent():
    client = make_client()
    assert client.get("/api/threads/unknown").json()["error"]["code"] == "thread_not_found"
    assert client.post("/api/threads", json={"title": "   "}).json()["error"]["code"] == "invalid_title"
    thread_id = client.post("/api/threads", json={}).json()["id"]
    assert client.post(f"/api/threads/{thread_id}/messages", json={"message": "   "}).json()["error"]["code"] == "invalid_message"
    assert client.post(f"/api/threads/{thread_id}/messages", json={"message": ""}).json()["error"]["code"] == "invalid_request"
    assert client.get("/api/files/unknown/download").status_code == 404


def test_agent_bridge_extracts_tool_result_without_database(monkeypatch):
    agent_module = ModuleType("agent")
    messages_module = ModuleType("langchain_core.messages")
    messages_module.HumanMessage = lambda content: SimpleNamespace(content=content)

    class FakeGraph:
        def stream(self, inputs, config, stream_mode):
            assert inputs["messages"][0].content == "Cari RKS"
            assert config["configurable"]["thread_id"] == "thread-1"
            assert stream_mode == "updates"
            yield {"agent": {"messages": [SimpleNamespace(tool_calls=[{"name": "fetch_full_documents"}], content="")]}}
            yield {"tools": {"messages": [SimpleNamespace(name="fetch_full_documents", content="{'title': 'RKS', 'full_docs': 'Isi lengkap'}")]}}
            yield {"agent": {"messages": [SimpleNamespace(tool_calls=[], content="Ini ringkasannya.")]}}

    agent_module.app = FakeGraph()
    monkeypatch.setitem(sys.modules, "agent", agent_module)
    monkeypatch.setitem(sys.modules, "langchain_core", ModuleType("langchain_core"))
    monkeypatch.setitem(sys.modules, "langchain_core.messages", messages_module)
    answer, events, payload = AgentBridge().run("thread-1", "Cari RKS")
    assert answer == "Ini ringkasannya."
    assert [event.status for event in events] == ["invoked", "completed"]
    assert payload["title"] == "RKS"
    assert _tool_payload("not a dict") is None


def test_document_bridge_does_not_accept_paths_outside_data():
    assert DocumentBridge._find_source_pdf("../../secret.pdf") is None


def test_document_bridge_uses_root_parser_and_existing_pdf():
    pdf = next(DATA_DIR.glob("*.pdf"))
    detail, source = DocumentBridge().from_agent_payload({
        "title": "RKS Contoh",
        "source_file": pdf.name,
        "full_docs": "BAB 1 PENDAHULUAN\n\nUraian pekerjaan.\n\nBAB 2 RUANG LINGKUP\n\nRincian pekerjaan.",
    })
    assert detail.can_convert is True
    assert detail.pdf_url == f"/api/documents/{detail.id}/pdf"
    assert len(detail.chapters) >= 2
    assert source == pdf.resolve()


def test_pdf_and_docx_downloads_use_registered_ids(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.DATA_DIR", tmp_path)
    monkeypatch.setattr("backend.app.OUTPUT_DIR", tmp_path)
    state = MemoryStore()
    thread = state.create_thread("Unduhan")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF")
    document = DocumentDetail(id="doc-1", title="RKS", content="Isi", chapters=[], can_convert=True)
    state.add_document(thread.id, document, source)
    output = tmp_path / "result.docx"
    output.write_bytes(b"DOCX test bytes")
    file_id = state.add_file(document.id, output).id

    app = create_app()
    app.dependency_overrides[get_store] = lambda: state
    client = TestClient(app)
    assert client.get("/api/documents/doc-1/pdf").content.startswith(b"%PDF")
    download = client.get(f"/api/files/{file_id}/download")
    assert download.status_code == 200
    assert download.content == b"DOCX test bytes"
    assert "result.docx" in download.headers["content-disposition"]

    outside = tmp_path.parent / "outside.docx"
    unsafe_id = state.add_file(document.id, outside).id
    assert client.get(f"/api/files/{unsafe_id}/download").status_code == 404
