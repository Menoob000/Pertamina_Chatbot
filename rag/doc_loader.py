import os
import uuid
import re
import psycopg
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
import config
from dotenv import load_dotenv
load_dotenv()

PGVECTOR_HOST = os.getenv("PGVECTOR_HOST", "127.0.0.1")
PGVECTOR_PORT = int(os.getenv("PGVECTOR_PORT", "5432"))
PGVECTOR_USER = os.getenv("PGVECTOR_USER", "langchain")
PGVECTOR_PASSWORD = os.getenv("PGVECTOR_PASSWORD", "langchain")
PGVECTOR_DB = os.getenv("PGVECTOR_DB", "langchain")
PGVECTOR_CONNECTION = (
    f"postgresql+psycopg://{PGVECTOR_USER}:{PGVECTOR_PASSWORD}"
    f"@{PGVECTOR_HOST}:{PGVECTOR_PORT}/{PGVECTOR_DB}"
)


def loader(file_path='./data', connection=PGVECTOR_CONNECTION):
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
        grouped_docs[source_file].append(doc)

    # 2. Setup Embeddings and PGVector Store
    embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name="knowledge_base",
        connection=connection,
    )

    # 3. Process each document
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.RKS_SEARCH_CHUNK_SIZE,
        chunk_overlap=config.RKS_SEARCH_CHUNK_OVERLAP,
    )

    db_conn = psycopg.connect(
        host=PGVECTOR_HOST,
        port=PGVECTOR_PORT,
        dbname=PGVECTOR_DB,
        user=PGVECTOR_USER,
        password=PGVECTOR_PASSWORD,
    )
    cursor = db_conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS documents ("
        "id UUID PRIMARY KEY, title TEXT NOT NULL, full_content TEXT NOT NULL)"
    )
    cursor.execute("SELECT title FROM documents")
    existing_titles = {row[0] for row in cursor.fetchall()}

    for file_name, pages in grouped_docs.items():
        if file_name in existing_titles:
            print(f"Skipping already indexed: {file_name}")
            continue

        doc_id = str(uuid.uuid4())
        # Before inserting into PostgreSQL, sanitize NUL bytes
        full_text = "\n".join(page.page_content for page in pages).replace("\x00", "")

        # Split document into smaller chunks for vector search
        chunks, metadatas = [], []
        year = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", file_name)
        version = re.search(r"\b(?:rev(?:isi)?|versi|v)[ ._-]*(\d+)\b", file_name, re.I)
        for page in pages:
            number = int(page.metadata.get("page", 0)) + 1
            section = next((line.strip() for line in page.page_content.splitlines()
                            if re.match(r"^(?:BAB\s+[IVXLC\d]+|\d+(?:\.\d+)*[.)]?\s+)", line.strip(), re.I)), None)
            for chunk in text_splitter.split_text(page.page_content.replace("\x00", "")):
                chunks.append(chunk)
                metadatas.append({"document_id": doc_id, "file_name": file_name,
                                  "page": number,
                                  "document_type": "RKS" if "rks" in file_name.lower() else "lainnya",
                                  **({"section": section} if section else {}),
                                  **({"year": int(year.group())} if year else {}),
                                  **({"version": version.group(1)} if version else {})})
        if not chunks:
            print(f"Skipping unreadable document: {file_name}")
            continue
        cursor.execute(
            "INSERT INTO documents (id, title, full_content) VALUES (%s, %s, %s)",
            (doc_id, file_name, full_text)
        )

        # Add vector embeddings into PGVector store
        vector_store.add_texts(texts=chunks, metadatas=metadatas)
        print(f"Successfully processed: {file_name} (ID: {doc_id})")
        existing_titles.add(file_name)

    db_conn.commit()
    db_conn.close()
    print("All PDFs loaded and indexed into PGVector!")

def main():
    loader()

if __name__ == "__main__":
    main()
