"""Configuration management for Graph RAG Resume Agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
RAW_DIR = DATA_DIR / "raw"
GRAPH_DIR = DATA_DIR / "graph"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

for d in [RAW_DIR, GRAPH_DIR, EMBEDDINGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN", "")
CLOUDFLARE_TOKEN = os.getenv("CLOUDFLARE_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

GITHUB_API = "https://api.github.com"
VERCEL_API = "https://api.vercel.com"
CLOUDFLARE_API = "https://api.cloudflare.com/client/v4"