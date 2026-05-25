# Knowledge Graph Redesign — Career Second Brain

**Goal**: turn this repo into a *professional, universal* knowledge graph that
fully represents the user's career path across every artifact (code, commits,
docs, conversations, deployments) — and emits it in shapes that the downstream
MCP UI consumers (`careergraph-wiki-mcp-ui` → `khiw.dev` portfolio via MCP)
can render dynamically.

This is the spec. All future work in this repo should align with it.

---

## 1. Why previous attempts missed

| Symptom                                              | Root cause                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| One repo collapsed to one node, fed by README only   | No multi-evidence extraction, no first-class File/Module/Commit/Doc nodes                   |
| Skills extracted by keyword regex in README          | No LLM concept extraction, no entity resolution across sources                              |
| Graph only lived in Neo4j or a private NetworkX dump | No **integration contract** with the MCP UI consumer                                        |
| Each rewrite added new extractor classes             | No universal schema — every component invented its own node/edge vocab                      |
| Conversation/Vercel/Cloudflare collectors siloed     | Sources never linked to repos, skills never linked to deployments                           |

**Fix**: a single universal schema + two stable integration outputs (graph JSON
and a markdown vault) + multi-evidence LLM-augmented extraction.

---

## 2. Integration contracts (the consumers we serve)

### 2a. `careergraph-wiki-mcp-ui` GraphConnector
Reads `data/graph/knowledge_graph.json`:

```json
{
  "nodes": [
    {"id": "...", "type": "...", "properties": {"name": "...", "confidence": 0.9, ...}}
  ],
  "edges": [
    {"from": "...", "to": "...", "type": "..."}
  ]
}
```

### 2b. Wiki app (Obsidian-style markdown vault)
Reads `wiki/{skills,projects,repos,vercel,cloudflare,career,docs,concepts}/<slug>.md`:

```markdown
---
title: <Human readable title>
type: skill | project | repo | vercel_project | cloudflare_worker | career | profile | doc | concept | conversation | commit | person
slug: <url-safe id>
tags: [tag1, tag2]
provider: github | vercel | cloudflare | manual | conversation
created: 2024-01-15
updated: 2026-05-23
synced_at: 2026-05-23T16:30:00
confidence: 0.87
career_value: 0.9
---

# Title

<rich body with [[wikilinks]] to other pages>

## Evidence
- [[repos/my-repo]] — `src/foo.py:42` (source_code, 1.0)
- [[skills/python]] — `requirements.txt` (dependency, 0.7)
```

### 2c. Universal MCP context endpoint
A FastAPI route that, given a query or a node id, returns a **subgraph**
sized for one MCP UI section: nodes, edges, plus optional rendered markdown
snippets — so the frontend can pick the right component (skill card, repo
deep-dive, timeline, etc.) without re-querying.

---

## 3. Universal schema

### 3.1 Node types

| Domain           | Type                | Purpose                                                                |
| ---------------- | ------------------- | ---------------------------------------------------------------------- |
| Identity         | `Person`            | The user (and notable collaborators)                                   |
| Identity         | `Organization`      | Companies, orgs, teams                                                 |
| Project surface  | `Project`           | Logical project (may span repos + deployments)                         |
| Project surface  | `Repo`              | A git repository                                                       |
| Project surface  | `Deployment`        | Vercel/Cloudflare/etc deployment instance                              |
| Project surface  | `Domain`            | DNS domain                                                             |
| Project surface  | `Route`             | URL route / endpoint                                                   |
| Code             | `File`              | Source file (path within a repo)                                       |
| Code             | `Module`            | Logical module / package                                               |
| Code             | `Class`             | OO class                                                               |
| Code             | `Function`          | Function / method                                                      |
| VCS history      | `Commit`            | A git commit                                                           |
| VCS history      | `PullRequest`       | A merged or open PR                                                    |
| VCS history      | `Issue`             | An issue                                                               |
| VCS history      | `Branch`            | A branch                                                               |
| VCS history      | `Release`           | A tagged release                                                       |
| Documents        | `Document`          | A README, blog post, plan, design doc                                  |
| Documents        | `Section`           | A heading-bounded chunk of a document                                  |
| Conversation     | `Conversation`      | A chat / agent transcript                                              |
| Conversation     | `Artifact`          | An output produced inside a conversation (e.g. design doc, code patch) |
| Knowledge        | `Skill`             | A demonstrable skill (e.g. "Distributed Systems")                      |
| Knowledge        | `Technology`        | A specific tech (e.g. "FastAPI", "Neo4j", "PyTorch")                   |
| Knowledge        | `Concept`           | A domain concept ("Vector DB", "RAG", "Graph traversal")               |
| Knowledge        | `Methodology`       | A practice ("TDD", "Agile", "GitOps")                                  |
| Knowledge        | `KnowledgeDomain`   | Broad area ("AI/ML", "Web", "DevOps") — the Domain enum                |
| Time             | `TimelineEvent`     | A dated career event (joined org, shipped feature, etc.)               |
| Time             | `CareerPhase`       | A multi-month phase (a job, a focus area, an internship)               |

### 3.2 Edge types

| Group       | Edge                  | Direction & meaning                              |
| ----------- | --------------------- | ------------------------------------------------ |
| Authorship  | `AUTHORED`            | Person → (Repo, Commit, PR, Document, Artifact)  |
| Authorship  | `CONTRIBUTED_TO`      | Person → (Repo, Project)                         |
| Authorship  | `OWNS`                | Person → (Project, Repo, Deployment)             |
| Composition | `CONTAINS`            | Repo → File, Project → Repo, Doc → Section, …    |
| Composition | `HAS_MEMBER`          | Class → Function, Module → Class                 |
| Code        | `IMPORTS`             | File → Module/File                               |
| Code        | `CALLS`               | Function → Function                              |
| Code        | `INHERITS`            | Class → Class                                    |
| Code        | `DEFINES`             | File → (Class, Function)                         |
| VCS         | `MODIFIES`            | Commit → File                                    |
| VCS         | `MERGED_VIA`          | Commit ↔ PullRequest                             |
| VCS         | `CLOSED_BY`           | Issue → PullRequest / Commit                     |
| Knowledge   | `USES`                | (Repo, Project, File) → Technology               |
| Knowledge   | `IMPLEMENTS`          | (Project, File, Function) → Concept              |
| Knowledge   | `EVIDENCES`           | (File, Commit, Document, Conversation) → Skill   |
| Knowledge   | `BELONGS_TO_DOMAIN`   | (Skill, Technology, Project) → KnowledgeDomain   |
| Knowledge   | `RELATED_TO`          | symmetric similarity / co-occurrence             |
| Hosting     | `DEPLOYS_TO`          | Repo / Project → Deployment                      |
| Hosting     | `SERVES`              | Deployment → Domain / Route                      |
| Hosting     | `CONFIGURED_BY`       | Deployment → File (e.g. `vercel.json`)           |
| Docs        | `DOCUMENTS`           | Document / Section → (Repo, Project, Function)   |
| Docs        | `MENTIONS`            | (Document, Section, Conversation) → any node     |
| Docs        | `LINKS_TO`            | Section → Section (wikilink, asymmetric)         |
| Time        | `OCCURRED_DURING`     | (Commit, PR, Release) → CareerPhase              |
| Time        | `PRECEDES`            | TimelineEvent → TimelineEvent                    |
| Time        | `EVOLVED_INTO`        | Project → Project (refactors, rewrites)          |
| Tagging     | `TAGGED_WITH`         | any → tag-as-Concept                             |

All edges have `weight: float` and `evidence: [evidence_id, ...]` attributes
so we can re-derive confidence at query time.

### 3.3 Evidence model
Evidence is **first-class** so claims are auditable.

```python
Evidence(
    id: str,                    # stable hash
    evidence_type: enum,        # SOURCE_CODE | DEPENDENCY | CONFIG | DEPLOYMENT |
                                # COMMIT_MSG | PR_BODY | DOC | CONVERSATION | LLM_INFERENCE
    source_node_id: str,        # which graph node produced it
    locator: str,               # path:line, commit sha, doc#section, etc.
    excerpt: str,               # quoted text
    confidence: float,          # 0..1 weight for this single piece
    extracted_at: datetime,
)
```

Edges store a list of evidence ids. Skill confidence = aggregation function
over edge evidences (default: `1 - prod(1 - w_i)`).

### 3.4 Identity & slugging
Every node has a stable, deterministic `id` and `slug`:

| Type              | id pattern                                  | slug pattern                                |
| ----------------- | ------------------------------------------- | ------------------------------------------- |
| Repo              | `repo:{owner}/{name}`                       | `repos/{owner}--{name}`                     |
| File              | `file:{repo}/{path}@{rev}`                  | n/a (not surfaced as wiki page by default)  |
| Function          | `fn:{repo}/{path}::{qualname}`              | n/a                                         |
| Skill             | `skill:{canonical-name}`                    | `skills/{canonical-name}`                   |
| Technology        | `tech:{canonical-name}`                     | `skills/{canonical-name}` (alias)           |
| Concept           | `concept:{canonical-name}`                  | `concepts/{canonical-name}`                 |
| Deployment        | `dep:{provider}/{project}/{id}`             | `{provider}/{project}`                      |
| Document          | `doc:{repo}/{path}`                         | `docs/{repo}--{path-slug}`                  |
| Commit            | `commit:{repo}@{sha[:10]}`                  | n/a                                         |
| Conversation      | `conv:{provider}/{id}`                      | `conversations/{slug}`                      |
| Person            | `person:{login or email-hash}`              | `career/{login}`                            |

Entity resolution: skills/technologies/concepts go through a canonicalizer
(lowercased, stop-stripped, alias-mapped via `data/canonical/aliases.json`)
so "FastAPI", "fastapi", "fast-api" merge to one node.

---

## 4. Pipeline architecture (revised)

```
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐    ┌────────────┐
│  Collectors  │ →  │   Extractors   │ →  │  Graph Builder  │ →  │  Exporters │
│ github,      │    │ AST, deps,     │    │ universal       │    │ JSON,      │
│ vercel,      │    │ deploy, doc,   │    │ schema, entity  │    │ wiki vault,│
│ cloudflare,  │    │ git-history,   │    │ resolution,     │    │ Neo4j,     │
│ conversation │    │ LLM concept    │    │ confidence agg  │    │ MCP API    │
└──────────────┘    └────────────────┘    └─────────────────┘    └────────────┘
```

### 4.1 Collectors (mostly already exist)
- `github_collector` ✅ — repos + metadata
- `github_history` 🔨 (new) — commits, PRs, issues, branches, releases per repo
- `vercel_collector` ✅
- `cloudflare_collector` ✅
- `conversation_collector` ✅

### 4.2 Extractors
Existing (keep, refactor to emit universal schema):
- `dependency_parser`
- `source_analyzer`
- `code_structure` (AST → File/Class/Function/Module)
- `cross_file_linker`
- `architecture_detector`
- `deployment_analyzer`
- `doc_code_linker`

New:
- `llm_extractor` — given (README + key code excerpts + commit summary) per
  repo, asks a small LLM to emit `{technologies, concepts, skills,
  methodologies, summary, narrative}` as JSON. Multiple passes per repo to
  keep prompt small. Used as one *additional* evidence stream — never
  overrides AST/dep evidence, just augments domain/methodology concepts that
  static analysis cannot see.
- `git_history_extractor` — commits/PRs/issues to nodes, links author-Person,
  links commits to files modified, classifies commit messages
  (feat/fix/refactor) for skill signal.
- `concept_resolver` — entity resolution across skills/tech/concepts using the
  alias file + fuzzy match.

### 4.3 Graph builder
A single `UniversalGraphBuilder` (replaces the per-store builders) that:
1. Receives typed events from extractors via a small bus interface
   (`emit_node`, `emit_edge`, `emit_evidence`).
2. Maintains an in-memory NetworkX graph as the canonical store.
3. Runs entity resolution + edge merging.
4. Hands the finished graph to N exporters.

### 4.4 Exporters
- `exporters/graph_json.py` → `data/graph/knowledge_graph.json` (consumer 2a)
- `exporters/wiki_vault.py` → `data/wiki/**.md` (consumer 2b)
- `exporters/neo4j_export.py` → upserts into Neo4j when configured
- `exporters/mcp_subgraph.py` → on-demand, query-driven subgraph for the MCP API

---

## 5. MCP-friendly query API

`POST /api/mcp/context` — universal context endpoint for dynamic UI sections.

Request:
```json
{
  "query": "show my GraphRAG / agent work",
  "section_hint": "project_card | skill_panel | timeline | repo_deep_dive",
  "node_id": null,
  "limit_nodes": 30,
  "limit_edges": 60
}
```

Response:
```json
{
  "nodes": [...universal schema...],
  "edges": [...],
  "primary_node_id": "...",
  "rendered": {
    "markdown": "## ...",      // pre-rendered for the section type
    "summary": "..."
  },
  "evidence": [...]
}
```

This is what gets called from the wiki app's MCP layer when khiw.dev needs to
populate a section.

---

## 6. Implementation order

1. **`app/schema/`** — universal node/edge enums, dataclasses, slug helpers,
   evidence model. Single source of truth for everyone.
2. **`app/exporters/graph_json.py`** + **`exporters/wiki_vault.py`** — make the
   integration contracts real first, even if the graph is small. Lock the
   downstream API shape.
3. **`app/builders/universal_builder.py`** — refactor the existing
   `KnowledgeGraphBuilder` to emit universal schema; existing extractors
   plug into it via the event bus.
4. **`app/collectors/github_history.py`** — commits/PRs/issues collection.
5. **`app/extractors/llm_extractor.py`** — LLM concept extraction with
   evidence tracking.
6. **`app/extractors/concept_resolver.py`** — entity resolution.
7. **`app/main.py` MCP endpoint** — `/api/mcp/context`.
8. **CI smoke test** — small fixture repo → run pipeline → assert vault &
   JSON shape.

---

## 7. Non-goals

- We do **not** rebuild the FastAPI app, Neo4j store, or vector store. They
  stay; we just give them a clean schema to speak.
- We do **not** delete existing extractors. They are refactored to emit into
  the universal builder.
- We do **not** ship a custom graph viz — the wiki app already has Sigma.js.
