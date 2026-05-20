---
title: Graph RAG Resume Agent
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
license: mit
---

# Graph RAG Resume Agent

An intelligent résumé agent that builds a knowledge graph from your GitHub repositories, Vercel deployments, Cloudflare workers, and conversation artifacts. It uses Retrieval-Augmented Generation (RAG) to answer queries about your skills and experience with evidence-backed responses.

## Features

- **Multi-Source Data Collection**: GitHub, Vercel, Cloudflare, and conversation exports
- **Evidence-Driven Skill Extraction**: Skills backed by actual code, dependencies, and configurations
- **Knowledge Graph Construction**: Structured representation of projects, skills, and relationships
- **Hybrid RAG Retrieval**: Combines vector search (FAISS) with graph traversal
- **Provenance Tracking**: Every skill claim links back to source evidence
- **Confidence Scoring**: Skills ranked by evidence quality and source reliability

## Deployment

This space is deployed on Hugging Face Spaces with Docker support.

### Environment Variables

Set the following in your Space settings:
- `GITHUB_TOKEN` - Your GitHub Personal Access Token
- `VERCEL_TOKEN` - Your Vercel API Token  
- `CLOUDFLARE_API_TOKEN` - Your Cloudflare API Token

### Local Development

```bash
# Clone the repository
git clone https://huggingface.co/spaces/your-username/graph-rag-resume-agent
cd graph-rag-resume-agent

# Install dependencies
pip install -r requirements.txt

# Run the server
python scripts/run_server.py
```

## Usage

### API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /query` - Query the agent with a question
- `GET /skills` - List all skills
- `GET /projects` - List all projects
- `GET /skills/{skill}/evidence` - Get evidence for a skill

### Example Query

```bash
curl -X POST "https://your-space.hf.space/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my Python skills?", "top_k": 5}'
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Data Collection Layer                                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│ GitHub          │ Vercel          │ Cloudflare              │
│ Collector       │ Collector       │ Collector               │
│                 │                 │                         │
│ - Repos         │ - Projects      │ - Workers               │
│ - Code files    │ - Deployments   │ - KV/D1/R2              │
│ - Dependencies  │ - Git links     │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │   Graph RAG   │
              │   Agent       │
              └───────────────┘
```

## License

MIT
