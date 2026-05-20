# Metadata Extraction Guide

## Overview

This guide explains how to extract hiring-manager-focused metadata from your GitHub, Vercel, and Cloudflare sources. The extracted metadata reduces knowledge graph size by **~90%** while preserving all the signal that matters for AI agent orchestration and portfolio display.

## Why Metadata Extraction?

**Without metadata extraction:**
- Store every file from every repo
- Store every npm package dependency
- Store every API endpoint
- Result: Thousands of nodes, slow queries, noisy graph

**With metadata extraction:**
- Store project identity, purpose, architecture patterns
- Store demonstrated skills (inferred from tech stack)
- Store evidence counts (not full file content)
- Result: ~240 nodes, fast queries, clean signal

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ RAW DATA SOURCES                                            │
│ github.json  │ vercel.json │ cloudflare.json                │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ Step 1: Extract Metadata
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ EXTRACTED METADATA (data/metadata/extracted_metadata.json) │
│ - 213 projects                                              │
│ - Each project has: name, domain, stack, skills, evidence  │
│ - ~90% size reduction vs. raw files                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ Step 2: Build Graph
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ KNOWLEDGE GRAPH (data/graph/knowledge_graph.json)          │
│ - 240 nodes (projects, skills, domains, tech, platforms)   │
│ - 1,480 edges (relationships)                               │
│ - Ready for MCP UI + AI agent queries                       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Step 1: Extract Metadata

```bash
cd /teamspace/studios/this_studio/graph-rag-resume-agent
python app/extractors/metadata_extractor.py
```

**Output:**
```
✓ Extracted from Vercel: 22 projects
✓ Extracted from Cloudflare: 51 workers
✓ Extracted from GitHub: 140 repos
✓ Extracted metadata for 213 projects to data/metadata/extracted_metadata.json

=== Metadata Extraction Summary ===
Total projects: 213
 - Vercel: 22
 - Cloudflare: 51
 - GitHub: 140

Graph size reduction: ~90%+ (metadata nodes only, no file-level nodes)
```

### Step 2: Build Knowledge Graph

```bash
python scripts/build_graph_from_metadata.py
```

**Output:**
```
✓ Knowledge graph built successfully!

Nodes: 240
  - Projects: 213
  - Skills: 11
  - Domains: 10
  - Tech: 8
  - Platforms: 3

Edges: 1480
Output: data/graph/knowledge_graph.json
```

## Metadata Schema

Each project in `extracted_metadata.json` has this structure:

```json
{
  "name": "BiteBase Intelligence",
  "source_type": "github",
  "project_type": "fullstack",
  "domain": ["geospatial", "analytics", "ai"],
  "problem_statement": "Restaurant owners need location-based insights...",
  "architecture_pattern": "SSR/SSG",
  "primary_stack": ["Next.js", "FastAPI", "PostgreSQL"],
  "skills_demonstrated": ["React", "Python", "Geospatial Analysis"],
  "evidence_count": 47,
  "confidence": 0.92,
  "source_url": "https://github.com/...",
  "deployed_url": "https://..."
}
```

### Field Descriptions

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Project name | "BiteBase Intelligence" |
| `source_type` | Where data came from | "github", "vercel", "cloudflare" |
| `project_type` | Type of project | "frontend", "backend", "fullstack", "worker" |
| `domain` | Business domain(s) | ["geospatial", "analytics"] |
| `problem_statement` | What problem it solves | "Restaurant owners need..." |
| `architecture_pattern` | Architectural style | "SSR/SSG", "SPA", "Edge Function" |
| `primary_stack` | Core technologies | ["Next.js", "FastAPI"] |
| `skills_demonstrated` | Skills this proves | ["React", "Python"] |
| `evidence_count` | Number of files/artifacts | 47 |
| `confidence` | Confidence in metadata | 0.92 |
| `source_url` | Link to source | GitHub repo URL |
| `deployed_url` | Live deployment URL | Vercel/Cloudflare URL |

## Inference Rules

### Domain Inference
The system infers domains from project names and descriptions:

| Keywords | Inferred Domain |
|----------|-----------------|
| "dashboard", "analytics", "metrics" | dashboard |
| "geo", "map", "location" | geo |
| "intelligence", "insights" | intelligence |
| "agent", "autonomous" | agent |
| "portfolio", "showcase" | portfolio |
| "api", "backend", "service" | api |
| "security", "auth" | security |
| "simulation", "modeling" | simulation |
| "chat", "messaging" | chat |
| "crm", "customer" | crm |

### Skill Inference
Skills are inferred from tech stack:

| Tech Pattern | Inferred Skills |
|--------------|-----------------|
| "nextjs" | React, Next.js, SSR/SSG |
| "fastapi" | FastAPI, Python Backend |
| "cloudflare" | Cloudflare Workers, Edge Computing |
| "faiss" | Vector Search, RAG |
| "agent" | AI Agents, Autonomous Systems |

## Knowledge Graph Structure

The built graph has these node types:

1. **person** - You (the portfolio owner)
2. **project** - Each project from metadata
3. **skill** - Inferred skills demonstrated
4. **domain** - Business domains
5. **tech** - Technology stack items
6. **platform** - Deployment platforms

### Edge Types

| Edge Label | From → To | Meaning |
|------------|-----------|---------|
| `DEMONSTRATES_SKILL` | Project → Skill | Project demonstrates this skill |
| `EVIDENCE_FOR` | Skill → Project | Skill is evidenced by this project |
| `USES_TECH` | Project → Tech | Project uses this technology |
| `BELONGS_TO_DOMAIN` | Project → Domain | Project belongs to this domain |
| `DEPLOYED_ON` | Project → Platform | Project is deployed on this platform |
| `CREATED` | Person → Project | Person created this project |

## Integration with MCP UI

The extracted metadata powers the MCP UI knowledge graph:

```typescript
// MCP UI queries the knowledge graph
const result = await query_knowledge_graph({ 
  node_type: "skill" 
});

// Returns all skills with evidence-backed projects
console.log(result.nodes); // Skill nodes
console.log(result.edges); // Skill → Project relationships
```

### Example: Agent Queries Graph

When the "Summary Expert" agent rewrites your resume summary:

1. Agent queries: `query_knowledge_graph({ node_type: "skill" })`
2. Graph returns: All 11 skills with connected projects
3. Agent uses top skills by confidence to craft summary
4. Evidence links back to actual repos/deployments

## Customization

### Add Custom Domain Keywords

Edit `app/extractors/metadata_extractor.py`:

```python
DOMAIN_KEYWORDS = {
    "my_domain": ["keyword1", "keyword2"],
    # ... existing domains
}
```

### Add Custom Skill Rules

```python
SKILL_RULES = {
    "my_framework": ["MyFramework", "Advanced Skill"],
    # ... existing rules
}
```

## Troubleshooting

### "Metadata not found"
Run the extraction script first:
```bash
python app/extractors/metadata_extractor.py
```

### "Graph build failed"
Check that metadata exists:
```bash
ls -la data/metadata/
```

### Graph is too large
If you still have too many nodes, increase abstraction:
- Merge similar domains
- Group tech into categories (e.g., "Frontend Framework" instead of "React", "Vue", "Svelte")
- Increase minimum confidence threshold

## Next Steps

After metadata extraction:
1. ✅ Metadata extracted
2. ✅ Knowledge graph built
3. ⏭️ Deploy to Hugging Face Spaces
4. ⏭️ Connect to MCP UI for AI agent orchestration
