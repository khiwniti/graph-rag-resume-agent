# Quick Start Guide

This guide will help you get the Graph RAG Resume Agent up and running quickly.

## Prerequisites

- Python 3.9+
- GitHub account (for Personal Access Token)
- Vercel account (for API Token)
- Cloudflare account (for API Token)

## Step 1: Install Dependencies

```bash
cd graph-rag-resume-agent
pip install -r requirements.txt
```

## Step 2: Configure API Tokens

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your tokens:

```env
# Required API Tokens
GITHUB_TOKEN=ghp_your_github_token_here
VERCEL_TOKEN=vcp_your_vercel_token_here
CLOUDFLARE_API_TOKEN=cfat_your_cloudflare_token_here

# Optional: Collection limits
MAX_REPOS=50
MAX_FILES_PER_REPO=10
```

### Getting Your Tokens

**GitHub:**
1. Go to https://github.com/settings/tokens
2. Create a new token with `repo` scope
3. Copy the token to `.env`

**Vercel:**
1. Go to https://vercel.com/account/settings
2. Navigate to API tokens
3. Create a new token
4. Copy the token to `.env`

**Cloudflare:**
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Create a new token with appropriate permissions
3. Copy the token to `.env`

## Step 3: Run the Collection Pipeline

Collect data from all sources:

```bash
python scripts/run_collection.py
```

This will:
- Fetch your GitHub repositories
- Get Vercel projects and deployments
- Retrieve Cloudflare Workers and resources
- Parse conversation exports (if available)
- Build the knowledge graph
- Create vector embeddings

## Step 4: Start the API Server

```bash
python scripts/run_server.py
```

The server will start at `http://localhost:8000`.

## Step 5: Query the Agent

### Option 1: Use the API directly

```bash
# Check health
curl http://localhost:8000/health

# Query the agent
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my Python skills?", "top_k": 5}'

# List skills
curl http://localhost:8000/skills?min_confidence=0.3

# List projects
curl http://localhost:8000/projects
```

### Option 2: Use the interactive docs

Open your browser and go to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Option 3: Use the test script

```bash
python scripts/test_agent.py
```

## Example Queries

Try these example queries to test the agent:

```bash
# General skills
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my main programming languages?"}'

# Specific technology
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Have I worked with React?"}'

# Project-based
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which projects use TypeScript?"}'

# Cloud experience
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What cloud platforms have I used?"}'
```

## Troubleshooting

### Import Errors

If you get import errors, ensure you've installed all dependencies:

```bash
pip install -r requirements.txt
```

### Token Errors

If collection fails due to authentication:
1. Verify tokens in `.env` are correct
2. Check token permissions (GitHub: repo scope, Vercel: read access, Cloudflare: appropriate zones)
3. Ensure tokens haven't expired

### Missing Data

If no data is collected:
1. Check that you have repositories/projects in your accounts
2. Verify the account associated with your tokens has access
3. Check the logs for specific error messages

### Port Already in Use

If port 8000 is already in use:

```bash
# Use a different port
python scripts/run_server.py --port 8001

# Or kill the process using port 8000
lsof -ti:8000 | xargs kill -9
```

## Next Steps

- Explore the API documentation at http://localhost:8000/docs
- Read the full README.md for detailed documentation
- Check IMPLEMENTATION_SUMMARY.md for architecture details
- Customize the agent by modifying `app/agent/resume_agent.py`

## Support

For issues or questions:
1. Check the README.md for detailed documentation
2. Review IMPLEMENTATION_SUMMARY.md for architecture details
3. Check the logs for error messages
