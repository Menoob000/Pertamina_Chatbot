from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from typing import Any, Dict, List, Literal, Optional, Annotated
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langchain_core.documents import Document
import config
from dotenv import load_dotenv
import os
import re
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from rag.vector_store import fetch_full_document, fetch_relevant_documents
from langgraph.prebuilt import ToolNode, tools_condition, InjectedState
from tools.docx_exporter import parse_text_to_rks_data, render_to_docx
import psycopg

load_dotenv()

@tool 
def search_tool(query : str):
    """A tool to search the internet for relevant context to the user's query"""
    search = TavilySearch(max_results=3)
    response = search.invoke(query)
    return response

@tool 
def fetch_full_documents(query : str) -> Dict[str, Any]:
    """Fetch the full document matching the user query from the document repository. Returns the document content and its title."""
    response = fetch_full_document(query)
    return response

# Backward compatibility alias
return_full_docs = fetch_full_documents

@tool
def convert_pdf_to_docx(state: Annotated[dict, InjectedState], target_pdf_name: str = "", output_filename: str = "") -> str:
    """Converts a database/retrieved RKS document directly into a clean, professionally formatted Microsoft Word (.docx) file with official Pertamina cover page, approval sheet, table of contents, and chapters.
    Use this tool when the user asks to convert, export, or turn a retrieved document into a DOCX / Word file.
    Note: The document must already be fetched or viewed in the chat via fetch_full_documents.
    """
    doc_title = ""
    doc_content = ""

    # 1. Search conversation state for the last retrieved document
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) in ("fetch_full_documents", "return_full_docs"):
            raw_content = msg.content
            if isinstance(raw_content, str):
                try:
                    raw_content = json.loads(raw_content)
                except Exception:
                    try:
                        import ast
                        raw_content = ast.literal_eval(raw_content)
                    except Exception:
                        pass

            if isinstance(raw_content, dict):
                doc_title = raw_content.get("title") or raw_content.get("source_file", "")
                doc_content = raw_content.get("full_docs") or raw_content.get("full_content", "")
                if doc_content:
                    break
            elif isinstance(raw_content, str) and len(raw_content) > 100:
                doc_content = raw_content
                break

    # 2. If target_pdf_name is provided or doc_content is empty, query PostgreSQL
    if not doc_content and target_pdf_name:
        try:
            with psycopg.connect("dbname=langchain user=langchain password=langchain host=127.0.0.1 connect_timeout=5") as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT title, full_content FROM documents WHERE title ILIKE %s LIMIT 1;",
                        (f"%{target_pdf_name}%",)
                    )
                    row = cur.fetchone()
                    if row:
                        doc_title, doc_content = row[0], row[1]
        except Exception:
            pass

    # 3. If still no document found, return guidance requirement
    if not doc_content:
        return (
            "Dokumen belum diambil atau ditampilkan di percakapan. "
            "Silakan minta asisten untuk mengambil dokumen terlebih dahulu (misal: 'Ambilkan RKS...') "
            "sebelum melakukan konversi ke Word (.docx)."
        )

    # 4. Parse structured RKS data and render DOCX
    try:
        rks_data = parse_text_to_rks_data(doc_content, custom_title=doc_title)
        out_name = output_filename or ""
        output_path = render_to_docx(rks_data, output_filename=out_name)
        filename = os.path.basename(output_path)
        final_title = rks_data.get("cover_page", {}).get("judul_pekerjaan", doc_title)
        num_babs = len(rks_data.get("bab", []))

        return (
            f"Successfully converted document to DOCX format!\n"
            f"- Title: {final_title}\n"
            f"- Structured Chapters: {num_babs} BAB\n"
            f"- Converted Word Document: {filename}\n"
            f"- Path: {output_path}\n"
            f"The document includes official Pertamina cover page, lembar pengesahan, daftar isi, and structured chapters."
        )
    except Exception as e:
        return f"Failed to convert document to DOCX: {str(e)}"

# Alias so legacy prompts/calls for export_to_docx still trigger this tool
export_to_docx = convert_pdf_to_docx


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    full_docs : str


tools = [search_tool, fetch_full_documents, fetch_relevant_documents, convert_pdf_to_docx]

llm = ChatOpenRouter(model=config.LLM_MODEL_NAME, api_key=os.environ.get('OPENROUTER_API_KEY'))
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState) -> dict:
    """Invokes the LLM to decide whether to call a tool or respond directly."""
    system_prompt = SystemMessage(
        content=(
            "You are an intelligent knowledge base assistant for Pertamina.\n"
            "You have access to the following tools:\n"
            "1. 'fetch_full_documents': Always use this tool first when the user asks to generate a Document. Returns the document text and its title.\n"
            "2. 'search_tool': Use this when you need live internet information.\n"
            "3. 'fetch_relevant_documents': Use this tool when the user asks specific questions about documents. Returns relevant snippets with their document titles.\n"
            "4. 'convert_pdf_to_docx': Use this tool when the user asks to convert, export, or turn a PDF into Word / DOCX format. It directly converts the original PDF layout into an editable DOCX file.\n\n"
            "IMPORTANT CITATION & CONVERSION RULES:\n"
            "- Whenever you answer using information retrieved from 'fetch_full_documents' or 'fetch_relevant_documents', cite and display the document's Title (e.g. '📄 Dokumen: <title>').\n"
            "- When the user asks to convert the document to Word/DOCX, invoke 'convert_pdf_to_docx'."
        )
    )
    
    # Prepend system prompt to the conversation thread
    messages = [system_prompt] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# Create the automated ToolNode for running requested tools
tool_node = ToolNode(tools=tools)

# ---------------------------------------------------------------------------
# 4. Build & Compile LangGraph Workflow
# ---------------------------------------------------------------------------

builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("agent", agent_node)
builder.add_node("tools", tool_node)

# Set Graph Edges
builder.add_edge(START, "agent")

# Add Conditional Edge: Agent -> Tools OR End
builder.add_conditional_edges(
    "agent",
    tools_condition,
)

# Return back to agent after tool execution
builder.add_edge("tools", "agent")

# Checkpointer for conversation state memory across turns
memory = MemorySaver()
app = builder.compile(checkpointer=memory)

try:
    png = app.get_graph().draw_mermaid_png()
    with open('graph.png', 'wb') as p: 
        p.write(png)
except Exception:
    pass
