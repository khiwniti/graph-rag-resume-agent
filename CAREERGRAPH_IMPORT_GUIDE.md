# CareerGraph Wiki MCP UI Integration Guide

## Overview

This guide explains how to use data from **CareerGraph Wiki MCP UI** as the data source for **Graph RAG Resume Agent**, eliminating the need for separate API integrations.

## Why Use CareerGraph as Data Source?

The **careergraph-wiki-mcp-ui** project already syncs data from:
- GitHub (repositories, code)
- Vercel (projects, deployments)
- Cloudflare (workers, zones, resources)

Instead of configuring separate API tokens and running duplicate syncs, you can import the already-synced wiki data directly into Graph RAG.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   CareerGraph Wiki MCP UI                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  GitHub     │  │  Vercel     │  │  Cloudflare │              │
│  │  Sync       │  │  Sync       │  │  Sync       │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                       │
│         └────────────────┼────────────────┘                       │
│                          │                                        │
│                   ┌──────▼──────┐                                 │
│                   │  Wiki Pages │                                │
│                   │  (Markdown) │                                │
│                   └──────┬──────┘                                │
│                          │                                        │
│                   ┌──────▼──────┐                                │
│                   │  Graph API  │                                │
│                   └──────┬──────┘                                │
└──────────────────────────┼────────────────────────────────────────┘
                           │
                    1. Export Script
                           │
                           ▼
                    ┌──────────────┐
                    │  JSON Export │
                    └──────┬───────┘
                           │
                    2. Pre-process
                           │
                           ▼
                    ┌──────────────┐
                    │  Filtered &  │
                    │  Enriched    │
                    └──────┬───────┘
                           │
                    3. Import Script
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Graph RAG Resume Agent                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Raw Data    │  │  Graph       │  │  Vector      │           │
│  │  (JSON)      │──│  Builder     │──│  Store       │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                             │                     │
│                                      ┌──────▼──────┐             │
│                                      │  RAG Agent  │             │
│                                      └─────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Step 1: Export from CareerGraph

```bash
cd /teamspace/studios/this_studio/careergraph-wiki-mcp-ui

# Export wiki pages to JSON
python apps/api/scripts/export_wiki_data.py \
  --output ../graph-rag-resume-agent/data/careergraph_export.json \
  --wiki-root ./wiki
```

### Step 2: Pre-process (Optional but Recommended)

```bash
cd /teamspace/studios/this_studio/graph-rag-resume-agent

# Pre-process with validation and enrichment
python scripts/preprocess_careergraph_data.py \
  --input data/careergraph_export.json \
  --output data/processed_data.json \
  --validate \
  --enrich \
  --deduplicate \
  --preview-skills
```

### Step 3: Import into Graph RAG

```bash
python scripts/import_from_careergraph.py \
  --input data/processed_data.json \
  --output-dir data/raw
```

### Step 4: Build Graph and Query

```bash
# Build the knowledge graph
python scripts/build_graph.py

# Start API server
python scripts/run_server.py

# Query your skills
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my Python skills?", "top_k": 5}'
```

## Scripts Reference

### 1. Export Script (`export_wiki_data.py`)

Exports wiki pages and graph data from CareerGraph.

**Location:** `/teamspace/studios/this_studio/careergraph-wiki-mcp-ui/apps/api/scripts/export_wiki_data.py`

**Options:**
- `--output`: Output file path (default: `exported_wiki_data.json`)
- `--wiki-root`: Wiki root directory (default: current wiki folder)
- `--api-base`: API base URL (default: `http://localhost:8000/api`)
- `--export-graph`: Also export graph data from API endpoint

**Example:**
```bash
python apps/api/scripts/export_wiki_data.py \
  --output data/careergraph_export.json \
  --wiki-root /path/to/wiki \
  --export-graph
```

### 2. Pre-process Script (`preprocess_careergraph_data.py`)

Filters, validates, and enriches exported data.

**Location:** `/teamspace/studios/this_studio/graph-rag-resume-agent/scripts/preprocess_careergraph_data.py`

**Options:**
- `--input`: Input file path (required)
- `--output`: Output file path (required)
- `--filter-types`: Filter by page types (e.g., `github_repo`, `vercel_project`)
- `--filter-tags`: Filter by tags (e.g., `python`, `react`)
- `--min-confidence`: Minimum confidence threshold (0.0-1.0)
- `--validate`: Validate data integrity
- `--enrich`: Enrich metadata with skill detection
- `--deduplicate`: Remove duplicate entries
- `--preview-skills`: Show detected skills preview

**Example:**
```bash
python scripts/preprocess_careergraph_data.py \
  --input data/export.json \
  --output data/processed.json \
  --filter-types github_repo vercel_project \
  --min-confidence 0.5 \
  --enrich \
  --preview-skills
```

### 3. Import Script (`import_from_careergraph.py`)

Transforms CareerGraph format to Graph RAG raw data format.

**Location:** `/teamspace/studios/this_studio/graph-rag-resume-agent/scripts/import_from_careergraph.py`

**Options:**
- `--input`: Input file path (required)
- `--output-dir`: Output directory for raw data (default: `data/raw`)
- `--filter-types`: Additional type filtering during import
- `--min-confidence`: Additional confidence filtering

**Example:**
```bash
python scripts/import_from_careergraph.py \
  --input data/processed.json \
  --output-dir data/raw
```

## Data Mappings

| CareerGraph Type | Graph RAG Format | Description |
|-----------------|------------------|-------------|
| `github_repo` | Repository | GitHub repository with metadata |
| `vercel_project` | Project | Vercel deployment |
| `cloudflare_worker` | Worker | Cloudflare Worker |
| `cloudflare_zone` | Zone | Cloudflare Zone |
| `page` | Artifact | Generic wiki page/artifact |

## Pre-processing Options

### Filter by Type

Only import specific types of pages:

```bash
python scripts/preprocess_careergraph_data.py \
  --input data/export.json \
  --output data/processed.json \
  --filter-types github_repo vercel_project cloudflare_worker
```

### Filter by Tags

Only import pages with specific tags:

```bash
python scripts/preprocess_careergraph_data.py \
  --input data/export.json \
  --output data/processed.json \
  --filter-tags python fastapi react nextjs
```

### Confidence Threshold

Filter by minimum confidence score:

```bash
python scripts/preprocess_careergraph_data.py \
  --input data/export.json \
  --output data/processed.json \
  --min-confidence 0.7
```

### Enrichment

The `--enrich` option adds:
- Word count
- Detected skill keywords
- Skill categories
- Confidence scores based on content quality

```bash
python scripts/preprocess_careergraph_data.py \
  --input data/export.json \
  --output data/processed.json \
  --enrich
```

## Workflow Examples

### Basic Workflow (All Data)

```bash
# 1. Export
python apps/api/scripts/export_wiki_data.py --output data/export.json

# 2. Import (skip preprocessing for full data)
python scripts/import_from_careergraph.py \
  --input data/export.json \
  --output-dir data/raw

# 3. Build graph
python scripts/build_graph.py
```

### Filtered Workflow (Specific Types Only)

```bash
# 1. Export
python apps/api/scripts/export_wiki_data.py --output data/export.json

# 2. Pre-process with filters
python scripts/preprocess_careergraph_data.py \
  --input data/export.json \
  --output data/processed.json \
  --filter-types github_repo vercel_project \
  --enrich

# 3. Import
python scripts/import_from_careergraph.py \
  --input data/processed.json \
  --output-dir data/raw

# 4. Build graph
python scripts/build_graph.py
```

### Preview Skills Before Import

```bash
# 1. Export
python apps/api/scripts/export_wiki_data.py --output data/export.json

# 2. Preview skills
python scripts/preprocess_careergraph_data.py \
  --input data/export.json \
  --output data/preview.json \
  --enrich \
  --preview-skills
```

## Troubleshooting

### Export shows 0 pages

**Solution:** Check that wiki pages exist:
```bash
ls -la /teamspace/studios/this_studio/careergraph-wiki-mcp-ui/wiki/**/*.md
```

### Import fails with format error

**Solution:** Ensure you're using the preprocessed output, not the raw export.

### Skills not detected

**Solution:** Use `--enrich` flag during preprocessing to detect skills from content.

## Benefits

1. **Single Sync Point**: Configure GitHub/Vercel/Cloudflare sync once in CareerGraph
2. **Consistent Data**: Same data source for wiki and RAG agent
3. **No Duplicate API Calls**: Avoid rate limiting
4. **Flexible Filtering**: Filter by type, tags, confidence before import
5. **Enrichment**: Automatic skill detection and confidence scoring

## Advanced: Custom Transformations

You can modify the preprocessing script to add custom transformations:

```python
# Add to preprocess_careergraph_data.py

def custom_transform(self):
    """Custom transformation logic."""
    pages = self.data.get('wiki_pages', {}).get('pages', [])
    
    for page in pages:
        # Your custom logic here
        if page.get('type') == 'github_repo':
            page['metadata']['custom_field'] = 'custom_value'
    
    return self
```

## Next Steps

After importing and building the graph:

1. **Start the API server**: `python scripts/run_server.py`
2. **Test queries**: Use curl or the Swagger UI at `http://localhost:8000/docs`
3. **Build embeddings**: `python scripts/build_embeddings.py`
4. **Query with RAG**: Combine graph traversal with vector search

For detailed API documentation, see the [README.md](README.md) or visit `/docs` after starting the server.
