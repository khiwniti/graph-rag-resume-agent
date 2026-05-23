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
