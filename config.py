import os
from dotenv import load_dotenv

load_dotenv()

# ========================
# Embedding Model
# ========================
# Runs locally via HuggingFace sentence-transformers, no API key needed.
# Vector size: 384 (all-minilm-l6-v2)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-minilm-l6-v2")

# Pencarian RKS. Skor dinormalisasi ke 0..1 dan tetap perlu dikalibrasi pada KB nyata.
RKS_SEARCH_TOP_K = int(os.getenv("RKS_SEARCH_TOP_K", "5"))
RKS_SEARCH_SCORE_THRESHOLD = float(os.getenv("RKS_SEARCH_SCORE_THRESHOLD", "0.55"))
RKS_SEARCH_KEYWORD_WEIGHT = float(os.getenv("RKS_SEARCH_KEYWORD_WEIGHT", "0.65"))
RKS_SEARCH_SEMANTIC_WEIGHT = float(os.getenv("RKS_SEARCH_SEMANTIC_WEIGHT", "0.35"))
RKS_SEARCH_SEMANTIC_ENABLED = os.getenv("RKS_SEARCH_SEMANTIC_ENABLED", "true").lower() in {"1", "true", "yes"}
RKS_SEARCH_CHUNK_SIZE = int(os.getenv("RKS_SEARCH_CHUNK_SIZE", "1000"))
RKS_SEARCH_CHUNK_OVERLAP = int(os.getenv("RKS_SEARCH_CHUNK_OVERLAP", "150"))
RKS_SEARCH_MAX_SECTIONS = int(os.getenv("RKS_SEARCH_MAX_SECTIONS", "100"))

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
