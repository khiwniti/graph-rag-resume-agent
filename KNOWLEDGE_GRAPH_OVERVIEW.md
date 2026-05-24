# Knowledge Graph Overview

> **High-level architecture guide for the Graph RAG Resume Agent**

This document provides a **bird's-eye view** of the knowledge graph system - what it does, how data flows through it, and key architectural decisions. For implementation details, see the [Setup Guide](README_KNOWLEDGE_GRAPH.md) and [design specs](docs/superpowers/specs/).

---

## 🎯 What This System Does

The Graph RAG Resume Agent builds a **structured representation of your skills and experience** from multiple data sources (GitHub, Vercel, Cloudflare, conversations), then uses that graph to answer queries with **evidence-backed responses**.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Collect    │ --> │  Normalize   │ --> │  Extract    │ --> │  Build Graph │
│  (raw data) │     │ (standardize)│     │ (skills)    │     │ (Neo4j)      │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
       │                    │                    │                    │
       v                    v                    v                    v
  GitHub repos       Unified format      Dependencies,      Nodes + Edges
  Vercel projects    across sources      source code        with evidence
  Cloudflare workers                     analysis
```

---

## 🏗️ Architecture Layers

### Layer 1: Data Collection

**Purpose:** Gather raw data from external sources

| Source    | What It Collects                          | Key File                          |
|-----------|-------------------------------------------|-----------------------------------|
| GitHub    | Repos, files, commits, PRs                | `app/collectors/github_collector.py` |
| Vercel    | Deployments, projects, environment info   | `app/collectors/vercel_collector.py` |
| Cloudflare| Workers, scripts, deployments             | `app/collectors/cloudflare_collector.py` |
| Conversations | Chat logs, decisions, context         | `app/collectors/conversation_collector.py` |

**Output:** Raw JSON data stored in `data/raw/`

---

### Layer 2: Normalization

**Purpose:** Convert source-specific data into a unified format

All collectors feed into normalizers that produce a consistent schema regardless of source. This allows the rest of the pipeline to treat GitHub, Vercel, and Cloudflare data identically.

```python
# Before normalization (GitHub-specific)
{
  "repo_name": "user/my-project",
  "git_url": "https://github.com/user/my-project",
  "commits": [...]
}

# After normalization (unified)
{
  "type": "repository",
  "id": "github:user/my-project",
  "url": "https://github.com/user/my-project",
  "artifacts": [...]
}
```

**Key file:** `app/normalizers/`

---

### Layer 3: Extraction

**Purpose:** Analyze normalized data to identify skills and dependencies

The extraction layer parses source code, configuration files, and dependencies to automatically identify:

- **Programming languages** (Python, JavaScript, etc.)
- **Frameworks** (FastAPI, React, etc.)
- **Tools & libraries** (NumPy, Docker, etc.)
- **Concepts** (RAG, knowledge graphs, etc.)

Each skill includes:
- **Confidence score** (0.0 - 1.0) based on evidence quality
- **Evidence type** (source code, dependency, config, deployment, conversation)
- **Source location** (file path, line number)

**Key files:**
- `app/extractors/skill_extractor.py` - Skill identification
- `app/extractors/dependency_parser.py` - Package analysis
- `app/extractors/source_analyzer.py` - Code structure

---

### Layer 4: Knowledge Graph

**Purpose:** Store skills, projects, and relationships in a queryable graph

The universal graph uses Neo4j with a custom schema designed for career/skill data.

#### Node Types

| Type | Description | Example ID |
|------|-------------|------------|
| `Person` | The developer(s) the graph represents | `person:me` |
| `Repository` | Code repository | `github:user/repo` |
| `File` | Source file | `file:app/main.py` |
| `Function` | Function/method | `function:main` |
| `Class` | Class definition | `class:KnowledgeGraph` |
| `Skill` | Technology or concept | `skill:python` |
| `Project` | Deployed project | `vercel:my-app` |
| `Deployment` | Specific deployment | `deployment:abc123` |
| `Document` | Documentation file | `doc:README.md` |
| `Concept` | Abstract concept | `concept:rag` |

#### Edge Types

| Type | Connects | Meaning |
|------|----------|---------|
| `DEFINES` | File → Function/Class | File contains this definition |
| `USES` | Function → Skill | Function uses this skill |
| `DEPENDS_ON` | Project → Library | Project requires this library |
| `DEPLOYS_TO` | Project → Deployment | Project deployed here |
| `DOCUMENTS` | Document → Concept | Document describes this concept |
| `HAS_SKILL` | Person → Skill | Person has this skill |
| `CALLS` | Function → Function | One function calls another |

**Key file:** `app/schema/` - Universal schema definition

---

### Layer 5: Export

**Purpose:** Write the graph to Neo4j (local or cloud)

The exporter handles:
- Batch writing nodes and edges
- Evidence attachment
- Profile-based filtering (e.g., `aura_free` for Neo4j's free tier)

```python
from app.exporters.neo4j_export import export_to_neo4j

# Export full graph (default)
export_to_neo4j(graph)

# Export filtered for Aura Free tier
export_to_neo4j(graph, profile="aura_free")
```

**Key files:**
- `app/exporters/neo4j_export.py` - Main exporter
- `DEPLOY.md` - Deployment configurations

---

### Layer 6: Query & RAG

**Purpose:** Answer questions using the graph

The RAG (Retrieval-Augmented Generation) layer combines:
1. **Graph traversal** - Find related skills/projects
2. **Vector search** - Semantic similarity on skill descriptions
3. **Evidence retrieval** - Link answers back to source code

```python
# Query the graph
response = agent.query("What are my Python skills?")

# Returns:
{
  "answer": "You have strong Python skills with evidence from...",
  "skills": ["python", "fastapi", "networkx"],
  "evidence": [
    {"source": "app/main.py:15", "type": "source_code"},
    {"source": "requirements.txt", "type": "dependency"}
  ]
}
```

**Key files:**
- `app/rag/retriever.py` - Hybrid retrieval
- `app/agent/resume_agent.py` - Main query interface

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │
│  │  GitHub  │  │  Vercel  │  │Cloudflare│  │Conversations │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘        │
└───────┼─────────────┼─────────────┼───────────────┼─────────────────┘
        │             │             │               │
        └─────────────┴─────────────┴───────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │     app/collectors/                 │
        │  - github_collector.py              │
        │  - vercel_collector.py              │
        │  - cloudflare_collector.py          │
        │  - conversation_collector.py        │
        └──────────────────┬──────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │     app/normalizers/                │
        │  - Normalize to unified schema      │
        └──────────────────┬──────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │     app/extractors/                 │
        │  - skill_extractor.py               │
        │  - dependency_parser.py             │
        │  - source_analyzer.py               │
        └──────────────────┬──────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │     app/graph/                      │
        │  - builder.py (UniversalGraph)      │
        └──────────────────┬──────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │     app/exporters/                  │
        │  - neo4j_export.py                  │
        │  - profile: "full" | "aura_free"    │
        └──────────────────┬──────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Neo4j DB   │
                    │ (local or   │
                    │  Aura Free) │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   FastAPI    │
                    │   /query     │
                    └──────────────┘
```

---

## 🔑 Key Design Decisions

### 1. Evidence-Based Skills

Skills are **not manually entered** - they're extracted from actual code, dependencies, and configurations. Every skill claim links back to concrete evidence.

**Why:** Prevents resume padding, provides verifiable claims

### 2. Confidence Scoring

Each skill has a confidence score (0.0-1.0) based on:

| Evidence Type      | Weight |
|--------------------|--------|
| Source code        | 1.0    |
| Dependencies       | 0.7    |
| Config files       | 0.6    |
| Deployments        | 0.5    |
| Conversations      | 0.3    |

**Why:** Distinguishes between "used in production" and "mentioned in chat"

### 3. Universal Graph Schema

All data sources speak the same schema - no translation needed during queries.

**Why:** Simplifies queries, enables cross-source reasoning

### 4. Profile-Based Export

The `profile` argument lets you export different subsets:
- `full` - Everything (local Neo4j)
- `aura_free` - Filtered for Neo4j's free tier (200K nodes, 400K edges)

**Why:** Same codebase works for local dev and cloud deployment

---

## 📦 Key Directories

| Directory | Purpose |
|-----------|---------|
| `app/schema/` | Universal graph types (nodes, edges, evidence) |
| `app/collectors/` | Data collection from sources |
| `app/normalizers/` | Normalize source data to unified format |
| `app/extractors/` | Skill and dependency extraction |
| `app/graph/` | Graph construction (NetworkX) |
| `app/exporters/` | Export to Neo4j |
| `app/rag/` | Retrieval and RAG logic |
| `app/agent/` | Resume agent interface |
| `scripts/` | CLI tools and utilities |
| `data/` | Stored graph, vectors, and raw data |

---

## 🚀 Getting Started

### Minimal Setup (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Neo4j (Docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community

# 3. Set environment
cp .env.example .env
# Edit .env with your tokens

# 4. Build the graph
python scripts/build_universal_graph.py

# 5. Query it
python scripts/query_agent.py "What are my Python skills?"
```

### Test Without Neo4j

You can test extraction without a database:

```bash
python scripts/test_extraction.py
```

---

## 🔍 Common Queries

### Find all skills for a person
```cypher
MATCH (p:Person {id: "me"})-[:HAS_SKILL]->(s:Skill)
RETURN s.name, s.category, s.confidence
ORDER BY s.confidence DESC;
```

### Find projects using a specific skill
```cypher
MATCH (p:Project)-[:REQUIRES_SKILL]->(s:Skill {name: "python"})
RETURN p.name, p.url;
```

### Find related skills
```cypher
MATCH (me:Person {id: "me"})-[:HAS_SKILL]->(s:Skill)
<-[:REQUIRES_SKILL]-(proj:Project)
-[:REQUIRES_SKILL]->(related:Skill)
RETURN related.name, count(*) as frequency
ORDER BY frequency DESC;
```

---

## 📚 Further Reading

- [Setup Guide](README_KNOWLEDGE_GRAPH.md) - Step-by-step setup
- [Aura Free Design](docs/superpowers/specs/2026-05-24-aura-free-export-profile-design.md) - Cloud deployment filtering
- [DEPLOY.md](DEPLOY.md) - Production deployment guide
- [Universal Graph Plan](plans/KNOWLEDGE_GRAPH_REDESIGN.md) - Architecture details

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused | Check Neo4j is running: `docker ps \| grep neo4j` |
| No skills found | Verify tokens in `.env` are valid |
| Graph too large for Aura Free | Use `profile="aura_free"` in export |
| Slow queries | Add indexes: `CREATE INDEX ON :Skill(name)` |

---

**Last updated:** 2026-05-24  
**Version:** 2.0 (Universal Graph Schema)
