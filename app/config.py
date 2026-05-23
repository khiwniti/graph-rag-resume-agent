"""Configuration management for Graph RAG Resume Agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

# override=True so .env takes precedence over shell env vars
# (e.g. cloud Neo4j Aura credentials override local Docker defaults)
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
RAW_DIR = DATA_DIR / "raw"
GRAPH_DIR = DATA_DIR / "graph"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

# =============================================================================
# Neo4j Configuration
# =============================================================================
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Create directories for d in [RAW_DIR, GRAPH_DIR, EMBEDDINGS_DIR]:
for d in [RAW_DIR, GRAPH_DIR, EMBEDDINGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Embedding Configuration
# =============================================================================
NVIDIA_MODEL_ID = os.getenv("NVIDIA_MODEL_ID", "nvidia/nemotron-4-340b")

# =============================================================================
# API Tokens (required for collection)
# =============================================================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN", "")
CLOUDFLARE_TOKEN = os.getenv("CLOUDFLARE_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

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
# Ingestion Behavior
# =============================================================================
MIN_FREE_DISK_GB = float(os.getenv("MIN_FREE_DISK_GB", "5.0"))
INCLUDE_FORKS = os.getenv("INCLUDE_FORKS", "false").lower() in ("true", "1", "yes")
ENABLE_CONVERSATION_COLLECTOR = os.getenv("ENABLE_CONVERSATION_COLLECTOR", "false").lower() in ("true", "1", "yes")

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