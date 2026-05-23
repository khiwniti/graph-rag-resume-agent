# Knowledge Graph Architecture

This document describes the refactored architecture for the Graph RAG Resume Agent knowledge graph system.

## Overview

The system builds a knowledge graph from GitHub, Vercel, and Cloudflare data sources, then uses hybrid retrieval (graph + vector) to answer resume/RAG queries.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Sources                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  GitHub  │  │  Vercel  │  │Cloudflare│                  │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘                  │
└───────────┼──────────┼──────────┼─────────────┼──────────────┘
            │          │          │             │
            ▼          ▼          ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Collectors Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │GitHubCollector│  │VercelCollector│  │CloudflareCollector  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Extraction Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │SkillExtractor│  │DependencyParser│  │SourceAnalyzer       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Knowledge Graph (Neo4j)                       │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │  Person  │───▶│ Project  │───▶│  Skill   │                 │
│  └──────────┘    └────┬─────┘    └────┬─────┘                 │
│       │               │               │                       │
│       │               ▼               ▼                       │
│       │         ┌──────────┐   ┌──────────┐                 │
│       └────────▶│Technology│   │Deployment│                  │
│                 └──────────┘   └──────────┘                  │
│                        ▲                                      │
│                        │                                      │
│                   ┌──────────┐                               │
│                   │ Narrative│                               │
│                   └──────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAG Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Embedder    │  │ VectorStore  │  │  HybridRetriever     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                          │
│  /query  /skills  /projects  /health                           │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
graph-rag-resume-agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── pipeline.py          # Main pipeline orchestrator
│   ├── nvidia_api.py        # NVIDIA API client
│   │
│   ├── graph_store/         # Neo4j knowledge graph
│   │   ├── __init__.py
│   │   ├── neo4j_store.py   # Neo4j operations
│   │   └── builder.py       # Graph builder
│   │
│   ├── extractors/          # Skill/dependency/narrative extraction
│   │   ├── __init__.py
│   │   ├── skill_extractor.py
│   │   ├── dependency_parser.py
│   │   ├── source_analyzer.py
│   │   └── narrative_builder.py   # LLM career summaries
│   │
│   ├── collectors/          # Data collection
│   │   ├── __init__.py
│   │   ├── github_collector.py
│   │   ├── vercel_collector.py
│   │   └── cloudflare_collector.py
│   │
│   └── rag/                 # RAG components
│       ├── __init__.py
│       ├── retriever.py     # Hybrid retriever
│       ├── embedder.py      # Text embeddings
│       ├── vector_store.py  # FAISS vector store
│       └── chunker.py       # Text chunking
│
├── scripts/
│   ├── build_knowledge_graph.py  # Graph build script
│   ├── run_server.py
│   └── run_collection.py
│
├── tests/
│   ├── __init__.py
│   ├── test_collectors.py
│   ├── test_extractors.py
│   └── test_graph_store.py
│
├── requirements.txt
├── .env.example
└── README.md
```

## Neo4j Schema

### Node Types

| Label | Properties | Description |
|-------|------------|-------------|
| `Person` | `id`, `name`, `email`, `updated_at` | The person (you) |
| `Project` | `id`, `name`, `source`, `url`, `description`, `created_at`, `pushed_at`, `first_commit_at`, `last_commit_at` | GitHub repos, Vercel projects, Cloudflare workers |
| `Skill` | `name`, `category`, `confidence` | Extracted skills |
| `Technology` | `name`, `type` | Technologies, libraries, frameworks |
| `Deployment` | `id`, `url`, `platform` | Deployed applications |
| `Narrative` | `id`, `text`, `period_start`, `period_end` | LLM-generated career story per project |

### Relationships

| Pattern | Description |
|---------|-------------|
| `(:Person)-[:OWNS]->(:Project)` | Person owns/created project |
| `(:Person)-[:HAS_SKILL {confidence, evidence}]->(:Skill)` | Person has skill |
| `(:Project)-[:REQUIRES_SKILL {evidence}]->(:Skill)` | Project requires skill |
| `(:Project)-[:USES_TECHNOLOGY {evidence_type}]->(:Technology)` | Project uses technology |
| `(:Project)-[:DEPLOYED_ON]->(:Deployment)` | Project deployed on platform |
| `(:Project)-[:DESCRIBED_BY]->(:Narrative)` | Project described by narrative |
| `(:Narrative)-[:MENTIONS]->(:Skill)` | Narrative mentions skill |
| `(:Narrative)-[:MENTIONS]->(:Technology)` | Narrative mentions technology |

## Usage

### 1. Set up Neo4j

```bash
# Install Neo4j Desktop or use Docker
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Build the knowledge graph

```bash
python scripts/build_knowledge_graph.py create_sample
```

### 4. Query skills

```bash
python scripts/build_knowledge_graph.py query --person-id me
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/query` | POST | Query the RAG system |
| `/skills` | GET | List all skills |
| `/skills/{name}/evidence` | GET | Get evidence for a skill |
| `/projects` | GET | List all projects |
| `/narratives` | GET | List career narratives |
| `/career-story` | GET | Get career story by period/topic |

## Key Components

### SkillExtractor
Extracts skills from source code with confidence scoring based on evidence type:
- Source code: 1.0
- Dependencies: 0.7
- Config files: 0.6
- Deployments: 0.5

### NarrativeBuilder
Generates LLM-powered career narrative summaries per project using repository
metadata, README content, and extracted skills. Narratives are stored as
`Narrative` nodes linked to `Project` nodes for career-story RAG queries.

### HybridRetriever
Combines graph traversal with vector similarity for comprehensive retrieval.
Supports skill search, narrative retrieval, and period-based career story queries.

### Neo4jStore
Provides graph operations with proper indexing and constraints for efficient querying.
