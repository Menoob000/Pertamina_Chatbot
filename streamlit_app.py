import os
import re
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from agent import app, tools
from tools.docx_exporter import parse_text_to_rks_data, render_to_docx

# ---------------------------------------------------------------------------
# Page Configuration & Professional Theming
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pertamina Knowledge Assistant",
    page_icon="assets/logo_pertamina.png" if os.path.exists("assets/logo_pertamina.png") else "🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Corporate CSS: White background, Pertamina Blue (#0072CE) & Pertamina Red (#ED1C24)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Clean white background and sleek framing */
    .stApp {
        background-color: #FFFFFF;
        color: #0F172A;
    }

    /* Hide standard Streamlit header chrome for a native web app feel */
    header[data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.95);
        border-bottom: 1px solid #F1F5F9;
    }
    footer {
        display: none !important;
    }

    /* Professional Sidebar */
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

    /* ChatGPT-style Message Layout */
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

    /* Tool Call Card Badges */
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

    /* Split-Screen Document Paper Viewer */
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
    }
    .doc-paper-body {
        max-height: 65vh;
        overflow-y: auto;
        padding-right: 0.5rem;
        font-size: 0.9rem;
        line-height: 1.6;
        color: #1E293B;
    }

    /* Empty state placeholder for document viewer */
    .doc-empty-state {
        text-align: center;
        padding: 4rem 1.5rem;
        color: #64748B;
        border: 2px dashed #E2E8F0;
        border-radius: 12px;
        background-color: #FAFAFA;
    }

    /* DOCX Download Card */
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

    /* Hero welcome */
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

    /* Primary buttons */
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

    /* Input box */
    div[data-testid="stChatInput"] {
        border-radius: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
def init_session_state():
    if "threads" not in st.session_state:
        initial_thread_id = f"thread_{str(uuid.uuid4())[:8]}"
        st.session_state.threads = {
            initial_thread_id: {
                "id": initial_thread_id,
                "title": "Chat 1",
                "created_at": datetime.now().strftime("%H:%M"),
                "tool_history": [],
            }
        }
        st.session_state.current_thread_id = initial_thread_id

    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]

    if "active_tool_now" not in st.session_state:
        st.session_state.active_tool_now = None

    if "prefilled_prompt" not in st.session_state:
        st.session_state.prefilled_prompt = None

    if "show_split_viewer" not in st.session_state:
        st.session_state.show_split_viewer = True

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
    new_id = f"thread_{str(uuid.uuid4())[:8]}"
    chat_idx = len(st.session_state.threads) + 1
    st.session_state.threads[new_id] = {
        "id": new_id,
        "title": f"Chat {chat_idx}",
        "created_at": datetime.now().strftime("%H:%M"),
        "tool_history": [],
    }
    st.session_state.current_thread_id = new_id
    st.session_state.active_tool_now = None


def get_thread_messages(thread_id: str):
    """Retrieves conversation messages stored in LangGraph's MemorySaver for this thread."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = app.get_state(config)
        if state and state.values:
            return state.values.get("messages", [])
    except Exception as e:
        st.error(f"Error fetching state for thread {thread_id}: {e}")
    return []


def extract_docx_path(text: str) -> Optional[str]:
    """Finds an existing .docx file path or filename in text."""
    if not text:
        return None
    match = re.search(r'([a-zA-Z]:[\\/][^:\*\?"<>\|\r\n]+\.docx)', text)
    if match:
        cand = match.group(1).strip()
        if os.path.exists(cand):
            return cand

    match_file = re.search(r'([a-zA-Z0-9_\-\.\s]+\.docx)', text)
    if match_file:
        cand_name = match_file.group(1).strip()
        local_cand = os.path.join("output", cand_name)
        if os.path.exists(local_cand):
            return os.path.abspath(local_cand)

    return None


def get_current_thread_document(thread_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the latest document fetched by fetch_full_documents or generated in this thread."""
    messages = get_thread_messages(thread_id)
    for msg in reversed(messages):
        # 1. Check ToolMessage from fetch_full_documents / return_full_docs
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) in ("fetch_full_documents", "return_full_docs", "fetch_full_document"):
            content = msg.content
            doc_str = ""
            if isinstance(content, dict) and "full_docs" in content:
                doc_str = content["full_docs"]
            elif isinstance(content, str):
                if "'full_docs':" in content or '"full_docs":' in content:
                    try:
                        import ast
                        parsed_dict = ast.literal_eval(content)
                        if isinstance(parsed_dict, dict) and "full_docs" in parsed_dict:
                            doc_str = parsed_dict["full_docs"]
                    except Exception:
                        pass
                if not doc_str:
                    doc_str = content
            if doc_str and len(doc_str.strip()) > 20:
                return {
                    "source": "fetch_full_documents",
                    "content": doc_str,
                }

        # 2. Check AIMessage containing substantial RKS structure
        if isinstance(msg, AIMessage) and msg.content and ("BAB 1" in msg.content or "RENCANA KERJA" in msg.content):
            if len(msg.content.strip()) > 100:
                return {
                    "source": "generated_rks",
                    "content": msg.content,
                }
    return None


def render_docx_download_card(file_path: str, key: str):
    """Renders a corporate Pertamina styled card with a download button for DOCX."""
    if file_path and os.path.exists(file_path):
        fname = os.path.basename(file_path)
        file_size_kb = os.path.getsize(file_path) / 1024
        with open(file_path, "rb") as f:
            data = f.read()

        st.markdown(
            f"""
            <div class="download-card">
                <div class="download-info">
                    <span class="download-title">📄 {fname}</span>
                    <span class="download-sub">Pertamina RKS DOCX • {file_size_kb:.1f} KB</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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


# Avatars
AVATAR_ASSISTANT = "assets/logo_pertamina.png" if os.path.exists("assets/logo_pertamina.png") else "🤖"
AVATAR_USER = "👤"


# ---------------------------------------------------------------------------
# Sidebar: ChatGPT-like History & Tools Monitor
# ---------------------------------------------------------------------------
with st.sidebar:
    if os.path.exists("assets/logo_pertamina.png"):
        st.image("assets/logo_pertamina.png", width=160)
    else:
        st.markdown("### 🏢 **PERTAMINA**")

    st.caption("AI Document & Knowledge Assistant")
    st.write("")

    # "+ New Chat" Button
    if st.button("➕ New Chat", key="btn_create_new_thread", use_container_width=True, type="primary"):
        create_new_thread()
        st.rerun()

    st.write("")
    st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;'>Recent Conversations</p>", unsafe_allow_html=True)

    thread_keys = list(st.session_state.threads.keys())
    for t_id in thread_keys:
        thread_info = st.session_state.threads[t_id]
        is_active = (t_id == current_thread_id)

        button_label = f"{'🔹 ' if is_active else '💬 '}{thread_info['title']}"
        if st.button(
            button_label,
            key=f"thread_select_btn_{t_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.current_thread_id = t_id
            st.rerun()

    st.write("")
    st.divider()

    # Active Thread Settings
    with st.expander("⚙️ Current Session Settings", expanded=False):
        st.text(f"Thread: {current_thread_id}")
        new_title = st.text_input("Rename Session", value=current_thread["title"], key="rename_title_input")
        if st.button("Save Name", key="btn_save_thread_name", use_container_width=True):
            if new_title.strip():
                st.session_state.threads[current_thread_id]["title"] = new_title.strip()
                st.rerun()

        if len(st.session_state.threads) > 1:
            if st.button("🗑️ Delete Session", key="btn_delete_current_thread", use_container_width=True):
                del st.session_state.threads[current_thread_id]
                st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]
                st.rerun()

    # Agent Tools Section
    st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;'>Agent Capabilities</p>", unsafe_allow_html=True)

    if st.session_state.active_tool_now:
        st.markdown(
            f"<div style='padding:6px 10px; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; font-size:0.8rem; color:#0072CE; font-weight:600; margin-bottom:8px;'>"
            f"⚡ Running: <code>{st.session_state.active_tool_now}</code></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='padding:6px 10px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; font-size:0.8rem; color:#475569; font-weight:600; margin-bottom:8px;'>"
            "🟢 Agent Status: Ready</div>",
            unsafe_allow_html=True,
        )

    with st.expander("🔧 Available Agent Tools", expanded=False):
        for t in tools:
            t_name = getattr(t, "name", str(t))
            t_desc = getattr(t, "description", "")
            is_export = "docx" in t_name
            badge_class = "tool-badge-red" if is_export else "tool-badge-blue"
            st.markdown(
                f"<div style='margin-bottom:6px;'>"
                f"<span class='{badge_class}'>● {t_name}</span><br>"
                f"<span style='font-size:0.75rem; color:#64748B;'>{t_desc.strip().splitlines()[0][:70]}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Exported Documents in ./output/
    output_dir = Path("./output")
    if output_dir.exists():
        docx_files = sorted(list(output_dir.glob("*.docx")), key=os.path.getmtime, reverse=True)
        if docx_files:
            with st.expander(f"📁 Exported Documents ({len(docx_files)})", expanded=True):
                for f_idx, docx_file in enumerate(docx_files[:4]):
                    f_name = docx_file.name
                    f_size = docx_file.stat().st_size / 1024
                    st.markdown(f"<span style='font-size:0.82rem; font-weight:600;'>📄 {f_name[:24]}...</span> <span style='font-size:0.75rem; color:#64748B;'>({f_size:.1f} KB)</span>", unsafe_allow_html=True)
                    with open(docx_file, "rb") as df:
                        st.download_button(
                            label="⬇️ Download",
                            data=df.read(),
                            file_name=f_name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"sidebar_dl_{f_idx}_{f_name}",
                            use_container_width=True,
                        )


# ---------------------------------------------------------------------------
# Main Header & Split-Screen View Controls
# ---------------------------------------------------------------------------
top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.markdown(
        f"""
        <div class="brand-title">
            <span class="brand-accent-blue">Pertamina</span> <span class="brand-accent-red">Knowledge</span> Assistant
            <span class="thread-pill">💬 {current_thread['title']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_col2:
    split_label = "📖 Hide Viewer" if st.session_state.show_split_viewer else "📖 Split Viewer"
    if st.button(split_label, key="toggle_split_viewer", use_container_width=True):
        st.session_state.show_split_viewer = not st.session_state.show_split_viewer
        st.rerun()

st.write("")

# Fetch historical messages for the current thread from LangGraph MemorySaver
thread_messages = get_thread_messages(current_thread_id)
current_doc_data = get_current_thread_document(current_thread_id)

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
        st.markdown(
            """
            <div class="hero-container">
                <div style="display:inline-block; padding:8px 12px; border-radius:50%; background:#F1F5F9; margin-bottom:8px;">
                    <span style="font-size:1.8rem;">⚡</span>
                </div>
                <div class="hero-title">Pertamina Document Assistant</div>
                <div class="hero-sub">
                    Retrieve official RKS document templates, inspect them live in the split viewer, and export formatted DOCX files.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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
            if st.button("📥 **Export DOCX**\n\nExport RKS terakhir ke DOCX", key="starter_docx", use_container_width=True):
                st.session_state.prefilled_prompt = "Export dokumen RKS terakhir ke format docx"
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

                    is_export = "docx" in tc_name
                    badge_type = "tool-badge-red" if is_export else "tool-badge-blue"

                    with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
                        with st.status(f"⚙️ Tool: {tc_name}", state="complete", expanded=False):
                            st.markdown(f"<span class='{badge_type}'>Invoked: {tc_name}</span>", unsafe_allow_html=True)
                            st.write("**Inputs:**")
                            st.json(tc_args)
                            if matching_tool_msg:
                                st.write("**Output Result:**")
                                st.text(str(matching_tool_msg.content)[:800])

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
        st.markdown(
            """
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                <span style="font-weight:700; font-size:1.1rem; color:#0F172A;">📄 Document Viewer</span>
                <span style="font-size:0.75rem; color:#64748B; font-weight:600;">LIVE PREVIEW</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not current_doc_data:
            st.markdown(
                """
                <div class="doc-empty-state">
                    <span style="font-size:2.4rem;">📑</span>
                    <h4 style="margin-top:10px; margin-bottom:6px; color:#334155;">No Document Loaded</h4>
                    <p style="font-size:0.85rem; max-width:340px; margin:0 auto; line-height:1.4;">
                        Ask the assistant to fetch an RKS (e.g. <em>"Ambilkan RKS overhaul tangki"</em>) to inspect its full content here in real time.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            doc_raw = current_doc_data["content"]
            parsed_rks = parse_text_to_rks_data(doc_raw)
            doc_title = parsed_rks.get("cover_page", {}).get("judul_pekerjaan", "DOKUMEN RKS")
            doc_csms = parsed_rks.get("cover_page", {}).get("resiko_csms", "HIGH")
            doc_no = parsed_rks.get("metadata", {}).get("nomor_dokumen", "RKS/PERTAMINA/2026")
            babs = parsed_rks.get("bab", [])

            # Paper Card Container
            st.markdown(
                f"""
                <div class="doc-viewer-container">
                    <div class="doc-top-stripe"></div>
                    <div class="doc-paper-header">
                        <div class="doc-paper-title">{doc_title}</div>
                        <div>
                            <span class="doc-metadata-pill">No: {doc_no}</span>
                            <span class="doc-metadata-csms">CSMS: {doc_csms}</span>
                            <span class="doc-metadata-pill">{len(babs)} Bab</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Document Viewer Tabs
            tab_preview, tab_outline, tab_export = st.tabs(["📖 Document Text", "📑 Chapter Outline", "⚡ Quick Actions"])

            with tab_preview:
                st.markdown(
                    f"""
                    <div class="doc-paper-body">
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(doc_raw)
                st.markdown("</div>", unsafe_allow_html=True)

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

            with tab_export:
                st.markdown("#### Document Export Options")
                st.caption("Directly export this loaded RKS document to standard Pertamina DOCX format.")

                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    if st.button("📤 Export Document Now", key="btn_quick_export_doc", type="primary", use_container_width=True):
                        try:
                            saved_file = render_to_docx(parsed_rks)
                            st.session_state.last_quick_export = saved_file
                            st.success(f"Generated: {os.path.basename(saved_file)}")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Failed to export: {ex}")

                with col_exp2:
                    if "last_quick_export" in st.session_state and os.path.exists(st.session_state.last_quick_export):
                        render_docx_download_card(st.session_state.last_quick_export, key="viewer_quick_dl_btn")


# ---------------------------------------------------------------------------
# Chat Input & Streaming Execution
# ---------------------------------------------------------------------------
initial_input = st.session_state.prefilled_prompt
if initial_input:
    user_prompt = initial_input
    st.session_state.prefilled_prompt = None
else:
    user_prompt = st.chat_input("Ask a question, fetch an RKS, or export to DOCX...")

if user_prompt:
    with chat_col:
        with st.chat_message("user", avatar=AVATAR_USER):
            st.markdown(user_prompt)

    # Auto-rename thread on first query
    if current_thread["title"].startswith("Chat ") and len(thread_messages) == 0:
        suggested_title = user_prompt.strip()[:24] + ("..." if len(user_prompt.strip()) > 24 else "")
        st.session_state.threads[current_thread_id]["title"] = suggested_title

    # Run LangGraph Workflow
    config = {"configurable": {"thread_id": current_thread_id}}
    input_state = {"messages": [HumanMessage(content=user_prompt)]}

    with chat_col:
        with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
            response_placeholder = st.empty()
            final_answer = ""
            generated_docx_path = None

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
                                    is_export = "docx" in tool_name
                                    badge_label = "Export Action" if is_export else "Retrieval Action"

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
                            tm_content = str(tm.content)
                            preview = tm_content[:250] + ("..." if len(tm_content) > 250 else "")

                            st.info(f"✅ **Tool `{tm.name}` completed:** {preview}")

                            f_cand = extract_docx_path(tm_content)
                            if f_cand:
                                generated_docx_path = f_cand

                            history = st.session_state.threads[current_thread_id]["tool_history"]
                            if history:
                                history[-1]["result_preview"] = preview
                                history[-1]["status"] = "completed"

                st.session_state.active_tool_now = None

                if final_answer:
                    response_placeholder.markdown(final_answer)

                if generated_docx_path:
                    render_docx_download_card(generated_docx_path, key=f"stream_run_dl_{uuid.uuid4().hex[:6]}")

            except Exception as e:
                st.session_state.active_tool_now = None
                st.error(f"Error while executing agent: {str(e)}")

    st.rerun()
