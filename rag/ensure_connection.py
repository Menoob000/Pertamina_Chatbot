import psycopg

# Connect to PostgreSQL
conn = psycopg.connect("postgresql://langchain:langchain@localhost:5432/langchain")
cursor = conn.cursor()

# Enable vector extension
cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# Create table for full, raw documents
cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id VARCHAR PRIMARY KEY,
        title TEXT,
        full_content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()
conn.close()
print("PostgreSQL setup ready!")