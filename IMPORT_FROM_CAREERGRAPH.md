# Importing Data from CareerGraph Wiki MCP UI

This guide explains how to import data from the **CareerGraph Wiki MCP UI** knowledge graph into the **Graph RAG Resume Agent**.

## Overview

Instead of collecting data directly from GitHub, Vercel, and Cloudflare APIs, you can use the already-synced data in CareerGraph Wiki MCP UI. This approach:

- ✅ Reuses existing API tokens and sync configurations
- ✅ Avoids rate limiting from multiple API calls
- ✅ Ensures consistency across both systems
- ✅ Provides additional context from wiki pages

## Architecture

```
careergraph-wiki-mcp-ui                    graph-rag-resume-agent
─────────────────────                     ──────────────────────
Wiki Pages (markdown)  ──┐
                         │
Graph Nodes/Edges ──────┼──> Export Script ──> JSON ──> Import Script ──> Raw Data
                         │
API Endpoints    ───────┘
```

## Step-by-Step Guide

### Step 1: Export Data from CareerGraph

```bash
cd /teamspace/studios/this_studio/careergraph-wiki-mcp-ui

# Export wiki pages and graph data
python apps/api/scripts/export_wiki_data.py \
  --output ../graph-rag-resume-agent/data/careergraph_export.json \
  --wiki-root ./wiki \
  --api-base http://localhost:8000/api \
  --export-graph
```

**Options:**
- `--output`: Output file path (default: `exported_wiki_data.json`)
- `--wiki-root`: Wiki root directory
- `--api-base`: API base URL
- `--export-graph`: Also export graph data from API

### Step 2: Pre-process Data (Optional)

Before importing, you can filter, validate, and enrich the data:

```bash
cd /teamspace/studios/this_studio/graph-rag-resume-agent

# Pre-process with all options
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --filter-types repo vercel_project cloudflare_worker \
  --validate \
  --enrich \
  --deduplicate \
  --preview-skills
```

**Preprocessing Options:**

| Option | Description |
|--------|-------------|
| `--filter-types` | Filter by page types (e.g., `repo`, `vercel_project`) |
| `--filter-tags` | Filter by tags |
| `--min-confidence` | Minimum confidence threshold (0.0-1.0) |
| `--validate` | Validate data integrity |
| `--enrich` | Enrich metadata with skill detection |
| `--deduplicate` | Remove duplicate entries |
| `--preview-skills` | Show detected skills preview |

### Step 3: Import into Graph RAG

```bash
python scripts/import_from_careergraph.py \
  --input data/processed_data.json \
  --output-dir data/raw
```

This transforms the CareerGraph format into the format expected by the Graph RAG pipeline.

### Step 4: Build the Knowledge Graph

```bash
python scripts/build_graph.py
```

### Step 5: Verify and Query

```bash
# Start the API server
python scripts/run_server.py

# Test query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my Python skills?", "top_k": 5}'
```

## Data Flow

### 1. Export Format (CareerGraph → JSON)

```json
{
  "wiki_pages": {
    "pages": [
      {
        "slug": "repos/username/repo-name",
        "title": "Repo Name",
        "type": "github_repo",
        "tags": ["python", "fastapi"],
        "content": "...",
        "metadata": {
          "full_name": "username/repo-name",
          "language": "Python",
          "stars": 42,
          "description": "..."
        }
      }
    ]
  },
  "repos": {
    "repositories": [...]
  },
  "graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### 2. Raw Data Format (After Import)

```json
// data/raw/github.json
{
  "repositories": [
    {
      "full_name": "username/repo-name",
      "name": "repo-name",
      "description": "...",
      "language": "Python",
      "stargazers_count": 42,
      "files": []
    }
  ]
}

// data/raw/vercel.json
{
  "projects": [...]
}

// data/raw/cloudflare.json
{
  "workers": [...],
  "zones": [...]
}

// data/raw/conversation.json
{
  "artifacts": [...]
}
```

## Type Mappings

| CareerGraph Type | Graph RAG Type | Description |
|-----------------|----------------|-------------|
| `github_repo` | Repository | GitHub repository |
| `vercel_project` | Project | Vercel deployment |
| `cloudflare_worker` | Worker | Cloudflare Worker |
| `cloudflare_zone` | Zone | Cloudflare Zone |
| `page` | Artifact | Generic wiki page |

## Advanced Usage

### Filter by Date Range

```bash
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --after "2025-01-01T00:00:00Z" \
  --before "2026-05-20T23:59:59Z"
```

### Filter by Tags

```bash
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --filter-tags python react nextjs \
  --match-all
```

### Custom Confidence Threshold

```bash
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --min-confidence 0.7
```

## Troubleshooting

### Issue: No data exported

**Solution:** Ensure the CareerGraph Wiki MCP UI has synced data:
```bash
# Check synced pages
curl http://localhost:8000/api/pages

# If empty, run sync
curl -X POST http://localhost:8000/api/sync/github
curl -X POST http://localhost:8000/api/sync/vercel
curl -X POST http://localhost:8000/api/sync/cloudflare
```

### Issue: Type mismatch errors

**Solution:** Check the type mappings above. You may need to adjust the type filtering:
```bash
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --filter-types github_repo vercel_project cloudflare_worker
```

### Issue: Skills not detected

**Solution:** Enable metadata enrichment:
```bash
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --enrich \
  --preview-skills
```

## Script Reference

### export_wiki_data.py

Exports data from CareerGraph Wiki MCP UI.

```bash
python apps/api/scripts/export_wiki_data.py [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | str | `exported_wiki_data.json` | Output file path |
| `--wiki-root` | str | `./wiki` | Wiki root directory |
| `--api-base` | str | `http://localhost:8000/api` | API base URL |
| `--export-graph` | flag | False | Export graph data |

### preprocess_careergraph_data.py

Pre-processes exported data with filtering and enrichment.

```bash
python scripts/preprocess_careergraph_data.py [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input` | str | Required | Input file path |
| `--output` | str | Required | Output file path |
| `--filter-types` | list | None | Filter by types |
| `--filter-tags` | list | None | Filter by tags |
| `--min-confidence` | float | 0.0 | Min confidence |
| `--validate` | flag | False | Validate integrity |
| `--enrich` | flag | False | Enrich metadata |
| `--deduplicate` | flag | False | Remove duplicates |
| `--preview-skills` | flag | False | Preview skills |

### import_from_careergraph.py

Imports processed data into Graph RAG format.

```bash
python scripts/import_from_careergraph.py [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input` | str | Required | Input file path |
| `--output-dir` | str | `data/raw` | Output directory |
| `--filter-types` | list | None | Filter by types |
| `--min-confidence` | float | 0.0 | Min confidence |

## Example: Complete Workflow

```bash
# 1. Export from CareerGraph
cd /teamspace/studios/this_studio/careergraph-wiki-mcp-ui
python apps/api/scripts/export_wiki_data.py \
  --output ../graph-rag-resume-agent/data/careergraph_export.json \
  --export-graph

# 2. Pre-process with enrichment
cd ../graph-rag-resume-agent
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --validate \
  --enrich \
  --deduplicate \
  --preview-skills

# 3. Import into raw format
python scripts/import_from_careergraph.py \
  --input data/processed_data.json \
  --output-dir data/raw

# 4. Build graph
python scripts/build_graph.py

# 5. Start server and test
python scripts/run_server.py

# 6. Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What backend skills do I have?", "top_k": 5}'
```

## Benefits of This Approach

1. **Single Source of Truth**: All data synced once in CareerGraph
2. **Consistent Data**: Same data across wiki and RAG agent
3. **Efficient**: No duplicate API calls or rate limiting
4. **Flexible**: Filter and transform before ingestion
5. **Validated**: Data integrity checks before import
