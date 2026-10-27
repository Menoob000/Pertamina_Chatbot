import os
from dotenv import load_dotenv

load_dotenv()

# ========================
# Embedding Model
# ========================
# Runs locally via HuggingFace sentence-transformers, no API key needed.
# Vector size: 384 (all-minilm-l6-v2)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-minilm-l6-v2")

# ========================
# Qdrant Cloud Vector Store
# ========================
QDRANT_CLUSTER_ENDPOINT = os.getenv("QDRANT_CLUSTER_ENDPOINT", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# ========================
# OpenRouter LLM
# ========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen/qwen3.7-flash")

# ========================
# Qdrant Collections
# ========================
COLLECTION_RKS = "rks_kb"
COLLECTION_CONTRACT = "contract_kb"
COLLECTION_AMENDMENT = "amendment_kb"

# Vector dimension for all-minilm-l6-v2
VECTOR_SIZE = 384