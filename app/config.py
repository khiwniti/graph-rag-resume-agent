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

# Create directories
for d in [RAW_DIR, GRAPH_DIR, EMBEDDINGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# =============================================================================
# API Tokens (required for collection)
# =============================================================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN", "")
CLOUDFLARE_TOKEN = os.getenv("CLOUDFLARE_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# =============================================================================
# Embedding Configuration
# =============================================================================
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# =============================================================================
# Collection Limits (to avoid rate limits and excessive data)
# =============================================================================
MAX_REPOS = int(os.getenv("MAX_REPOS", "0"))  # 0 = all repos
MAX_FILES_PER_REPO = int(os.getenv("MAX_FILES_PER_REPO", "50"))
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", "50000"))
MAX_COMMITS_PER_REPO = int(os.getenv("MAX_COMMITS_PER_REPO", "30"))

# =============================================================================
# Conversation Artifact Configuration
# =============================================================================
CONVERSATION_ZIP_PATH = os.getenv("CONVERSATION_ZIP_PATH", "conversation_acc97712a9c1482992c7523a4ed73e08.zip")

# =============================================================================
# Output Paths
# =============================================================================
GRAPH_OUTPUT_PATH = os.getenv("GRAPH_OUTPUT_PATH", str(GRAPH_DIR / "knowledge_graph.json"))
VECTOR_INDEX_PATH = os.getenv("VECTOR_INDEX_PATH", str(EMBEDDINGS_DIR / "faiss_index"))

# =============================================================================
# API Endpoints
# =============================================================================
GITHUB_API = "https://api.github.com"
VERCEL_API = "https://api.vercel.com"
CLOUDFLARE_API = "https://api.cloudflare.com/client/v4"

# =============================================================================
# Validation
# =============================================================================
def validate_config():
    """Validate required configuration is present."""
    errors = []
    if not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN is required for collection")
    if not CLOUDFLARE_TOKEN:
        errors.append("CLOUDFLARE_TOKEN is required for Cloudflare collection")
    if not CLOUDFLARE_ACCOUNT_ID:
        errors.append("CLOUDFLARE_ACCOUNT_ID is required for Cloudflare collection")
    # VERCEL_TOKEN is optional if user has no Vercel projects
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    return True
