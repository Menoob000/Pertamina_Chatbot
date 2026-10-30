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
from tools.pdf_converter import find_matching_pdf, convert_pdf_to_docx_layout, get_pdf_metadata

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
    """Converts a database/retrieved PDF document directly into an editable Microsoft Word (.docx) file preserving the visual layout.
    Use this tool when the user asks to convert, export, or turn a PDF into a DOCX / Word file.
    The tool automatically locates the matching PDF in the database/repository.
    """
    matched_pdf = None

    # 1. If user or agent explicitly supplied a target pdf name or query
    if target_pdf_name:
        matched_pdf = find_matching_pdf(target_pdf_name)

    # 2. If not found or empty, search conversation state for the last retrieved document title/file
    if not matched_pdf:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage) and getattr(msg, "name", None) in ("fetch_full_documents", "return_full_docs", "fetch_relevant_documents"):
                content = msg.content
                cand_title = ""
                if isinstance(content, dict):
                    cand_title = content.get("title") or content.get("source_file", "")
                elif isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                    cand_title = content[0].get("title", "")
                elif isinstance(content, str):
                    match = re.search(r"([A-Za-z0-9_\-\.\+]+\.pdf)", content)
                    if match:
                        cand_title = match.group(1)
                
                if cand_title:
                    matched_pdf = find_matching_pdf(cand_title)
                    if matched_pdf:
                        break

    if not matched_pdf:
        return (
            "Error: Could not locate the target PDF file to convert in the repository. "
            "Please ensure the document has been fetched first using 'fetch_full_documents' or provide the exact PDF filename."
        )

    # 3. Perform direct layout conversion
    try:
        output_path = convert_pdf_to_docx_layout(matched_pdf, output_filename=output_filename)
        meta = get_pdf_metadata(matched_pdf)
        filename = os.path.basename(output_path)
        return (
            f"Successfully converted PDF to DOCX with direct layout preservation!\n"
            f"- Source PDF: {meta.get('file_name')} ({meta.get('page_count')} pages)\n"
            f"- Converted Word Document: {filename}\n"
            f"- Path: {output_path}\n"
            f"The converted DOCX is now ready for download."
        )
    except Exception as e:
        return f"Failed to convert PDF to DOCX: {str(e)}"

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
