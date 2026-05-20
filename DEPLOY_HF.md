# Deploy to Hugging Face Spaces

This guide explains how to deploy the Graph RAG Resume Agent to Hugging Face Spaces.

## Prerequisites

1. A Hugging Face account (free at https://huggingface.co/join)
2. `huggingface-cli` installed: `pip install huggingface_hub`
3. Your Hugging Face token from https://huggingface.co/settings/tokens

## Quick Deploy

### Option 1: Using the Makefile (if available)

```bash
# Login to Hugging Face
huggingface-cli login

# Create and push to your space
python scripts/deploy_hf.py --repo-id your-username/graph-rag-resume-agent
```

### Option 2: Manual Steps

1. **Create a new Space:**
   - Go to https://huggingface.co/new-space
   - Choose a Space name (e.g., `graph-rag-resume-agent`)
   - Select "Docker" as the SDK
   - Choose your license

2. **Push the code:**

```bash
# Login
huggingface-cli login

# Add remote (replace with your Space URL)
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/graph-rag-resume-agent

# Push to Hugging Face
git push hf main
```

3. **Set environment variables in your Space:**
   - Go to your Space settings
   - Add the following environment variables:
     - `GITHUB_TOKEN` - Your GitHub Personal Access Token
     - `VERCEL_TOKEN` - Your Vercel API Token
     - `CLOUDFLARE_API_TOKEN` - Your Cloudflare API Token

4. **Wait for the build to complete**

## Using the API

Once deployed, your API will be available at:

```
https://huggingface.co/spaces/YOUR_USERNAME/graph-rag-resume-agent
```

### API Endpoints

```bash
# Health check
curl https://YOUR_USERNAME-graph-rag-resume-agent.hf.space/health

# List skills
curl https://YOUR_USERNAME-graph-rag-resume-agent.hf.space/skills

# List projects
curl https://YOUR_USERNAME-graph-rag-resume-agent.hf.space/projects

# Query the agent
curl -X POST "https://YOUR_USERNAME-graph-rag-resume-agent.hf.space/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my Python skills?", "top_k": 5}'
```

## Notes

- The Docker build may take 5-10 minutes on first deploy
- Hugging Face Spaces with CPU are free for public repos
- For private Spaces, you need the Pro plan ($9/month)
- The FAISS index and models are cached in the Docker image
