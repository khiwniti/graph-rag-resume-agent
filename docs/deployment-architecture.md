# Deployment Architecture

## Overview

The Graph RAG Resume Agent system has two deployable components:

1. **Graph RAG Backend** (this repo) → Hugging Face Spaces (Docker)
2. **MCP UI Frontend** (resume-mcp-ui repo) → Vercel/Manufact Cloud

## Component 1: Graph RAG Backend

**Repository:** `graph-rag-resume-agent` (this repo)

**Deploys to:** Hugging Face Spaces (Docker)

**Why Hugging Face Spaces:**
- Supports Docker containers with no strict size limits
- Can run Gradio + Python backend together
- Free tier supports private repos
- Built-in environment variable management

**Deployment:**
```bash
python scripts/deploy_hf.py --repo-id getintheq/graph-rag-resume-agent
```

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `VERCEL_TOKEN` | Vercel API Token (optional) |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token (optional) |
| `HF_TOKEN` | Hugging Face Token (for MCP integration) |

**What it serves:**
- Gradio UI on port 7860
- Knowledge graph data (static JSON)
- FAISS vector store for RAG
- MCP server tools (when integrated)

---

## Component 2: MCP UI Frontend

**Repository:** `resume-mcp-ui` (separate repo)

**Deploys to:** Vercel / Manufact Cloud

**Why Vercel:**
- Optimized for Next.js/React apps
- Edge functions for low-latency widget rendering
- Easy deployment from GitHub
- Free tier sufficient for portfolio use

**Deployment:**
```bash
cd resume-mcp-ui
npm install
npm run deploy
```

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `MCP_URL` | URL of the MCP server (Graph RAG backend) |
| `ANTHROPIC_API_KEY` | For AI agent redesign features |
| `GRAPH_RAG_URL` | URL of deployed Graph RAG backend |

**What it serves:**
- Resume dashboard with AI agents
- Knowledge graph visualization
- Agent activity feed
- Scheduling controls

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ DEVELOPMENT (Local)                                             │
│                                                                 │
│  1. Raw Data (github.json, vercel.json, cloudflare.json)       │
│            │                                                    │
│  2. Extract Metadata (metadata_extractor.py)                   │
│            │                                                    │
│  3. Build Graph (build_graph_from_metadata.py)                 │
│            │                                                    │
│  4. Serve via Gradio (app_gradio.py)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ Deploy
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PRODUCTION (Hugging Face Spaces)                                │
│                                                                 │
│  Graph RAG Backend                                              │
│  - Knowledge Graph: 240 nodes, 1480 edges                      │
│  - Metadata: 213 projects                                       │
│  - Vector Store: FAISS embeddings                               │
│  - Gradio UI: 4 tabs (Query, Skills, Projects, Health)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ MCP Protocol
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCP UI (Vercel)                                                 │
│                                                                 │
│  - Resume Tab: Section cards with AI redesign                  │
│  - Agents Tab: Expert agent status                              │
│  - Graph Tab: Knowledge graph visualization                     │
│  - Schedule Tab: Automated redesign config                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Steps

### Step 1: Deploy Graph RAG Backend

```bash
# 1. Extract metadata (if raw data changed)
python app/extractors/metadata_extractor.py

# 2. Build knowledge graph
python scripts/build_graph_from_metadata.py

# 3. Deploy to Hugging Face Spaces
python scripts/deploy_hf.py --repo-id getintheq/graph-rag-resume-agent
```

**Expected output:**
```
✓ Space created/exists: getintheq/graph-rag-resume-agent
✓ Uploaded: Dockerfile
✓ Uploaded: requirements.txt
✓ Uploaded: README.md
✓ Uploaded: app_gradio.py
✓ Uploaded: app/extractors/metadata_extractor.py
✓ Uploaded: app/mcp_server.py
✓ Uploaded: scripts/build_graph_from_metadata.py
✓ Uploaded: data/metadata/extracted_metadata.json
✓ Uploaded: data/graph/knowledge_graph.json

Deployment complete!
View: https://huggingface.co/spaces/getintheq/graph-rag-resume-agent
```

### Step 2: Deploy MCP UI Frontend

```bash
cd resume-mcp-ui

# Set environment variables
vercel env set MCP_URL https://getintheq-graph-rag-resume-agent.hf.space
vercel env set ANTHROPIC_API_KEY $ANTHROPIC_API_KEY

# Deploy
npm run deploy
```

**Expected output:**
```
Vercel CLI 3.x.x
Ready → https://resume-mcp-ui.vercel.app
```

---

## Post-Deployment Verification

### 1. Check Graph RAG Backend

```bash
# Health check
curl https://getintheq-graph-rag-resume-agent.hf.space/health

# Expected:
# {"status": "healthy", "graph_loaded": true, "vector_store_loaded": true}
```

### 2. Check MCP UI

```bash
# Open in browser
open https://resume-mcp-ui.vercel.app

# Or test MCP tools
curl https://resume-mcp-ui.vercel.app/api/tools/query_knowledge_graph \
  -H "Content-Type: application/json" \
  -d '{"node_type": "skill"}'
```

### 3. Test Integration

1. Open MCP UI dashboard
2. Click "Graph" tab
3. Should see knowledge graph with 240 nodes
4. Query should return skills, projects, domains

---

## Troubleshooting

### Graph RAG Backend Issues

| Issue | Solution |
|-------|----------|
| "Module not found: app" | Dockerfile CMD is correct, don't change |
| "Metadata not found" | Run `metadata_extractor.py` first |
| Build fails | Check `requirements.txt` has all deps |
| Port 7860 not responding | Check Hugging Face Space logs |

### MCP UI Issues

| Issue | Solution |
|-------|----------|
| "MCP server not reachable" | Check `MCP_URL` env var |
| Widget not loading | Check browser console for errors |
| AI agents not working | Verify `ANTHROPIC_API_KEY` is set |

---

## Cost Breakdown

| Component | Platform | Cost |
|-----------|----------|------|
| Graph RAG Backend | Hugging Face Spaces | Free (public) / $9/mo (private) |
| MCP UI Frontend | Vercel | Free (hobby tier) |
| Knowledge Graph Storage | Hugging Face Spaces | Included |
| Vector Store | Hugging Face Spaces | Included |
| MCP Tools | Vercel Functions | Free (100k req/mo) |

**Total: $0-9/month** depending on privacy needs

---

## Security Notes

1. **Never commit tokens** - Use environment variables
2. **Private repos** - Hugging Face Spaces supports private Docker deployments
3. **API rate limiting** - MCP server should rate limit queries
4. **Input sanitization** - All graph queries should sanitize user input
