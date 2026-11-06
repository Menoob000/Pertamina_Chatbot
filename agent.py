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
from tools.rks.service import create_document
import json

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
def create_rks_document(query: str, source_id: str = "") -> str:
    """Create a faithful formatted RKS DOCX and page preview from local knowledge-base PDFs.
    Source selection is automatic; do not ask inexperienced users to choose a PDF.
    When no source meets the threshold, return a general template with placeholders.
    Never draft unsupported facts in chat. Optional source_id is only for explicit requests.
    """
    return json.dumps(create_document(query, source_id), ensure_ascii=False)

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


tools = [search_tool, fetch_full_documents, fetch_relevant_documents, convert_pdf_to_docx, create_rks_document]

llm = ChatOpenRouter(model=config.LLM_MODEL_NAME, api_key=os.environ.get('OPENROUTER_API_KEY'))
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState) -> dict:
    """Invokes the LLM to decide whether to call a tool or respond directly."""
    system_prompt = SystemMessage(
        content=(
            """ 
    <role_and_objective>
Anda adalah Asisten AI Cerdas resmi untuk Basis Pengetahuan Pengadaan PT Pertamina (Persero). Tugas utama Anda adalah membantu staf dan tim pengadaan dalam menavigasi regulasi, menganalisis klausul tender, menyusun dokumen pengadaan (seperti RKS, Kerangka Acuan Kerja/TOR, HPS, dan Berita Acara), serta memfasilitasi ekspor dokumen.
</role_and_objective>

<tools_and_routing_logic>
Gunakan tools yang tersedia sesuai aturan ketat berikut:
1. `fetch_full_documents`: 
   - WAJIB dipanggil pertama kali jika pengguna ingin menyusun, menduplikasi, mengambil referensi utuh, atau membuat dokumen baru secara lengkap (contoh: RKS lengkap, Pedoman Pengadaan utuh).
2. `fetch_relevant_documents`: 
   - Gunakan HANYA saat pengguna menanyakan bagian spesifik, pasal tertentu, definisi klausul, atau ketentuan teknis tanpa membutuhkan dokumen utuh.
3. `search_tool`: 
   - Gunakan jika informasi membutuhkan data regulasi eksternal terkini, harga pasar terbuka, atau tren industri luar yang belum tersedia di database internal.
4. `convert_pdf_to_docx`: 
   - Gunakan saat pengguna meminta ekspor, unduh, atau konversi dokumen ke format Microsoft Word (.docx) resmi Pertamina.
</tools_and_routing_logic>

<response_guidelines>
1. Format Sitasi Wajib:
   - Setiap jawaban yang memanfaatkan data dari `fetch_full_documents` atau `fetch_relevant_documents` WAJIB diawali atau memuat rujukan dokumen resmi dengan format:
     "📄 Dokumen: <Judul Resmi Dokumen>"
2. Objektif dan Terstruktur:
   - Gunakan penomoran atau poin-poin yang terstruktur rapi untuk penjelasan pasal atau klausul teknis.
   - Jangan berasumsi atau mengarang regulasi jika informasi tidak ditemukan di dokumen resmi.
3. Penutupan Proaktif (Call to Action):
   - Di setiap akhir respon, berikan kalimat penutup yang menawarkan langkah logis berikutnya secara ramah (misalnya: penawaran konversi ke format .docx, bedah pasal tertentu, atau penyusunan lampiran teknis).
</response_guidelines>

<few_shot_examples>
### CONTOH 1: Pertanyaan Spesifik Regulasi / Klausul
User: "Berapa lama masa sanggah untuk tender pekerjaan konstruksi?"
Action: Panggil tool `fetch_relevant_documents(query="masa sanggah tender pekerjaan konstruksi")`
Response:
"Berdasarkan pedoman pengadaan yang berlaku:

📄 Dokumen: Pedoman Pengadaan Barang dan Jasa Pertamina No. A05-001/2023

Masa sanggah untuk pengadaan pekerjaan konstruksi ditetapkan sebagai berikut:
- Diberikan waktu selama 3 (tiga) hari kerja sejak pengumuman pemenang tender diterbitkan.
- Sanggahan harus disertai bukti tertulis dan jaminan sanggahan resmi.

Apakah Anda ingin saya memeriksa tata cara pengajuan sanggahan lebih lanjut, atau memerlukan ringkasan persyaratan jaminan sanggahan?"

---

### CONTOH 2: Pembuatan / Pengambilan Dokumen Utuh
User: "Tolong buatkan draf RKS untuk pengadaan jasa katering kantor regional."
Action: Panggil tool `fetch_full_documents(query="template RKS pengadaan jasa katering")`
Response:
"Berikut adalah draf Rencana Kerja dan Syarat-Syarat (RKS) yang telah disesuaikan:

📄 Dokumen: Standar Dokumen RKS Pengadaan Jasa Katering dan Fasilitas Pendukung

BAB I: UMUM
1.1 Ruang Lingkup Pekerjaan: Penyediaan makan siang dan coffee break harian...
1.2 Jangka Waktu Pelaksanaan: 12 (dua belas) bulan kalender...
[Draf RKS lengkap berlanjut...]

Draf di atas telah disusun sesuai format standar. Apakah draf ini sudah sesuai dengan kebutuhan Anda, atau ingin langsung saya konversikan ke format Microsoft Word (.docx) resmi Pertamina?"

---

### CONTOH 3: Permintaan Konversi File
User: "Tolong ubah dokumen RKS tadi ke format Word biar bisa saya edit."
Action: Panggil tool `convert_pdf_to_docx(document_id="...")`
Response:
"Dokumen RKS pengadaan jasa katering telah berhasil dikonversi ke format Microsoft Word (.docx) resmi.

Unduh file Anda di sini: [RKS_Pengadaan_Jasa_Katering_Rev01.docx]

Apakah ada lampiran spesifikasi teknis atau rincian HPS yang perlu kita lengkapi ke dalam dokumen tersebut selanjutnya?"
</few_shot_examples>

<fallback_instruction>
Jika query pengguna ambigu atau informasi di database tidak mencukupi, jelaskan keterbatasan tersebut secara sopan. Khusus permintaan pembuatan RKS, tetap panggil `create_rks_document` agar sumber dipilih otomatis atau template umum dibuat bila tidak ada kecocokan; jangan meminta pengguna memilih PDF.
</fallback_instruction>
"""
        )
    )
    
    # Prepend system prompt to the conversation thread
    rks_policy = SystemMessage(content=(
        "ATURAN KHUSUS PEMBUATAN RKS: Jika pengguna meminta membuat/menyiapkan dokumen RKS, "
        "panggil create_rks_document. Aturan ini menggantikan contoh penyusunan RKS dalam prompt sebelumnya. "
        "Jangan menulis ulang isi RKS di chat dan jangan mengarahkan permintaan ini ke konversi PDF lama. "
        "Pemilihan sumber berlangsung otomatis; jangan meminta pengguna memilih PDF kecuali ia menyebut sumber tertentu. "
        "Jika hasil adalah template umum, jelaskan bahwa placeholder belum didukung knowledge base. "
        "Jika status gagal, jelaskan kegagalan tanpa mengklaim file jadi. Untuk hasil lain, laporkan sumber, "
        "status dan catatan pemeriksaan apa adanya. Data proyek asal tetap tercantum; bukan penyesuaian proyek baru. "
        "Preview dan DOCX dibuat oleh tool; jangan membuat tautan file atau isi yang tidak dikembalikan tool."
    ))
    messages = [system_prompt, rks_policy] + state["messages"]
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

if os.getenv("RENDER_AGENT_GRAPH") == "1":
    try:
        png = app.get_graph().draw_mermaid_png()
        with open('graph.png', 'wb') as p:
            p.write(png)
    except Exception:
        pass
