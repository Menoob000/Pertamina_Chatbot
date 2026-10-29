from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
import config
from langchain_core.tools import tool
import psycopg
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
import os

load_dotenv()

embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=os.getenv('OPENROUTER_API_KEY'),
            openai_api_base="https://openrouter.ai/api/v1",
            tiktoken_enabled=False,
            )
connection = "postgresql+psycopg://langchain:langchain@localhost:5432/langchain"  # Uses psycopg3!
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="knowledge_base",
    connection=connection,
)

def fetch_full_document(user_query: str) -> Dict[str, Any]:
    """Finds and returns the full document content matching the user query along with its title and metadata.
    If no match is found, defaults to fetching the first 'RKS' document.
    """
    # 1. Search for user query
    results = vector_store.similarity_search(user_query, k=1)
    
    # 2. Fallback to 'RKS' search if initial search returns empty
    if not results:
        results = vector_store.similarity_search("RKS", k=1)
        if not results:
            return {
                "title": "Document Not Found",
                "full_docs": "No matching document or fallback RKS template found.",
                "error": True
            }

    # 3. Safely extract metadata
    doc_id: Optional[str] = results[0].metadata.get("document_id")
    file_name: str = results[0].metadata.get("file_name", "Untitled Document")

    if not doc_id:
        return {
            "title": file_name,
            "full_docs": "Metadata error: Document ID is missing from the vector search result.",
            "error": True
        }

    # 4. Fetch title & full text from SQL database
    connection_string = "dbname=langchain user=langchain password=langchain host=localhost"
    
    try:
        with psycopg.connect(connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT title, full_content FROM documents WHERE id = %s", (doc_id,))
                row = cursor.fetchone()
                
                if row and row[1]:
                    doc_title = row[0] or file_name
                    return {
                        "title": doc_title,
                        "full_docs": row[1],
                        "document_id": doc_id,
                        "source_file": file_name
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
def fetch_relevant_documents(query : str) -> List[Dict[str, Any]]:
    """Retrieve the most relevant document chunks based on the query, including document title and relevance score."""
    results = vector_store.similarity_search_with_relevance_scores(query, k=3)
    formatted_chunks = []
    for doc, score in results:
        formatted_chunks.append({
            "title": doc.metadata.get("file_name", "Unknown Document"),
            "content": doc.page_content,
            "relevance_score": round(float(score), 3)
        })
    print(f"[Retrieve KB] Found {len(formatted_chunks)} docs for query: '{query}'")
    return formatted_chunks
