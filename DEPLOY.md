# Deployment Guide

This guide covers deployment options for the Graph RAG Resume Agent.

## Deployment Status

| Platform | Status | Notes |
|----------|--------|-------|
| Vercel | ❌ Failed | Bundle size (4945 MB) exceeds 500 MB limit |
| Cloud Run | ✅ Ready | Dockerfile and script provided |
| Local | ✅ Working | Neo4j + FastAPI running locally |

## Why Vercel Failed

The application uses `sentence-transformers` which requires PyTorch, resulting in a 4945 MB bundle. Vercel's serverless functions have a 500 MB limit.

**Options:**
1. Use **Google Cloud Run** (recommended)
2. Use **AWS Lambda** with container support (10 GB limit)
3. Use **Azure Container Apps**
4. Keep running **locally** with Neo4j

---

## Option 1: Google Cloud Run (Recommended)

### Prerequisites

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Login to GCP
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### Deploy

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export GITHUB_TOKEN="ghp_xxx"
export VERCEL_TOKEN="vcp_xxx"
export CLOUDFLARE_TOKEN="cfat_xxx"
export CLOUDFLARE_ACCOUNT_ID="xxx"
export NEO4J_URI="bolt://your-neo4j-host:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"

# Deploy
./deploy-cloud-run.sh
```

### Manual Deploy Steps

```bash
# 1. Build Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/graph-rag-agent:latest .

# 2. Push to Container Registry
docker push gcr.io/YOUR_PROJECT_ID/graph-rag-agent:latest

# 3. Deploy to Cloud Run
gcloud run deploy graph-rag-agent \
  --image gcr.io/YOUR_PROJECT_ID/graph-rag-agent:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

---

## Option 2: AWS Lambda (Container)

```bash
# Build and push to ECR
aws ecr create-repository --repository-name graph-rag-agent
docker tag graph-rag-agent:latest <account>.dkr.ecr.region.amazonaws.com/graph-rag-agent:latest
docker push <account>.dkr.ecr.region.amazonaws.com/graph-rag-agent:latest

# Deploy to Lambda
aws lambda create-function \
  --function-name graph-rag-agent \
  --package-type container \
  --image-uri <account>.dkr.ecr.region.amazonaws.com/graph-rag-agent:latest \
  --memory-size 10240 \
  --timeout 900
```

---

## Option 3: Azure Container Apps

```bash
# Build and push to ACR
az acr build --registry YOUR_REGISTRY --image graph-rag-agent:latest .

# Deploy to Container Apps
az containerapp create \
  --name graph-rag-agent \
  --resource-group YOUR_RG \
  --image YOUR_REGISTRY.azurecr.io/graph-rag-agent:latest \
  --target-port 8000 \
  --ingress external
```

---

## Local Development

For local testing:

```bash
# Start Neo4j
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community

# Install dependencies
pip install -r requirements.txt

# Run the API server
python scripts/run_server.py
```

---

## Neo4j Aura Free profile

`export_to_neo4j(graph, profile="aura_free")` ships a pruned subgraph that
fits inside Aura Free's 200,000-node / 400,000-relationship cap. The full
graph stays on disk in `data/graph/knowledge_graph.json`.

**What the profile drops or caps:**

- All `CALLS` edges (the largest edge type — ~78% of the full graph).
- `IMPLEMENTS` and `DOCUMENTS` edges, capped at `implements_top_n` / `documents_top_n`
  per source node (default 10, by descending weight).
- `:function` nodes orphaned by the `CALLS` removal.
- `Evidence` rows not referenced by any retained node or edge.

The profile can also be set via `NEO4J_PROFILE=aura_free` (kwarg wins).

A projection log is emitted before any write; if projected counts still
exceed Aura Free's caps the exporter logs a warning but does not abort.
Lower the `*_top_n` kwargs to trim further (the product page advertises a
stricter 50,000-node / 175,000-relationship cap in some regions).

**Aura Free pause behavior:**

Aura Free pauses an instance after 72 hours of inactivity; the first query
after resume can take a few minutes while the backup is restored. Build
retry/backoff into clients and consider a daily lightweight `RETURN 1`
query to keep the instance warm.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub API token |
| `VERCEL_TOKEN` | Yes | Vercel API token |
| `CLOUDFLARE_TOKEN` | Yes | Cloudflare API token |
| `CLOUDFLARE_ACCOUNT_ID` | Yes | Cloudflare account ID |
| `NEO4J_URI` | Yes | Neo4j connection URI |
| `NEO4J_USER` | Yes | Neo4j username |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `NEO4J_PROFILE` | No | Export profile: "full" (default) or "aura_free" |
| `EMBEDDING_MODEL` | No | Default: `all-MiniLM-L6-v2` |

---

## Cost Comparison

| Platform | Free Tier | Paid | Notes |
|----------|-----------|------|-------|
| Vercel | 100 GB-hrs/mo | $20/mo | Not suitable (size limit) |
| Cloud Run | 2M req/mo | ~$0.016/GB-hr | Best for this app |
| Lambda | 1M req/mo | $0.0000166667/GB-sec | Good alternative |
| Azure ACA | No free tier | ~$0.012/GB-hr | Similar to Cloud Run |

---

## Post-Deployment

After deployment, verify:

```bash
# Check health
curl https://YOUR_URL/health

# List skills
curl https://YOUR_URL/skills

# Query the agent
curl -X POST https://YOUR_URL/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my Python skills?", "top_k": 5}'
```
