from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
import config
from langchain_core.tools import tool
import psycopg
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
import os

load_dotenv()

PGVECTOR_HOST = os.getenv("PGVECTOR_HOST", "127.0.0.1")
PGVECTOR_PORT = int(os.getenv("PGVECTOR_PORT", "5432"))
PGVECTOR_USER = os.getenv("PGVECTOR_USER", "langchain")
PGVECTOR_PASSWORD = os.getenv("PGVECTOR_PASSWORD", "langchain")
PGVECTOR_DB = os.getenv("PGVECTOR_DB", "langchain")
connection = (
    f"postgresql+psycopg://{PGVECTOR_USER}:{PGVECTOR_PASSWORD}"
    f"@{PGVECTOR_HOST}:{PGVECTOR_PORT}/{PGVECTOR_DB}"
)

_vector_store = None


def _get_vector_store():
    """Connect to PostgreSQL only when a retrieval tool is actually used."""
    global _vector_store
    if _vector_store is None:
        embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL,
                                          model_kwargs={"local_files_only": True})
        _vector_store = PGVector(
            embeddings=embeddings,
            collection_name="knowledge_base",
            connection=connection,
        )
    return _vector_store

def fetch_full_document(user_query: str) -> Dict[str, Any]:
    """Finds and returns the full document content matching the user query along with its title and metadata.
    Never substitutes an unrelated RKS when the query has no match.
    """
    try:
        results = _get_vector_store().similarity_search_with_relevance_scores(user_query, k=1)
    except Exception:
        return {"title": "Sumber tidak ditemukan", "full_docs": "Layanan pencarian tidak tersedia.", "error": True}
    if not results or results[0][1] < config.RKS_SEARCH_SCORE_THRESHOLD:
        return {"title": "Sumber tidak ditemukan", "full_docs": "Tidak ada dokumen yang memenuhi ambang kecocokan.", "error": True}

    # 3. Safely extract metadata
    doc_id: Optional[str] = results[0][0].metadata.get("document_id")
    file_name: str = results[0][0].metadata.get("file_name", "Untitled Document")

    if not doc_id:
        return {
            "title": file_name,
            "full_docs": "Metadata error: Document ID is missing from the vector search result.",
            "error": True
        }

    # 4. Fetch title & full text from SQL database
    try:
        with psycopg.connect(
            host=PGVECTOR_HOST,
            port=PGVECTOR_PORT,
            dbname=PGVECTOR_DB,
            user=PGVECTOR_USER,
            password=PGVECTOR_PASSWORD,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT title, full_content FROM documents WHERE id = %s", (doc_id,))
                row = cursor.fetchone()
                
                if row and row[1]:
                    doc_title = row[0] or file_name
                    return {
                        "title": doc_title,
                        "full_docs": row[1],
                        "document_id": doc_id,
                        "source_file": file_name,
                        "matched_page": results[0][0].metadata.get("page"),
                        "relevance_score": round(float(results[0][1]), 3),
                    }
                return {
                    "title": file_name,
                    "full_docs": f"Document ID '{doc_id}' exists in vector metadata but was not found in SQL database.",
                    "error": True
                }
    except Exception as e:
        return {
            "title": file_name,
            "full_docs": f"Database query failed: {str(e)}",
            "error": True
        }

@tool
def fetch_relevant_documents(query: str, top_k: int = 3,
                             score_threshold: float = -1.0,
                             document_type: str = "") -> List[Dict[str, Any]]:
    """Retrieve the most relevant document chunks based on the query, including document title and relevance score."""
    threshold = config.RKS_SEARCH_SCORE_THRESHOLD if score_threshold < 0 else score_threshold
    if not 0 <= threshold <= 1:
        raise ValueError("score_threshold harus di antara 0 dan 1")
    filters = {"document_type": document_type} if document_type else None
    try:
        results = _get_vector_store().similarity_search_with_relevance_scores(query, k=max(1, top_k), filter=filters)
    except Exception:
        return []
    formatted_chunks = []
    for doc, score in results:
        if score < threshold:
            continue
        formatted_chunks.append({
            "title": doc.metadata.get("file_name", "Unknown Document"),
            "source_id": doc.metadata.get("document_id"),
            "page": doc.metadata.get("page"),
            "version": doc.metadata.get("version"),
            "year": doc.metadata.get("year"),
            "content": doc.page_content,
            "relevance_score": round(float(score), 3)
        })
    print(f"[Retrieve KB] Found {len(formatted_chunks)} docs for query: '{query}'")
    return formatted_chunks
