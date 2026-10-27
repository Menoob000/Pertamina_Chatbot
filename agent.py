from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
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
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from rag.vector_store import fetch_full_document, fetch_relevant_documents
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
load_dotenv()

@tool 
def search_tool(query : str):
    """A tool to search the internet for relevant context to the user's query"""
    search = TavilySearch(max_results=3)
    response = search.invoke(query)
    return response

@tool 
def return_full_docs(query : str):
    """Return the full documents most similar to the user's query. Use this tool when the user asked you to make a document"""
    response = fetch_full_document(query)
    return {'full_docs' : response}


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    full_docs : str


tools = [search_tool, return_full_docs, fetch_relevant_documents]


llm = ChatOpenRouter(model=config.LLM_MODEL_NAME, api_key=os.environ.get('OPENROUTER_API_KEY'))
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState) -> dict:
    """Invokes the LLM to decide whether to call a tool or respond directly."""
    system_prompt = SystemMessage(
        content=(
            "You are an intelligent knowledge base assistant. You have access to tools:\n"
            "1. 'fetch_full_document': Use this when the user asks you to generate a document. Just return the full document fetched. \n"
            "2. 'search_tool': Use this when you need live internet information.\n"
            "3. 'fetch_relevant_documents' : Use this tool when the user ask information in the documents "
            "If a tool returns document content, use that content to accurately fulfill the user's request."
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


png = app.get_graph().draw_mermaid_png()

with open('graph.png', 'wb') as p: 
    p.write(png)

