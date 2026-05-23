# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Graph RAG Resume Agent that builds a knowledge graph from multiple sources (GitHub repositories, Vercel deployments, Cloudflare workers, conversation artifacts) and uses Retrieval-Augmented Generation (RAG) to answer queries about skills and experience with evidence-backed responses.

## Architecture

The system consists of several key components:

1. **Data Collection Layer**: Collectors for GitHub, Vercel, Cloudflare, and conversation data
2. **Normalization Layer**: Normalizers that standardize data from different sources
3. **Extraction Layer**: Extractors that parse dependencies, analyze source code, and extract skills
4. **Knowledge Graph**: NetworkX-based graph representing projects, skills, and relationships
5. **Vector Store**: FAISS-based vector storage for semantic search
6. **Hybrid Retriever**: Combines vector search with graph traversal
7. **Resume Agent**: Main interface for querying skills and experience

## Common Commands

### Installation
```bash
pip install -r requirements.txt
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env to add API tokens:
# GITHUB_TOKEN=ghp_your_token_here
# VERCEL_TOKEN=vcp_your_token_here
# CLOUDFLARE_API_TOKEN=cfat_your_token_here
```

### Running the API Server
```bash
# Using the run script
python scripts/run_server.py

# Or directly with uvicorn
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Collection Pipeline
```bash
# Run the full collection pipeline
python scripts/run_collection.py

# Or with custom limits
python scripts/run_collection.py --max-repos 100 --max-files-per-repo 20
```

### Testing
```bash
# Run the test suite
python scripts/test_agent.py
```

## Key Files and Directories

- `app/main.py`: FastAPI application with endpoints
- `app/pipeline.py`: Main collection pipeline orchestrator
- `app/config.py`: Configuration management
- `app/collectors/`: Data collectors for GitHub, Vercel, Cloudflare, and conversations
- `app/normalizers/`: Data normalizers for different sources
- `app/extractors/`: Skill and dependency extractors
- `app/graph/builder.py`: Knowledge graph construction
- `app/rag/`: RAG components (chunker, embedder, vector store, retriever)
- `app/agent/resume_agent.py`: Main agent implementation
- `scripts/`: Utility scripts for running the application
- `data/`: Storage for graph, vector store, and chunks (auto-created)

## Development Guidelines

1. **Evidence-Based Approach**: All skills must be backed by actual code, dependencies, or configurations
2. **Confidence Scoring**: Skills are ranked by evidence quality and source reliability
3. **Provenance Tracking**: Every skill claim links back to source evidence
4. **Multi-Source Integration**: Combine information from GitHub, Vercel, Cloudflare, and conversations

## API Endpoints

- `GET /health`: Health check
- `POST /collect`: Trigger data collection
- `POST /query`: Query the resume agent
- `GET /skills`: List all extracted skills
- `GET /skills/{skill}/evidence`: Get evidence for a specific skill
- `GET /projects`: List all projects
- `GET /skills/search`: Search for skills by name

## Key Concepts

- **Knowledge Graph**: NetworkX-based representation of projects, skills, and relationships
- **Vector Store**: FAISS-based storage for semantic search of text chunks
- **Hybrid Retrieval**: Combines vector search with graph traversal for comprehensive results
- **Confidence Scoring**: Skills ranked by evidence quality with weights for different evidence types
- **Evidence Types**: Source code (1.0), dependencies (0.7), config files (0.6), deployments (0.5), conversations (0.3)