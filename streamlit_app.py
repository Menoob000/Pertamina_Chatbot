import os
import re
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from agent import app, tools

# ---------------------------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pertamina AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #6c757d;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    .thread-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: #e9ecef;
        color: #495057;
        margin-right: 0.4rem;
    }
    .active-badge {
        background-color: #d1e7dd;
        color: #0f5132;
    }
    .tool-chip {
        display: inline-flex;
        align-items: center;
        background: #f1f3f5;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 0.85rem;
        font-family: monospace;
        margin: 2px;
    }
    .tool-active {
        background: #cfe2ff;
        border-color: #9ec5fe;
        color: #084298;
    }
    .download-card {
        background-color: #f8f9fa;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 12px;
        margin-top: 8px;
        margin-bottom: 8px;
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
                "created_at": datetime.now().strftime("%H:%M:%S"),
                "tool_history": [],
            }
        }
        st.session_state.current_thread_id = initial_thread_id

    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]

    if "active_tool_now" not in st.session_state:
        st.session_state.active_tool_now = None

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
        "created_at": datetime.now().strftime("%H:%M:%S"),
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
    """Finds a .docx file path or filename in text."""
    if not text:
        return None
    # 1. Absolute Windows/Unix path
    match = re.search(r'([a-zA-Z]:[\\/][^:\*\?"<>\|\r\n]+\.docx)', text)
    if match:
        cand = match.group(1).strip()
        if os.path.exists(cand):
            return cand

    # 2. Filename under ./output/
    match_file = re.search(r'([a-zA-Z0-9_\-\.\s]+\.docx)', text)
    if match_file:
        cand_name = match_file.group(1).strip()
        local_cand = os.path.join("output", cand_name)
        if os.path.exists(local_cand):
            return os.path.abspath(local_cand)

    return None


def render_docx_download_button(file_path: str, key: str):
    """Renders a styled download button for a .docx file."""
    if file_path and os.path.exists(file_path):
        fname = os.path.basename(file_path)
        file_size_kb = os.path.getsize(file_path) / 1024
        with open(file_path, "rb") as f:
            data = f.read()
        
        st.download_button(
            label=f"📥 Download DOCX ({fname} - {file_size_kb:.1f} KB)",
            data=data,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=key,
            type="primary",
        )


# ---------------------------------------------------------------------------
# Sidebar: Active Threads & Agent Tools Monitor
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 💬 Active Threads")
    st.caption("Manage and switch between active conversation sessions.")

    col_btn, col_count = st.columns([2, 1])
    with col_btn:
        if st.button("➕ New Thread", key="btn_create_new_thread", use_container_width=True, type="primary"):
            create_new_thread()
            st.rerun()
    with col_count:
        st.markdown(
            f"<div style='text-align:center; padding:6px; background:#e9ecef; border-radius:6px; font-weight:600;'>{len(st.session_state.threads)} Active</div>",
            unsafe_allow_html=True,
        )

    st.write("")

    # List of threads
    thread_keys = list(st.session_state.threads.keys())
    for t_id in thread_keys:
        thread_info = st.session_state.threads[t_id]
        is_active = (t_id == current_thread_id)
        
        # Count how many messages in LangGraph state for this thread
        msgs = get_thread_messages(t_id)
        user_msgs_count = sum(1 for m in msgs if isinstance(m, HumanMessage))

        button_label = f"{'🟢' if is_active else '💬'} {thread_info['title']} ({user_msgs_count} msgs)"
        if st.button(
            button_label,
            key=f"thread_select_btn_{t_id}",
            use_container_width=True,
            type="secondary" if not is_active else "primary",
        ):
            st.session_state.current_thread_id = t_id
            st.rerun()

    st.divider()

    # Thread Details & Actions
    with st.expander("⚙️ Current Thread Settings", expanded=False):
        st.text(f"Thread ID: {current_thread_id}")
        st.text(f"Started at: {current_thread['created_at']}")
        new_title = st.text_input("Rename Thread", value=current_thread["title"], key="rename_title_input")
        if st.button("Save Name", key="btn_save_thread_name", use_container_width=True):
            if new_title.strip():
                st.session_state.threads[current_thread_id]["title"] = new_title.strip()
                st.rerun()

        if len(st.session_state.threads) > 1:
            if st.button("🗑️ Delete This Thread", key="btn_delete_current_thread", use_container_width=True, type="secondary"):
                del st.session_state.threads[current_thread_id]
                st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]
                st.rerun()

    st.divider()

    # -----------------------------------------------------------------------
    # Available Tools & Live Usage Monitor
    # -----------------------------------------------------------------------
    st.markdown("### 🛠️ Agent Tools Monitor")
    
    # Active tool status badge
    if st.session_state.active_tool_now:
        st.info(f"⚡ **Currently Running:** `{st.session_state.active_tool_now}`")
    else:
        st.success("🟢 **Agent Status:** Ready / Idle")

    st.markdown("**Available Tools in Agent:**")
    for t in tools:
        t_name = getattr(t, "name", str(t))
        t_desc = getattr(t, "description", "")
        is_tool_running = (st.session_state.active_tool_now == t_name)
        active_class = "tool-active" if is_tool_running else ""
        
        with st.container():
            st.markdown(
                f"<div class='tool-chip {active_class}'>🔧 <strong>{t_name}</strong></div>",
                unsafe_allow_html=True,
            )
            st.caption(t_desc.strip().split("\n")[0])

    # Exported Files in ./output/
    output_dir = Path("./output")
    if output_dir.exists():
        docx_files = sorted(list(output_dir.glob("*.docx")), key=os.path.getmtime, reverse=True)
        if docx_files:
            with st.expander(f"📁 Exported Documents ({len(docx_files)})", expanded=True):
                for f_idx, docx_file in enumerate(docx_files[:5]):
                    f_name = docx_file.name
                    f_size = docx_file.stat().st_size / 1024
                    st.markdown(f"**📄 {f_name}** `({f_size:.1f} KB)`")
                    with open(docx_file, "rb") as df:
                        st.download_button(
                            label=f"⬇️ Download",
                            data=df.read(),
                            file_name=f_name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"sidebar_dl_{f_idx}_{f_name}",
                            use_container_width=True,
                        )

    # Tool Execution History for this thread
    st.markdown("**Recent Tool Calls in this Thread:**")
    thread_tool_history = current_thread.get("tool_history", [])
    if not thread_tool_history:
        st.caption("No tools have been called yet in this session.")
    else:
        for idx, item in enumerate(reversed(thread_tool_history[-5:])):
            with st.expander(f"🔹 {item['name']} ({item['timestamp']})", expanded=False):
                st.write("**Arguments:**")
                st.json(item.get("args", {}))
                if "result_preview" in item:
                    st.write("**Result Preview:**")
                    st.code(item["result_preview"], language="text")


# ---------------------------------------------------------------------------
# Main Chat Area
# ---------------------------------------------------------------------------
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown(f"<div class='main-header'>🤖 Pertamina Knowledge Assistant</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='sub-header'>Thread: <strong>{current_thread['title']}</strong> "
        f"<span class='thread-badge active-badge'>ID: {current_thread_id}</span></div>",
        unsafe_allow_html=True,
    )
with col_status:
    if st.button("🔄 Refresh State", key="btn_refresh_main_state", use_container_width=True):
        st.rerun()

st.divider()

# Fetch historical messages for the current thread from LangGraph MemorySaver
thread_messages = get_thread_messages(current_thread_id)

# Render conversation history
i = 0
while i < len(thread_messages):
    msg = thread_messages[i]

    if isinstance(msg, SystemMessage):
        i += 1
        continue

    elif isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
        i += 1

    elif isinstance(msg, AIMessage):
        detected_file_path = None

        # Check if this AIMessage contains tool calls
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tc_name = tc.get("name", "Tool")
                tc_args = tc.get("args", {})
                tc_id = tc.get("id")

                # Look ahead for matching ToolMessage
                matching_tool_msg = None
                for candidate in thread_messages[i+1:]:
                    if isinstance(candidate, ToolMessage) and getattr(candidate, "tool_call_id", None) == tc_id:
                        matching_tool_msg = candidate
                        break

                with st.chat_message("assistant"):
                    with st.status(f"🛠️ Tool Used: `{tc_name}`", state="complete", expanded=False):
                        st.write("**Tool Inputs / Arguments:**")
                        st.json(tc_args)
                        if matching_tool_msg:
                            st.write("**Tool Output / Result:**")
                            st.text(str(matching_tool_msg.content)[:1000])

                if matching_tool_msg:
                    f_cand = extract_docx_path(str(matching_tool_msg.content))
                    if f_cand:
                        detected_file_path = f_cand

        # If the AIMessage has direct text content, render it
        if msg.content:
            with st.chat_message("assistant"):
                st.markdown(msg.content)
                # Check for docx mention in message text as well
                f_cand = extract_docx_path(msg.content)
                if f_cand:
                    detected_file_path = f_cand

        # Render download button if this turn produced a docx file
        if detected_file_path:
            with st.chat_message("assistant"):
                render_docx_download_button(detected_file_path, key=f"hist_msg_dl_{i}_{uuid.uuid4().hex[:4]}")

        i += 1

    elif isinstance(msg, ToolMessage):
        i += 1
    else:
        i += 1


# ---------------------------------------------------------------------------
# Chat Input & Streaming Execution
# ---------------------------------------------------------------------------
user_prompt = st.chat_input("Ask a question, generate an RKS, or export to DOCX...")

if user_prompt:
    # 1. Immediately render user's message in UI
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Auto-rename the thread if it's the first query and still has default name
    if current_thread["title"].startswith("Chat ") and len(thread_messages) == 0:
        suggested_title = user_prompt.strip()[:24] + ("..." if len(user_prompt.strip()) > 24 else "")
        st.session_state.threads[current_thread_id]["title"] = suggested_title

    # 2. Run LangGraph with the new HumanMessage
    config = {"configurable": {"thread_id": current_thread_id}}
    input_state = {"messages": [HumanMessage(content=user_prompt)]}

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        final_answer = ""
        generated_docx_path = None

        try:
            for event in app.stream(input_state, config=config, stream_mode="updates"):
                # Check for agent node updates
                if "agent" in event:
                    agent_output = event["agent"]
                    agent_msgs = agent_output.get("messages", [])
                    for am in agent_msgs:
                        if hasattr(am, "tool_calls") and am.tool_calls:
                            for tc in am.tool_calls:
                                tool_name = tc.get("name", "Tool")
                                tool_args = tc.get("args", {})
                                
                                st.session_state.active_tool_now = tool_name
                                
                                # Show real-time tool execution status widget
                                with st.status(f"🛠️ Agent calling tool: `{tool_name}`...", expanded=True) as status_box:
                                    st.write("**Arguments:**")
                                    st.json(tool_args)
                                    status_box.update(label=f"⏳ Running `{tool_name}`...", state="running")
                                
                                # Record into thread tool history
                                st.session_state.threads[current_thread_id]["tool_history"].append({
                                    "name": tool_name,
                                    "args": tool_args,
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                    "status": "invoked"
                                })

                        if am.content:
                            final_answer = am.content
                            response_placeholder.markdown(final_answer)

                # Check for tools node updates
                if "tools" in event:
                    tool_output = event["tools"]
                    tool_msgs = tool_output.get("messages", [])
                    for tm in tool_msgs:
                        tm_content = str(tm.content)
                        preview = tm_content[:300] + ("..." if len(tm_content) > 300 else "")
                        
                        st.info(f"✅ **Tool `{tm.name}` completed:** {preview}")

                        # Check if export_to_docx produced a file
                        f_cand = extract_docx_path(tm_content)
                        if f_cand:
                            generated_docx_path = f_cand

                        # Update last tool history entry with result preview
                        history = st.session_state.threads[current_thread_id]["tool_history"]
                        if history:
                            history[-1]["result_preview"] = preview
                            history[-1]["status"] = "completed"

            # Reset active tool when run finishes
            st.session_state.active_tool_now = None

            # Final response render
            if final_answer:
                response_placeholder.markdown(final_answer)

            # Show download button if docx was generated
            if generated_docx_path:
                render_docx_download_button(generated_docx_path, key=f"stream_run_dl_{uuid.uuid4().hex[:6]}")

        except Exception as e:
            st.session_state.active_tool_now = None
            st.error(f"Error while running agent: {str(e)}")

    # Rerun so session state, message count, tool history and UI stay 100% in sync
    st.rerun()
