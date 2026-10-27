from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
import config
from langchain_core.tools import tool
import psycopg
from dotenv import load_dotenv
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
    """Finds and returns the full document content matching the user query."""
    
    # Step A: Perform vector search to find the matching chunk
    results = vector_store.similarity_search(user_query, k=1)
    if not results:
        return "No matching document found."
    
    # Extract the document_id saved in chunk metadata
    doc_id = results[0].metadata.get("document_id")
    
    # Step B: Fetch the original full text from the SQL table
    conn = psycopg.connect("dbname=langchain user=langchain password=langchain host=localhost")
    cursor = conn.cursor()
    cursor.execute("SELECT full_content FROM documents WHERE id = %s", (doc_id,))
    full_doc = cursor.fetchone()
    conn.close()
    
    return full_doc[0] if full_doc else "Document ID not found in database."

@tool
def fetch_relevant_documents(query : str):
    """A function to retrieve the most relevant document based on the query"""
    results = vector_store.similarity_search_with_relevance_scores(query, k=3)
    print(f"[Retrieve KB] Found {len(results)} docs")
    return results