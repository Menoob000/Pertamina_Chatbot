import os
import re
import json
import uuid
import ast
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from textwrap import dedent
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
try:
    from agent import app, tools
    AGENT_IMPORT_ERROR = None
except Exception as exc:
    # Keep the independent Tender Generator usable when chatbot setup is
    # incomplete (for example, OPENROUTER_API_KEY is not configured yet).
    app, tools = None, []
    AGENT_IMPORT_ERROR = str(exc)
try:
    from tools.tender.streamlit_tender_view import render_tender_generator_page
except Exception:
    try:
        import importlib
        import tools.tender.streamlit_tender_view as _tv
        importlib.reload(_tv)
        render_tender_generator_page = _tv.render_tender_generator_page
    except Exception as _tv_err:
        def render_tender_generator_page(*args, **kwargs):
            st.error(f"Gagal memuat modul Tender Generator: {_tv_err}")

try:
    from tools.rks.streamlit_view import render_rks_page, render_chat_preview
except Exception:
    def render_rks_page(*args, **kwargs):
        st.error("Gagal memuat modul RKS Generator.")
    def render_chat_preview(*args, **kwargs):
        pass

try:
    from tools.rks.library_view import render_rks_library
except Exception:
    def render_rks_library(*args, **kwargs):
        st.error("Gagal memuat modul Gudang RKS.")

try:
    from tools.tender.contract_library_view import render_contract_library
except Exception:
    def render_contract_library(*args, **kwargs):
        st.error("Gagal memuat modul Gudang Kontrak.")

try:
    from tools.amendment.streamlit_amendment_view import render_amendment_generator_page
except Exception:
    def render_amendment_generator_page(*args, **kwargs):
        st.error("Gagal memuat modul Amandemen Generator.")

try:
    from tools.amendment.library_view import render_amendment_library
except Exception:
    def render_amendment_library(*args, **kwargs):
        st.error("Gagal memuat modul Gudang Amandemen.")
try:
    from tools.gdrive.streamlit_view import render_gdrive_settings_section
except Exception:
    def render_gdrive_settings_section():
        st.markdown("**☁️ Integrasi Google Drive**")
        st.info("Pustaka Google Drive belum selesai diinstal di server cloud. Silakan Clear cache and deploy di Streamlit Cloud.")
from tools.rks.chat import current_document as select_chat_document
from tools.docx_exporter import parse_text_to_rks_data
from tools.pdf_converter import find_matching_pdf, convert_pdf_to_docx_layout, get_pdf_metadata, DATA_DIR
from rag.conversation_store import ConversationStore

# ---------------------------------------------------------------------------
# Page Configuration & Professional Theming
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pertamina Knowledge Assistant",
    page_icon="assets/logo_pertamina.png" if os.path.exists("assets/logo_pertamina.png") else "🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html(
    dedent("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #FFFFFF;
        color: #0F172A;
    }

    header[data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.95);
        border-bottom: 1px solid #F1F5F9;
    }
    footer {
        display: none !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.8rem;
        padding-bottom: 1.8rem;
    }

    /* Top App Bar */
    .app-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.4rem 0rem 0.8rem 0rem;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 1.2rem;
    }
    .brand-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brand-accent-blue {
        color: #0072CE;
    }
    .brand-accent-red {
        color: #ED1C24;
    }
    .thread-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: #F1F5F9;
        color: #334155;
        border: 1px solid #E2E8F0;
    }

    /* Messages */
    .stChatMessage {
        border-radius: 12px !important;
        margin-bottom: 0.8rem !important;
        padding: 0.9rem 1.1rem !important;
    }
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat message from user"]) {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
    }
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat message from assistant"]) {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }

    /* Badges */
    .tool-badge-blue {
        background-color: #EFF6FF;
        color: #0072CE;
        border: 1px solid #BFDBFE;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .tool-badge-red {
        background-color: #FEF2F2;
        color: #ED1C24;
        border: 1px solid #FECACA;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .doc-title-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        color: #166534;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.82rem;
        margin: 4px 0;
    }

    /* Document Viewer */
    .doc-viewer-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        padding: 1.5rem;
        position: relative;
    }
    .doc-top-stripe {
        height: 4px;
        width: 100%;
        background: linear-gradient(90deg, #0072CE 65%, #ED1C24 100%);
        border-radius: 4px 4px 0 0;
        margin-bottom: 1rem;
    }
    .doc-paper-header {
        border-bottom: 2px solid #F1F5F9;
        padding-bottom: 0.8rem;
        margin-bottom: 1rem;
    }
    .doc-paper-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.3rem;
        word-break: break-word;
    }
    .doc-metadata-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        background-color: #EFF6FF;
        color: #0072CE;
        margin-right: 6px;
    }
    .doc-metadata-csms {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        background-color: #FEF2F2;
        color: #ED1C24;
        margin-right: 6px;
    }
    .doc-paper-body {
        max-height: 62vh;
        overflow-y: auto;
        padding-right: 0.5rem;
        font-size: 0.9rem;
        line-height: 1.6;
        color: #1E293B;
    }

    .doc-empty-state {
        text-align: center;
        padding: 4rem 1.5rem;
        color: #64748B;
        border: 2px dashed #E2E8F0;
        border-radius: 12px;
        background-color: #FAFAFA;
    }

    .download-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #ED1C24;
        border-radius: 10px;
        padding: 12px 16px;
        margin-top: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(237, 28, 36, 0.05);
    }
    .download-info {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .download-title {
        font-weight: 700;
        color: #0F172A;
        font-size: 0.92rem;
    }
    .download-sub {
        font-size: 0.78rem;
        color: #64748B;
    }

    .hero-container {
        text-align: center;
        padding: 2rem 1rem 1.5rem 1rem;
        margin: 0 auto;
    }
    .hero-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 0.5rem;
        margin-bottom: 0.3rem;
    }
    .hero-sub {
        font-size: 0.9rem;
        color: #64748B;
        margin-bottom: 1.5rem;
        line-height: 1.4;
    }

    button[kind="primary"] {
        background-color: #0072CE !important;
        border-color: #0072CE !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    button[kind="primary"]:hover {
        background-color: #005bb5 !important;
        border-color: #005bb5 !important;
    }

    div[data-testid="stChatInput"] {
        border-radius: 16px !important;
    }

    /* Sidebar conversation rows & hover delete button */
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
        position: relative;
        align-items: center !important;
        margin-bottom: 2px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="column"]:first-child button {
        text-align: left !important;
        justify-content: flex-start !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="column"]:first-child button p {
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child button {
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.2s ease, visibility 0.2s ease, background-color 0.15s ease, color 0.15s ease;
        border: none !important;
        background: transparent !important;
        color: #94A3B8 !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        padding: 0 !important;
        min-height: 38px !important;
        height: 38px !important;
        border-radius: 6px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:hover div[data-testid="column"]:last-child button,
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child button:focus {
        opacity: 1;
        visibility: visible;
    }

    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child button:hover {
        color: #ED1C24 !important;
        background-color: #FEE2E2 !important;
    }
    </style>
    """),
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
CHAT_IDENTITY_MODE = "single"  # Ganti ke "multi" untuk identitas per pengguna; token URL bukan pengganti login pada akses publik.
if CHAT_IDENTITY_MODE == "single":
    owner_token = "local_single_user"
    if "chat_owner" in st.query_params:
        del st.query_params["chat_owner"]
else:
    owner_token = st.query_params.get("chat_owner", "")
    if not re.fullmatch(r"[0-9a-f]{32}", owner_token):
        owner_token = uuid.uuid4().hex
        st.query_params["chat_owner"] = owner_token
if st.session_state.get("_chat_owner_token") not in (None, owner_token):
    for key in ("threads", "current_thread_id", "_chat_store_synced_owner",
                "_chat_migrated_threads"):
        st.session_state.pop(key, None)
st.session_state["_chat_owner_token"] = owner_token

try:
    chat_store = ConversationStore(owner_token, single_user=CHAT_IDENTITY_MODE == "single")
    chat_store.initialize()
except Exception as exc:
    chat_store = None
    st.warning(f"Riwayat percakapan belum terhubung ke PostgreSQL: {exc}")


def init_session_state():
    if "threads" not in st.session_state:
        saved_threads = chat_store.list_threads() if chat_store else []
        if saved_threads:
            st.session_state.threads = {item["id"]: item for item in saved_threads}
            requested = st.query_params.get("chat_thread", "")
            st.session_state.current_thread_id = (
                requested if requested in st.session_state.threads else saved_threads[0]["id"]
            )
        else:
            initial_thread_id = f"thread_{uuid.uuid4().hex}"
            st.session_state.threads = {
                initial_thread_id: {
                    "id": initial_thread_id,
                    "title": "Chat 1",
                    "created_at": datetime.now().strftime("%H:%M"),
                    "tool_history": [],
                }
            }
            st.session_state.current_thread_id = initial_thread_id
            if chat_store:
                chat_store.create_thread(initial_thread_id, "Chat 1")
        st.query_params["chat_thread"] = st.session_state.current_thread_id

    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]

    if chat_store and st.session_state.get("_chat_store_synced_owner") != owner_token:
        for thread in st.session_state.threads.values():
            chat_store.ensure_thread(thread["id"], thread["title"])
        st.session_state["_chat_store_synced_owner"] = owner_token

    if "active_tool_now" not in st.session_state:
        st.session_state.active_tool_now = None

    if "prefilled_prompt" not in st.session_state:
        st.session_state.prefilled_prompt = None

    if "show_split_viewer" not in st.session_state:
        st.session_state.show_split_viewer = False

    if "dialog_converted_file" not in st.session_state:
        st.session_state.dialog_converted_file = None

init_session_state()

current_thread_id = st.session_state.current_thread_id
if current_thread_id not in st.session_state.threads:
    current_thread_id = list(st.session_state.threads.keys())[0]
    st.session_state.current_thread_id = current_thread_id

current_thread = st.session_state.threads[current_thread_id]

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def create_new_thread():
    new_id = f"thread_{uuid.uuid4().hex}"
    chat_idx = len(st.session_state.threads) + 1
    if chat_store:
        chat_store.create_thread(new_id, f"Chat {chat_idx}")
    st.session_state.threads[new_id] = {
        "id": new_id,
        "title": f"Chat {chat_idx}",
        "created_at": datetime.now().strftime("%H:%M"),
        "tool_history": [],
    }
    st.session_state.current_thread_id = new_id
    st.query_params["chat_thread"] = new_id
    st.session_state.active_tool_now = None


def delete_thread_by_id(thread_id: str):
    """Delete a thread from database and session state."""
    if chat_store:
        try:
            chat_store.delete_thread(thread_id)
        except Exception as e:
            logger.warning(f"Error deleting thread {thread_id} from DB: {e}")
    if thread_id in st.session_state.threads:
        del st.session_state.threads[thread_id]

    if len(st.session_state.threads) == 0:
        create_new_thread()
    elif st.session_state.current_thread_id == thread_id:
        st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]
        st.query_params["chat_thread"] = st.session_state.current_thread_id
        st.session_state.active_tool_now = None


def get_thread_messages(thread_id: str):
    """Restore persisted messages to LangGraph when its in-memory state is empty."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = app.get_state(config)
        messages = state.values.get("messages", []) if state and state.values else []
        if messages and chat_store:
            migrated = st.session_state.setdefault("_chat_migrated_threads", set())
            if thread_id not in migrated:
                try:
                    if not chat_store.load_messages(thread_id):
                        chat_store.save_messages(thread_id, messages)
                    migrated.add(thread_id)
                except Exception as exc:
                    st.warning(f"Riwayat percakapan belum tersimpan: {exc}")
        elif chat_store:
            messages = chat_store.load_messages(thread_id)
            if messages:
                app.update_state(config, {"messages": messages}, as_node="agent")
        return messages
    except Exception as e:
        st.error(f"Error fetching state for thread {thread_id}: {e}")
    return []


def persist_thread_messages(thread_id: str):
    if not chat_store:
        return
    try:
        state = app.get_state({"configurable": {"thread_id": thread_id}})
        if state and state.values:
            chat_store.save_messages(thread_id, state.values.get("messages", []))
    except Exception as exc:
        st.error(f"Percakapan belum tersimpan ke database: {exc}")


def extract_docx_path(text: str) -> Optional[str]:
    """Finds an existing .docx file path or filename in text."""
    if not text:
        return None
    match = re.search(r'([a-zA-Z]:[\\/][^:\*\?"<>\|\r\n]+\.docx)', text)
    if match:
        cand = match.group(1).strip()
        if os.path.exists(cand):
            return cand

    match_file = re.search(r'([a-zA-Z0-9_\-\.\+\s]+\.docx)', text)
    if match_file:
        cand_name = match_file.group(1).strip()
        local_cand = os.path.join("output", cand_name)
        if os.path.exists(local_cand):
            return os.path.abspath(local_cand)

    return None


def get_current_thread_document(thread_id: str) -> Optional[Dict[str, Any]]:
    return select_chat_document(get_thread_messages(thread_id))


def format_tool_output_display(tc_name: str, raw_content: Any) -> Any:
    """Nicely formats and displays RAG and Conversion tool outputs."""
    if tc_name == "create_rks_document":
        try:
            artifact = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            st.write(f"Status RKS: {artifact.get('status', 'belum tersedia')}")
            if artifact.get("source"):
                st.caption(artifact["source"]["filename"])
            st.caption("Halaman hasil dan unduhan tersedia pada panel Pratinjau halaman.")
        except (ValueError, TypeError):
            st.text(str(raw_content))
        return
    content = raw_content
    if isinstance(content, str):
        if content.startswith("{") or content.startswith("["):
            try:
                content = ast.literal_eval(content)
            except Exception:
                pass

    if tc_name == "fetch_full_documents" and isinstance(content, dict):
        title = content.get("title", "Untitled Document")
        st.html(f"<div class='doc-title-badge'>📄 Document Title: <strong>{title}</strong></div>")
        full_text = content.get("full_docs", "")
        st.caption(f"Fetched full content ({len(full_text)} characters). Preview below:")
        st.text(full_text[:500] + ("..." if len(full_text) > 500 else ""))
        return

    if tc_name == "fetch_relevant_documents" and isinstance(content, list):
        st.markdown(f"**Retrieved {len(content)} Document Passages:**")
        for idx, item in enumerate(content, 1):
            if isinstance(item, dict):
                t = item.get("title") or item.get("document_title", "Unknown Document")
                score = item.get("relevance_score") or item.get("score", "N/A")
                snippet = str(item.get("content", ""))[:200]
                st.html(f"{idx}. <span class='doc-title-badge'>📄 {t}</span> <span style='font-size:0.75rem; color:#64748B;'>Score: {score}</span>")
                st.caption(f"> {snippet}...")
        return

    if tc_name in ("convert_pdf_to_docx", "export_to_docx"):
        st.success(str(raw_content))
        return

    st.text(str(raw_content)[:800])


def render_docx_download_card(file_path: str, key: str):
    """Renders a corporate Pertamina styled card with a download button for DOCX."""
    if file_path and os.path.exists(file_path):
        fname = os.path.basename(file_path)
        file_size_kb = os.path.getsize(file_path) / 1024
        with open(file_path, "rb") as f:
            data = f.read()

        st.html(
            f"""
            <div class="download-card">
                <div class="download-info">
                    <span class="download-title">📄 {fname}</span>
                    <span class="download-sub">Converted Word DOCX • {file_size_kb:.1f} KB</span>
                </div>
            </div>
            """,
        )
        st.download_button(
            label=f"📥 Download {fname}",
            data=data,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=key,
            type="primary",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Requirement 3: Streamlit Modal Popup for PDF -> DOCX Conversion
# ---------------------------------------------------------------------------
@st.dialog("🔄 Convert PDF to Word (DOCX)")
def open_pdf_converter_dialog(pdf_path: str, doc_title: str):
    """Modal popup dialog that converts a retrieved database PDF directly to DOCX with layout preservation."""
    st.markdown(f"#### 📄 **{doc_title}**")

    if not pdf_path or not os.path.exists(pdf_path):
        st.error(f"Source PDF file could not be found on disk for '{doc_title}'.")
        return

    meta = get_pdf_metadata(pdf_path)

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Total Pages", f"{meta.get('page_count', 1)} pages")
    with col_m2:
        st.metric("Original Size", f"{meta.get('file_size_kb', 0)} KB")

    st.write("")
    st.info("ℹ️ **Direct Layout Engine:** Converts tables, graphics, headers, and original formatting directly into Microsoft Word (.docx).")

    suggested_docx_name = f"{Path(pdf_path).stem}.docx"
    custom_name = st.text_input("Output Filename", value=suggested_docx_name, key="dialog_output_filename_input")

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("🚀 Start Conversion", type="primary", use_container_width=True, key="btn_run_dialog_conversion"):
            with st.spinner(f"Converting {meta.get('page_count', 1)} pages into Word layout..."):
                try:
                    res_path = convert_pdf_to_docx_layout(pdf_path, output_filename=custom_name)
                    st.session_state.dialog_converted_file = res_path
                    st.success(f"✅ Conversion successful! Saved to: `{os.path.basename(res_path)}`")
                except Exception as e:
                    st.error(f"Conversion failed: {e}")

    # If converted, show the instant download button inside modal
    if st.session_state.dialog_converted_file and os.path.exists(st.session_state.dialog_converted_file):
        out_fpath = st.session_state.dialog_converted_file
        out_fname = os.path.basename(out_fpath)
        out_size = os.path.getsize(out_fpath) / 1024
        st.divider()
        st.markdown(f"**🎉 Ready for download:** `{out_fname}` ({out_size:.1f} KB)")
        with open(out_fpath, "rb") as df:
            st.download_button(
                label=f"📥 Download {out_fname}",
                data=df.read(),
                file_name=out_fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="btn_download_from_dialog",
                type="primary",
                use_container_width=True,
            )


@st.dialog("Konfirmasi Hapus Percakapan")
def confirm_delete_thread_dialog(thread_id: str, thread_title: str):
    """Popup modal dialog to confirm chat thread deletion."""
    st.markdown("Apakah Anda yakin ingin menghapus percakapan berikut?")
    st.markdown(f"#### 💬 **{thread_title}**")
    st.caption("⚠️ Riwayat chat dalam percakapan ini akan dihapus secara permanen.")
    st.write("")
    col_cancel, col_del = st.columns([1, 1])
    with col_cancel:
        if st.button("Batal", key=f"cancel_del_{thread_id}", use_container_width=True):
            st.rerun()
    with col_del:
        if st.button("🗑️ Hapus", type="primary", key=f"confirm_del_{thread_id}", use_container_width=True):
            delete_thread_by_id(thread_id)
            st.rerun()


AVATAR_ASSISTANT = "assets/logo_pertamina.png" if os.path.exists("assets/logo_pertamina.png") else "🤖"
AVATAR_USER = "👤"


# ---------------------------------------------------------------------------
# Sidebar: ChatGPT-like History & Tools Monitor
# ---------------------------------------------------------------------------
def _close_rks_pages():
    st.session_state["show_rks_page"] = False
    st.session_state["show_rks_library"] = False
    st.session_state["show_contract_library"] = False
    st.session_state["show_amendment_library"] = False


with st.sidebar:
    if os.path.exists("assets/logo_pertamina.png"):
        st.image("assets/logo_pertamina.png", width=160)
    else:
        st.markdown("### 🏢 **PERTAMINA**")

    st.caption("AI Document & Knowledge Assistant")
    st.write("")

    # Navigation Switcher
    if st.button("Pembuatan RKS dan preview", key="open_rks_page", use_container_width=True):
        st.session_state["show_rks_page"] = True
        st.session_state["show_rks_library"] = False
        st.session_state["show_contract_library"] = False
        st.session_state["show_amendment_library"] = False
    if st.button("Gudang RKS", key="open_rks_library", use_container_width=True):
        st.session_state["show_rks_library"] = True
        st.session_state["show_rks_page"] = False
        st.session_state["show_contract_library"] = False
        st.session_state["show_amendment_library"] = False
    if st.button("Gudang Rancangan Kontrak", key="open_contract_library", use_container_width=True):
        st.session_state["show_contract_library"] = True
        st.session_state["show_rks_page"] = False
        st.session_state["show_rks_library"] = False
        st.session_state["show_amendment_library"] = False
    if st.button("Gudang Dokumen Amandemen", key="open_amendment_library", use_container_width=True):
        st.session_state["show_amendment_library"] = True
        st.session_state["show_rks_page"] = False
        st.session_state["show_rks_library"] = False
        st.session_state["show_contract_library"] = False
    if st.session_state.get("show_rks_page") and st.button("Kembali ke chat / generator", key="close_rks_page"):
        st.session_state["show_rks_page"] = False
    if st.session_state.get("show_rks_library") and st.button("Kembali ke chat / generator", key="close_rks_library"):
        st.session_state["show_rks_library"] = False
    if st.session_state.get("show_contract_library") and st.button("Kembali ke chat / generator", key="close_contract_library"):
        st.session_state["show_contract_library"] = False
    if st.session_state.get("show_amendment_library") and st.button("Kembali ke chat / generator", key="close_amendment_library"):
        st.session_state["show_amendment_library"] = False

    nav_index = 0
    if st.session_state.get("nav_choice") == "tender":
        nav_index = 1
    elif st.session_state.get("nav_choice") == "amendment":
        nav_index = 2

    nav_selection = st.radio(
        "Menu Navigasi",
        ["💬 Chatbot & RKS Viewer", "📑 Dokumen Tender Generator", "📝 Dokumen Amendemen Generator"],
        index=nav_index,
        key="app_nav_radio_menu",
        label_visibility="collapsed",
        on_change=_close_rks_pages,
    )
    if "Amendemen" in nav_selection:
        st.session_state.nav_choice = "amendment"
    elif "Tender" in nav_selection:
        st.session_state.nav_choice = "tender"
    else:
        st.session_state.nav_choice = "chat"

    st.write("")

    if st.button("➕ New Chat", key="btn_create_new_thread", use_container_width=True, type="primary"):
        create_new_thread()
        st.rerun()

    st.write("")
    st.html("<p style='font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;'>Recent Conversations</p>")

    thread_keys = list(st.session_state.threads.keys())
    for t_id in thread_keys:
        thread_info = st.session_state.threads[t_id]
        is_active = (t_id == current_thread_id)

        button_label = f"{'🔹 ' if is_active else '💬 '}{thread_info['title']}"
        col_thread, col_del = st.columns([5.3, 1.1], gap="small", vertical_alignment="center")
        with col_thread:
            if st.button(
                button_label,
                key=f"thread_select_btn_{t_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.current_thread_id = t_id
                st.query_params["chat_thread"] = t_id
                st.rerun()
        with col_del:
            if st.button("✕", key=f"btn_del_thread_{t_id}", help="Hapus percakapan", use_container_width=True):
                confirm_delete_thread_dialog(t_id, thread_info["title"])

    st.write("")
    st.divider()

    # Outer tag details: Pengaturan Tambahan containing individual expandable elements
    with st.expander("Pengaturan Tambahan", expanded=False):
        # 1. Current Session Settings Element
        with st.expander("⚙️ Current Session Settings", expanded=False):
            st.text(f"Thread: {current_thread_id}")
            new_title = st.text_input("Rename Session", value=current_thread["title"], key="rename_title_input")
            if st.button("Save Name", key="btn_save_thread_name", use_container_width=True):
                if new_title.strip():
                    if chat_store:
                        chat_store.rename_thread(current_thread_id, new_title.strip())
                    st.session_state.threads[current_thread_id]["title"] = new_title.strip()
                    st.rerun()

            if st.button("🗑️ Delete Session", key="btn_delete_current_thread", use_container_width=True):
                confirm_delete_thread_dialog(current_thread_id, current_thread["title"])

        # 2. Agent Capabilities Element
        with st.expander("⚡ Agent Capabilities", expanded=False):
            if st.session_state.active_tool_now:
                st.html(
                    f"<div style='padding:6px 10px; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; font-size:0.8rem; color:#0072CE; font-weight:600; margin-bottom:8px;'>"
                    f"⚡ Running: <code>{st.session_state.active_tool_now}</code></div>",
                )
            else:
                st.html(
                    "<div style='padding:6px 10px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; font-size:0.8rem; color:#475569; font-weight:600; margin-bottom:8px;'>"
                    "🟢 Agent Status: Ready</div>",
                )

            st.caption("Available Tools:")
            for t in tools:
                t_name = getattr(t, "name", str(t))
                t_desc = getattr(t, "description", "")
                is_convert = "convert" in t_name or "docx" in t_name
                badge_class = "tool-badge-red" if is_convert else "tool-badge-blue"
                st.html(
                    f"<div style='margin-bottom:6px;'>"
                    f"<span class='{badge_class}'>● {t_name}</span><br>"
                    f"<span style='font-size:0.75rem; color:#64748B;'>{t_desc.strip().splitlines()[0][:70]}</span>"
                    f"</div>",
                )

        # 3. Database PDF Converter Shortcut Element
        all_repo_pdfs = list(DATA_DIR.glob("*.pdf")) if DATA_DIR.exists() else []
        if all_repo_pdfs:
            with st.expander("🔄 Convert Any Repository PDF", expanded=False):
                st.caption("Select any PDF from the repository database to convert via popup dialog:")
                pdf_options = {p.name: str(p.resolve()) for p in all_repo_pdfs}
                selected_pdf_name = st.selectbox("Choose PDF", list(pdf_options.keys()), key="sidebar_pdf_selector")
                if st.button("Open Conversion Popup", key="btn_open_sidebar_dialog", use_container_width=True):
                    open_pdf_converter_dialog(pdf_options[selected_pdf_name], selected_pdf_name)

        # 4. Converted Documents Element
        output_dir = Path("./output")
        if output_dir.exists():
            docx_files = sorted(list(output_dir.glob("*.docx")), key=os.path.getmtime, reverse=True)
            if docx_files:
                with st.expander(f"📁 Converted Documents ({len(docx_files)})", expanded=False):
                    for f_idx, docx_file in enumerate(docx_files[:4]):
                        f_name = docx_file.name
                        f_size = docx_file.stat().st_size / 1024
                        st.html(f"<span style='font-size:0.82rem; font-weight:600;'>📄 {f_name[:24]}...</span> <span style='font-size:0.75rem; color:#64748B;'>({f_size:.1f} KB)</span>")
                        with open(docx_file, "rb") as df:
                            st.download_button(
                                label="⬇️ Download",
                                data=df.read(),
                                file_name=f_name,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"sidebar_dl_{f_idx}_{f_name}",
                                use_container_width=True,
                            )

        # 5. Google Drive Knowledge Base Integration Element
        with st.expander("☁️ Integrasi Google Drive (RKS Knowledge Base)", expanded=False):
            render_gdrive_settings_section()


# ---------------------------------------------------------------------------
# Navigation Dispatcher: Tender Generator vs Chatbot & RKS Viewer
# ---------------------------------------------------------------------------
if st.session_state.get("show_rks_page"):
    render_rks_page()
    st.stop()

if st.session_state.get("show_rks_library"):
    render_rks_library()
    st.stop()

if st.session_state.get("show_contract_library"):
    render_contract_library()
    st.stop()

if st.session_state.get("show_amendment_library"):
    render_amendment_library()
    st.stop()

if st.session_state.get("nav_choice") == "amendment":
    render_amendment_generator_page()
    st.stop()

if st.session_state.get("nav_choice") == "tender":
    render_tender_generator_page(render_docx_download_card, chat_store=chat_store,
                                 thread_id=current_thread_id)
    st.stop()

if app is None:
    st.error(
        "Chatbot belum dapat dimulai karena konfigurasi atau dependensinya belum lengkap. "
        "Periksa OPENROUTER_API_KEY pada file .env di direktori proyek."
    )
    with st.expander("Detail error"):
        st.code(AGENT_IMPORT_ERROR or "Unknown agent initialization error")
    st.stop()

# ---------------------------------------------------------------------------
# Main Header & Split-Screen View Controls
# ---------------------------------------------------------------------------
thread_messages = get_thread_messages(current_thread_id)
current_doc_data = get_current_thread_document(current_thread_id)

top_col1, top_col2, top_col3 = st.columns([3, 1, 1])
with top_col1:
    st.html(
        f"""
        <div class="brand-title">
            <span class="brand-accent-blue">Pertamina</span> <span class="brand-accent-red">Knowledge</span> Assistant
            <span class="thread-pill">💬 {current_thread['title']}</span>
        </div>
        """,
    )
with top_col2:
    # Popup Button in Topbar when an RKS document is loaded
    if current_doc_data and current_doc_data.get("pdf_path"):
        if st.button("🔄 Convert PDF", key="top_convert_popup_btn", type="primary", use_container_width=True):
            open_pdf_converter_dialog(current_doc_data["pdf_path"], current_doc_data["title"])
with top_col3:
    split_label = "📖 Hide Viewer" if st.session_state.show_split_viewer else "📖 Split Viewer"
    if st.button(split_label, key="toggle_split_viewer", use_container_width=True):
        st.session_state.show_split_viewer = not st.session_state.show_split_viewer
        st.rerun()

st.write("")

# ---------------------------------------------------------------------------
# Layout: Split-Screen (Chat Left | Document Viewer Right)
# ---------------------------------------------------------------------------
if st.session_state.show_split_viewer:
    chat_col, doc_col = st.columns([11, 10], gap="large")
else:
    chat_col = st.container()
    doc_col = None

# ===========================================================================
# LEFT COLUMN: ChatGPT-style Conversation
# ===========================================================================
with chat_col:
    # Empty State Hero
    if len(thread_messages) == 0:
        st.html(
            """
            <div class="hero-container">
                <div style="display:inline-block; padding:8px 12px; border-radius:50%; background:#F1F5F9; margin-bottom:8px;">
                    <span style="font-size:1.8rem;">⚡</span>
                </div>
                <div class="hero-title">Pertamina Document Assistant</div>
                <div class="hero-sub">
                    Retrieve official RKS document templates, inspect them in the split viewer, and convert original PDFs directly into Word (.docx) with preserved layout.
                </div>
            </div>
            """,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📄 **Fetch RKS**\n\nAmbil template RKS overhaul tangki", key="starter_rks", use_container_width=True):
                st.session_state.prefilled_prompt = "Tolong ambilkan dokumen full RKS untuk overhaul tangki"
                st.rerun()
        with col2:
            if st.button("🔍 **Check CSMS**\n\nCek persyaratan CSMS kategori High", key="starter_csms", use_container_width=True):
                st.session_state.prefilled_prompt = "Apa saja persyaratan aspek CSMS untuk kategori High?"
                st.rerun()
        with col3:
            if st.button("🔄 **Convert PDF**\n\nConvert PDF RKS terakhir ke DOCX", key="starter_docx", use_container_width=True):
                st.session_state.prefilled_prompt = "Convert dokumen PDF RKS terakhir ke docx format"
                st.rerun()

        st.write("")

    # Render Conversation History
    i = 0
    while i < len(thread_messages):
        msg = thread_messages[i]

        if isinstance(msg, SystemMessage):
            i += 1
            continue

        elif isinstance(msg, HumanMessage):
            with st.chat_message("user", avatar=AVATAR_USER):
                st.markdown(msg.content)
            i += 1

        elif isinstance(msg, AIMessage):
            detected_file_path = None

            # Tool Calls inside Message
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_name = tc.get("name", "Tool")
                    tc_args = tc.get("args", {})
                    tc_id = tc.get("id")

                    matching_tool_msg = None
                    for candidate in thread_messages[i+1:]:
                        if isinstance(candidate, ToolMessage) and getattr(candidate, "tool_call_id", None) == tc_id:
                            matching_tool_msg = candidate
                            break

                    is_convert = "convert" in tc_name or "docx" in tc_name
                    badge_type = "tool-badge-red" if is_convert else "tool-badge-blue"

                    with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
                        with st.status(f"⚙️ Tool: {tc_name}", state="complete", expanded=False):
                            st.html(f"<span class='{badge_type}'>Invoked: {tc_name}</span>")
                            st.write("**Inputs:**")
                            st.json(tc_args)
                            if matching_tool_msg:
                                st.write("**Tool Results:**")
                                format_tool_output_display(tc_name, matching_tool_msg.content)

                    if matching_tool_msg:
                        f_cand = extract_docx_path(str(matching_tool_msg.content))
                        if f_cand:
                            detected_file_path = f_cand

            # Direct Message Text
            if msg.content:
                with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
                    st.markdown(msg.content)
                    f_cand = extract_docx_path(msg.content)
                    if f_cand:
                        detected_file_path = f_cand
                        st.session_state["last_exported_docx"] = f_cand

            # Render download card if docx was produced
            if detected_file_path:
                with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
                    render_docx_download_card(detected_file_path, key=f"hist_msg_dl_{i}_{uuid.uuid4().hex[:4]}")

            i += 1

        elif isinstance(msg, ToolMessage):
            i += 1
        else:
            i += 1


# ===========================================================================
# RIGHT COLUMN: Split-Screen Live Document Viewer
# ===========================================================================
if doc_col:
    with doc_col:
        st.html(
            """
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                <span style="font-weight:700; font-size:1.1rem; color:#0F172A;">📄 Document Viewer</span>
                <span style="font-size:0.75rem; color:#64748B; font-weight:600;">LIVE PREVIEW</span>
            </div>
            """,
        )

        if not current_doc_data:
            st.html(
                """
                <div class="doc-empty-state">
                    <span style="font-size:2.4rem;">📑</span>
                    <h4 style="margin-top:10px; margin-bottom:6px; color:#334155;">No Document Loaded</h4>
                    <p style="font-size:0.85rem; max-width:340px; margin:0 auto; line-height:1.4;">
                        Ask the assistant to fetch an RKS (e.g. <em>"Ambilkan RKS overhaul tangki"</em>) to inspect its full content and convert its original PDF.
                    </p>
                </div>
                """,
            )
        else:
            doc_raw = current_doc_data["content"]
            rag_doc_title = current_doc_data.get("title", "")
            source_file = current_doc_data.get("source_file", "")
            pdf_path = current_doc_data.get("pdf_path")

            parsed_rks = parse_text_to_rks_data(doc_raw, custom_title=rag_doc_title)
            display_title = rag_doc_title or parsed_rks.get("cover_page", {}).get("judul_pekerjaan", "DOKUMEN RKS")
            doc_csms = parsed_rks.get("cover_page", {}).get("resiko_csms", "HIGH")
            doc_no = parsed_rks.get("metadata", {}).get("nomor_dokumen", "RKS/PERTAMINA/2026")
            babs = parsed_rks.get("bab", [])

            # Paper Card Container showing explicit document title
            st.html(
                f"""
                <div class="doc-viewer-container">
                    <div class="doc-top-stripe"></div>
                    <div class="doc-paper-header">
                        <div class="doc-paper-title">📄 {display_title}</div>
                        <div style="margin-top:6px;">
                            <span class="doc-metadata-pill">📁 File: {source_file or display_title}</span>
                            <span class="doc-metadata-csms">Draf referensi</span>
                            <span class="doc-metadata-pill">Pratinjau DOCX</span>
                        </div>
                    </div>
                </div>
                """,
            )

            # Document Viewer Tabs
            tab_preview, tab_source, tab_outline, tab_convert = st.tabs(["Pratinjau halaman", "Teks sumber", "Daftar bab", "Konversi PDF asli"])

            with tab_preview:
                render_chat_preview(current_doc_data, current_thread_id)

            with tab_source:
                if doc_raw:
                    st.markdown(doc_raw)
                else:
                    st.caption("Isi dokumen ditampilkan pada tab Pratinjau halaman dari hasil DOCX.")

            with tab_outline:
                if babs:
                    for b in babs:
                        b_num = b.get("nomor", "")
                        b_title = b.get("judul", "")
                        sub_list = b.get("sub_bab", [])
                        st.markdown(f"**BAB {b_num} — {b_title}** `({len(sub_list)} sub-bab)`")
                        for s in sub_list:
                            s_no = s.get("nomor", "")
                            s_title = s.get("judul", "")
                            st.caption(f"• {s_no} {s_title}")
                        st.write("")
                else:
                    st.caption("No chapters identified in the text.")

            with tab_convert:
                st.markdown("#### Direct PDF to DOCX Conversion")
                st.caption("Converts the original PDF file directly into Word format preserving tables, formatting, and layout.")

                if pdf_path and os.path.exists(pdf_path):
                    p_meta = get_pdf_metadata(pdf_path)
                    st.write(f"**Source File:** `{p_meta.get('file_name')}` ({p_meta.get('page_count')} pages, {p_meta.get('file_size_kb')} KB)")

                    # Popup Modal Trigger Button
                    if st.button("🚀 Open Conversion Popup", key="btn_trigger_pdf_popup", type="primary", use_container_width=True):
                        open_pdf_converter_dialog(pdf_path, display_title)
                else:
                    st.warning("Original PDF file was not found in `./data/` for this document.")


# ---------------------------------------------------------------------------
# Chat Input & Streaming Execution
# ---------------------------------------------------------------------------
initial_input = st.session_state.prefilled_prompt
if initial_input:
    user_prompt = initial_input
    st.session_state.prefilled_prompt = None
else:
    user_prompt = st.chat_input("Ask a question, fetch an RKS, or convert PDF to DOCX...")

if user_prompt:
    with chat_col:
        with st.chat_message("user", avatar=AVATAR_USER):
            st.markdown(user_prompt)

    if current_thread["title"].startswith("Chat ") and len(thread_messages) == 0:
        suggested_title = user_prompt.strip()[:24] + ("..." if len(user_prompt.strip()) > 24 else "")
        if chat_store:
            chat_store.rename_thread(current_thread_id, suggested_title)
        st.session_state.threads[current_thread_id]["title"] = suggested_title

    config = {"configurable": {"thread_id": current_thread_id}}
    input_state = {"messages": [HumanMessage(content=user_prompt)]}

    with chat_col:
        with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
            response_placeholder = st.empty()
            final_answer = ""
            generated_docx_path = None
            stream_completed = False

            try:
                for event in app.stream(input_state, config=config, stream_mode="updates"):
                    # Agent Node
                    if "agent" in event:
                        agent_output = event["agent"]
                        agent_msgs = agent_output.get("messages", [])
                        for am in agent_msgs:
                            if hasattr(am, "tool_calls") and am.tool_calls:
                                for tc in am.tool_calls:
                                    tool_name = tc.get("name", "Tool")
                                    tool_args = tc.get("args", {})

                                    st.session_state.active_tool_now = tool_name
                                    is_convert = "convert" in tool_name or "docx" in tool_name
                                    badge_label = "PDF Conversion" if is_convert else "Retrieval Action"

                                    with st.status(f"⚙️ Running `{tool_name}` ({badge_label})...", expanded=True) as status_box:
                                        st.write("**Parameters:**")
                                        st.json(tool_args)
                                        status_box.update(label=f"⏳ Executing `{tool_name}`...", state="running")

                                    st.session_state.threads[current_thread_id]["tool_history"].append({
                                        "name": tool_name,
                                        "args": tool_args,
                                        "timestamp": datetime.now().strftime("%H:%M"),
                                        "status": "invoked"
                                    })

                            if am.content:
                                final_answer = am.content
                                response_placeholder.markdown(final_answer)

                    # Tools Node
                    if "tools" in event:
                        tool_output = event["tools"]
                        tool_msgs = tool_output.get("messages", [])
                        for tm in tool_msgs:
                            tm_content = tm.content
                            if tm.name == "create_rks_document":
                                st.info("Hasil RKS akan ditampilkan pada panel Pratinjau halaman setelah proses selesai.")
                            if tm.name == "fetch_full_documents" and isinstance(tm_content, dict):
                                fetched_title = tm_content.get("title", "Untitled Document")
                                st.success(f"📄 **Document Fetched:** `{fetched_title}`")
                            elif tm.name == "fetch_relevant_documents" and isinstance(tm_content, list):
                                titles = list({item.get("title") for item in tm_content if isinstance(item, dict) and item.get("title")})
                                if titles:
                                    st.info(f"🔍 **Matched Documents:** {', '.join([f'`{t}`' for t in titles])}")
                            elif tm.name in ("convert_pdf_to_docx", "export_to_docx"):
                                st.success(f"✅ **PDF Converted to DOCX:** {str(tm_content)[:250]}")
                            else:
                                preview = str(tm_content)[:250] + ("..." if len(str(tm_content)) > 250 else "")
                                st.info(f"✅ **Tool `{tm.name}` completed:** {preview}")

                            f_cand = extract_docx_path(str(tm_content))
                            if f_cand:
                                generated_docx_path = f_cand
                                st.session_state["last_exported_docx"] = f_cand

                            history = st.session_state.threads[current_thread_id]["tool_history"]
                            if history:
                                history[-1]["result_preview"] = str(tm_content)[:250]
                                history[-1]["status"] = "completed"

                stream_completed = True
                st.session_state.active_tool_now = None

                if final_answer:
                    response_placeholder.markdown(final_answer)

                if generated_docx_path:
                    render_docx_download_card(generated_docx_path, key=f"stream_run_dl_{uuid.uuid4().hex[:6]}")

            except Exception as e:
                st.session_state.active_tool_now = None
                st.error(f"Error while executing agent: {str(e)}")
            finally:
                if stream_completed:
                    persist_thread_messages(current_thread_id)

    st.rerun()
