import os
import uuid
import psycopg
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
import config
from dotenv import load_dotenv
load_dotenv()


def loader(file_path='./data', connection="postgresql+psycopg://langchain:langchain@localhost:5432/langchain"):
    # 1. Load all PDFs from the ./data folder
    print(f"Loading PDFs from {file_path}...")
    loader = PyPDFDirectoryLoader(file_path)
    raw_docs = loader.load()

    if not raw_docs:
        print("No PDF files found in ./data folder!")
        exit()

    # Group page contents by file source so we can assemble the full raw document
    grouped_docs = {}
    for doc in raw_docs:
        source_file = os.path.basename(doc.metadata.get("source", "unknown"))
        if source_file not in grouped_docs:
            grouped_docs[source_file] = []
        grouped_docs[source_file].append(doc.page_content)

    # 2. Setup Embeddings and PGVector Store
    embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=os.getenv('OPENROUTER_API_KEY'),
            openai_api_base="https://openrouter.ai/api/v1",
            tiktoken_enabled=False,
            )
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name="knowledge_base",
        connection=connection,
    )

    # 3. Process each document
    text_splitter = SemanticChunker(embeddings=embeddings)

    db_conn = psycopg.connect("postgresql://langchain:langchain@localhost:5432/langchain")
    cursor = db_conn.cursor()

    for file_name, pages in grouped_docs.items():
        doc_id = str(uuid.uuid4())
        # Before inserting into PostgreSQL, sanitize NUL bytes
        full_text = "\n".join(pages).replace("\x00", "")

        # Insert raw, full document into standard SQL table
        cursor.execute(
            "INSERT INTO documents (id, title, full_content) VALUES (%s, %s, %s)",
            (doc_id, file_name, full_text)
        )

        # Split document into smaller chunks for vector search
        chunks = text_splitter.split_text(full_text)
        
        # Prepare metadata for each chunk so it references the original document ID
        metadatas = [{"document_id": doc_id, "file_name": file_name} for _ in chunks]

        # Add vector embeddings into PGVector store
        vector_store.add_texts(texts=chunks, metadatas=metadatas)
        print(f"Successfully processed: {file_name} (ID: {doc_id})")

    db_conn.commit()
    db_conn.close()
    print("All PDFs loaded and indexed into PGVector!")

def main():
    loader()

if __name__ == "__main__":
    main()