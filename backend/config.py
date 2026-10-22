"""All environment-specific settings live here. Override with env vars."""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

# Folder with chunks.pkl, embeddings.npy, faiss.index.
# On Kaggle: RAG_DATA_DIR=/kaggle/input/datasets/madhavtiwary01/os-cef
RAG_DATA_DIR = os.environ.get("RAG_DATA_DIR", os.path.join(_HERE, "data"))

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen3-8B")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

# "local" = Qwen3-8B 4-bit on your own GPU (original Kaggle setup).
# "groq"  = CPU hosting: same retrieval, answers written by a Groq-hosted Qwen.
GENERATOR = os.environ.get("GENERATOR", "local").lower()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
FASTEMBED_CACHE = os.environ.get("FASTEMBED_CACHE", os.path.join(_HERE, ".fastembed"))

# Comma-separated list of frontend origins allowed to call the API.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080,"
        "https://id-preview--ecec7949-432a-48e3-a269-b79d5f4e7f12.lovable.app,"
        "https://ecec7949-432a-48e3-a269-b79d5f4e7f12.lovableproject.com,"
        "https://os-tutor.lovable.app",
    ).split(",")
    if o.strip()
]

# Set SKIP_MODEL_LOAD=1 to start without the theory side (numericals only).
SKIP_MODEL_LOAD = os.environ.get("SKIP_MODEL_LOAD") == "1"
