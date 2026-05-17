# Graph RAG Resume Agent

An intelligent résumé agent that builds a knowledge graph from your GitHub repositories, Vercel deployments, Cloudflare workers, and conversation artifacts. It uses Retrieval-Augmented Generation (RAG) to answer queries about your skills and experience with evidence-backed responses.

## Features

- **Multi-Source Data Collection**: GitHub, Vercel, Cloudflare, and conversation exports
- **Evidence-Driven Skill Extraction**: Skills backed by actual code, dependencies, and configurations
- **Knowledge Graph Construction**: Structured representation of projects, skills, and relationships
- **Hybrid RAG Retrieval**: Combines vector search (FAISS) with graph traversal
- **Provenance Tracking**: Every skill claim links back to source evidence
- **Confidence Scoring**: Skills ranked by evidence quality and source reliability

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│  GitHub         │  Vercel         │  Cloudflare             │
│  Collector      │  Collector      │  Collector              │
│                 │                 │                         │
│  - Repos        │  - Projects     │  - Workers              │
│  - Code files   │  - Deployments  │  - Pages                │
│  - Dependencies │  - Git links    │  - KV/D1/R2             │
└─────────────────┴─────────────────┴─────────────────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                   ┌────────▼────────┐
                   │   Normalizers   │
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │   Extractors    │
                   │  - Dependencies │
                   │  - Source Code  │
                   │  - Skills       │
                   └────────┬────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
┌────────▼────────┐ ┌──────▼───────┐ ┌────────▼────────┐
│  Knowledge      │ │  Vector      │ │  Skill          │
│  Graph          │ │  Store       │ │  Extractor      │
│  (NetworkX)     │ │  (FAISS)     │ │                 │
└────────┬────────┘ └──────┬───────┘ └─────────────────┘
         │                  │
         └────────┬─────────┘
                  │
         ┌────────▼────────┐
         │  Hybrid         │
         │  Retriever      │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  Résumé         │
         │  Agent          │
         └─────────────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- GitHub Personal Access Token
- Vercel API Token
- Cloudflare API Token

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/khiwniti/graph-rag-resume-agent.git
   cd graph-rag-resume-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API tokens:
   ```env
   GITHUB_TOKEN=ghp_your_token_here
   VERCEL_TOKEN=vcp_your_token_here
   CLOUDFLARE_API_TOKEN=cfat_your_token_here
   
   # Optional: Collection limits
   MAX_REPOS=50
   MAX_FILES_PER_REPO=10
   ```

## Usage

### Running the API Server

Start the FastAPI server:

```bash
# Using the run script
python scripts/run_server.py

# Or directly with uvicorn
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Collect Data
```bash
curl -X POST http://localhost:8000/collect \
  -H "Content-Type: application/json" \
  -d '{"max_repos": 50, "max_files_per_repo": 10}'
```

#### Query the Agent
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my Python skills?", "top_k": 5}'
```

#### List Skills
```bash
curl http://localhost:8000/skills?min_confidence=0.3
```

#### List Projects
```bash
curl http://localhost:8000/projects
```

#### Get Skill Evidence
```bash
curl http://localhost:8000/skills/Python/evidence
```

### Running the Collection Pipeline

Run the full collection pipeline from command line:

```bash
python scripts/run_collection.py
```

Or with custom limits:

```bash
python scripts/run_collection.py --max-repos 100 --max-files-per-repo 20
```

### Testing the Agent

Run the test suite:

```bash
python scripts/test_agent.py
```

## Project Structure

```
graph-rag-resume-agent/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Configuration management
│   ├── main.py                   # FastAPI application
│   ├── pipeline.py               # Collection pipeline
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic models
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── github_collector.py   # GitHub data collector
│   │   ├── vercel_collector.py   # Vercel data collector
│   │   ├── cloudflare_collector.py
│   │   ├── conversation_collector.py
│   │   └── code_fetcher.py       # Code fetcher
│   ├── normalizers/
│   │   ├── __init__.py
│   │   ├── github_normalizer.py
│   │   ├── vercel_normalizer.py
│   │   ├── cloudflare_normalizer.py
│   │   └── conversation_normalizer.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── dependency_parser.py
│   │   ├── source_analyzer.py
│   │   ├── skill_extractor.py
│   │   └── evidence_ranker.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── builder.py            # Graph construction
│   │   ├── serializer.py         # Graph serialization
│   │   └── query.py              # Graph queries
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── chunker.py            # Text chunking
│   │   ├── embedder.py           # Embedding generation
│   │   ├── vector_store.py       # FAISS vector store
│   │   └── retriever.py          # Hybrid retrieval
│   └── agent/
│       ├── __init__.py
│       └── resume_agent.py       # Résumé agent
├── scripts/
│   ├── run_collection.py         # Collection CLI
│   ├── run_server.py             # Server runner
│   └── test_agent.py             # Test suite
├── data/                         # Data directory (auto-created)
│   ├── graph.json
│   ├── vector_store.faiss
│   └── chunks.json
├── .env.example
├── requirements.txt
├── README.md
└── IMPLEMENTATION_SUMMARY.md
```

## Evidence Confidence Weights

The system assigns confidence scores based on evidence type:

| Evidence Type | Weight | Description |
|--------------|--------|-------------|
| Source Code | 1.0 | Direct code implementation |
| Dependencies | 0.7 | Package dependencies (package.json, requirements.txt) |
| Config Files | 0.6 | Configuration files (tsconfig.json, etc.) |
| Deployments | 0.5 | Vercel/Cloudflare deployments |
| Conversation | 0.3 | Mentions in conversations |

## Example Queries

The agent can answer various questions about your skills and experience:

- "What are my Python skills?"
- "Which projects use React?"
- "What cloud technologies have I used?"
- "Show me my backend development experience"
- "Have I worked with Kubernetes?"
- "What frontend frameworks do I know?"

## API Documentation

Interactive API documentation are available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | Required |
| `VERCEL_TOKEN` | Vercel API Token | Required |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token | Required |
| `MAX_REPOS` | Maximum repositories to collect | 50 |
| `MAX_FILES_PER_REPO` | Maximum files per repository | 10 |
| `DATA_DIR` | Directory for data storage | `data/` |
| `GRAPH_PATH` | Path to graph JSON | `data/graph.json` |
| `VECTOR_STORE_PATH` | Path to FAISS index | `data/vector_store` |

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
