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
from tools.docx_exporter import render_to_docx, parse_text_to_rks_data

load_dotenv()

@tool 
def search_tool(query : str):
    """A tool to search the internet for relevant context to the user's query"""
    search = TavilySearch(max_results=3)
    response = search.invoke(query)
    return response

@tool 
def fetch_full_documents(query : str):
    """Fetch the full document matching the user query from the document repository. Use this tool when the user asks for a full document."""
    response = fetch_full_document(query)
    return {'full_docs' : response}

# Backward compatibility alias
return_full_docs = fetch_full_documents

@tool
def export_to_docx(state: Annotated[dict, InjectedState], output_filename: str = "", title: str = "") -> str:
    """Exports the last document fetched by 'fetch_full_documents' into a formatted Word (.docx) document.
    Use this tool when the user asks to export, download, or save the document as Word / DOCX / docs format.
    The tool automatically retrieves the last document fetched by 'fetch_full_documents' from the conversation history.
    """
    doc_content = ""

    # 1. Inspect previous messages specifically for the last document fetched by fetch_full_documents / return_full_docs
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) in ("fetch_full_documents", "return_full_docs", "fetch_full_document"):
            content = msg.content
            if isinstance(content, dict) and "full_docs" in content:
                doc_content = content["full_docs"]
                break
            elif isinstance(content, str) and content:
                # If content is a stringified dict representation, try to extract 'full_docs'
                if "'full_docs':" in content or '"full_docs":' in content:
                    try:
                        import ast
                        parsed_dict = ast.literal_eval(content)
                        if isinstance(parsed_dict, dict) and "full_docs" in parsed_dict:
                            doc_content = parsed_dict["full_docs"]
                            break
                    except Exception:
                        pass
                doc_content = content
                break

    # 2. Check if state has full_docs as fallback
    if not doc_content and state.get("full_docs"):
        doc_content = state["full_docs"]

    if not doc_content:
        return (
            "Error: No document has been fetched yet using 'fetch_full_documents'. "
            "Please fetch the document first using 'fetch_full_documents' before calling this tool."
        )

    # 3. Parse the fetched document into RKS structure and render
    rks_data = parse_text_to_rks_data(doc_content, custom_title=title)

    try:
        saved_path = render_to_docx(draft_data=rks_data, output_filename=output_filename)
        filename = os.path.basename(saved_path)
        return (
            f"Document successfully exported to DOCX format!\n"
            f"- File: {filename}\n"
            f"- Path: {saved_path}\n"
            f"The document is ready for download."
        )
    except Exception as e:
        return f"Failed to export document to DOCX: {str(e)}"


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    full_docs : str


tools = [search_tool, fetch_full_documents, fetch_relevant_documents, export_to_docx]

llm = ChatOpenRouter(model=config.LLM_MODEL_NAME, api_key=os.environ.get('OPENROUTER_API_KEY'))
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState) -> dict:
    """Invokes the LLM to decide whether to call a tool or respond directly."""
    system_prompt = SystemMessage(
        content=(
            "You are an intelligent knowledge base assistant for Pertamina.\n"
            "You have access to the following tools:\n"
            "1. 'fetch_full_documents': Use this when the user asks for a document or RKS. Always fetch the document using this tool.\n"
            "2. 'search_tool': Use this when you need live internet information.\n"
            "3. 'fetch_relevant_documents': Use this tool when the user asks specific questions about documents.\n"
            "4. 'export_to_docx': Use this tool when the user asks to export, download, or convert the document to Word / DOCX / docs format. It renders the last document fetched by 'fetch_full_documents'.\n"
            "If the user asks to fetch and export a document in a single request, call 'fetch_full_documents' first, then call 'export_to_docx'."
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
