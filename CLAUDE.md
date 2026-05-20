# CLAUDE.md
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Graph RAG Resume Agent that builds a knowledge graph from multiple sources (GitHub repositories, Vercel deployments, Cloudflare workers, conversation artifacts) and uses Retrieval-Augmented Generation (RAG) to answer queries about skills and experience with evidence-backed responses.

## Architecture

### Data Flow
```
Collectors (GitHub, Vercel, Cloudflare, Conversations)
    ↓
Normalizers (standardize data formats)
    ↓
Extractors (dependencies, source code, skills)
    ↓
Knowledge Graph (NetworkX) + Vector Store (FAISS)
    ↓
Hybrid Retriever (vector + graph search)
    ↓
Resume Agent (query interface)
```

### Key Components

**Collectors** (`app/collectors/`):
- `github_collector.py`: Fetches repos, code, languages, dependencies
- `vercel_collector.py`: Fetches projects, deployments, domains
- `cloudflare_collector.py`: Fetches workers, pages, KV/D1/R2 resources
- `conversation_collector.py`: Processes conversation artifacts

**Normalizers** (`app/normalizers/`):
- Normalize data from different sources into common schemas

**Extractors** (`app/extractors/`):
- `dependency_parser.py`: Parses package.json, requirements.txt
- `source_analyzer.py`: Analyzes source code for patterns
- `skill_extractor.py`: Extracts skills with confidence scoring
- `evidence_ranker.py`: Ranks evidence by type (source=1.0, deps=0.7, config=0.6, deployment=0.5, conversation=0.3)

**Graph** (`app/graph/`):
- `builder.py`: Constructs NetworkX graph with nodes (person, repo, project, skill) and edges (OWNS, BUILT, USES, DEPLOYED_ON)
- `query.py`: Graph traversal and skill lookup
- `serializer.py`: Graph persistence

**RAG** (`app/rag/`):
- `chunker.py`: Text chunking for embeddings
- `embedder.py`: Sentence transformer embeddings
- `vector_store.py`: FAISS index management
- `retriever.py`: Hybrid retrieval (vector + graph with Reciprocal Rank Fusion)

**Agent** (`app/agent/`):
- `resume_agent.py`: Main query interface with evidence-based responses

## Common Commands

### Installation
```bash
pip install -r requirements.txt
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env with: GITHUB_TOKEN, VERCEL_TOKEN, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, OPENAI_API_KEY
```

### Running the API Server
```bash
# Development server with auto-reload
python scripts/run_server.py

# Or directly
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Collection Pipeline
```bash
# Full collection pipeline
python scripts/run_collection.py

# With limits
python scripts/run_collection.py --max-repos 50 --max-files-per-repo 10
```

### Testing
```bash
# Run test suite
python scripts/test_agent.py

# Test individual components
python scripts/validate.py  # Validate graph structure
python scripts/demo.py      # Demo queries
```

### Utility Scripts
- `scripts/build_graph.py`: Build graph from collected data
- `scripts/build_embeddings.py`: Build FAISS embeddings
- `scripts/validate.py`: Validate graph integrity

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with graph/vector store status |
| `/collect` | POST | Trigger data collection pipeline |
| `/query` | POST | Query the resume agent |
| `/skills` | GET | List all extracted skills (filter by min_confidence) |
| `/skills/{skill}/evidence` | GET | Get evidence for a specific skill |
| `/projects` | GET | List all projects |
| `/skills/search` | GET | Search skills by name |
| `/reset` | POST | Reset agent state |

## Configuration

### Environment Variables
- `GITHUB_TOKEN`: Required for GitHub collection
- `VERCEL_TOKEN`: Required for Vercel collection
- `CLOUDFLARE_API_TOKEN`: Required for Cloudflare collection
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID
- `OPENAI_API_KEY`: For embeddings (if using OpenAI)
- `EMBEDDING_MODEL`: Sentence transformer model (default: all-MiniLM-L6-v2)

### Collection Limits
- `MAX_REPOS`: Max repositories to collect (0 = all)
- `MAX_FILES_PER_REPO`: Max files per repository
- `MAX_FILE_BYTES`: Max file size to process
- `MAX_COMMITS_PER_REPO`: Max commits to fetch per repo

## Evidence Confidence Weights

| Evidence Type | Weight | Source |
|--------------|--------|--------|
| Source Code | 1.0 | Direct code usage, imports |
| Dependencies | 0.7 | package.json, requirements.txt |
| Config Files | 0.6 | tsconfig.json, deployment configs |
| Deployments | 0.5 | Vercel/Cloudflare deployments |
| Conversation | 0.3 | Conversation mentions |

## Development Patterns

1. **Evidence-Based**: All skills must have traceable evidence
2. **Confidence Scoring**: Skills ranked by evidence quality
3. **Provenance Tracking**: Every claim links to source
4. **Multi-Source**: Combine GitHub, Vercel, Cloudflare, conversations

## Key Files

- `app/main.py`: FastAPI application
- `app/pipeline.py`: Collection pipeline orchestrator
- `app/config.py`: Configuration management
- `app/models/schemas.py`: Pydantic models
- `data/`: Auto-created storage for graph, vector store, chunks
