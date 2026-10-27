from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
import config
from langchain_core.tools import tool
import psycopg
from dotenv import load_dotenv
from typing import Optional
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

# @tool
def fetch_full_document(user_query: str) -> str:
    """Finds and returns the full document content matching the user query.
    If no match is found, defaults to fetching the first 'RKS' document.
    """
    # 1. Search for user query
    results = vector_store.similarity_search(user_query, k=1)
    
    # 2. Fallback to 'RKS' search if initial search returns empty
    if not results:
        results = vector_store.similarity_search("RKS", k=1)
        if not results:
            return "No matching document or fallback RKS template found."

    # 3. Safely extract document_id
    doc_id: Optional[str] = results[0].metadata.get("document_id")
    if not doc_id:
        return "Metadata error: Document ID is missing from the vector search result."

    # 4. Fetch full text using a context manager for automatic connection closure
    connection_string = "dbname=langchain user=langchain password=langchain host=localhost"
    
    try:
        with psycopg.connect(connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT full_content FROM documents WHERE id = %s", (doc_id,))
                row = cursor.fetchone()
                
                if row and row[0]:
                    return row[0]
                return f"Document ID '{doc_id}' exists in vector metadata but was not found in SQL database."
    except Exception as e:
        return f"Database query failed: {str(e)}"

@tool
def fetch_relevant_documents(query : str):
    """A function to retrieve the most relevant document based on the query"""
    results = vector_store.similarity_search_with_relevance_scores(query, k=3)
    print(f"[Retrieve KB] Found {len(results)} docs")
    return results