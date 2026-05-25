# Universal Knowledge Graph — Quickstart

This repo now produces a **professional, multi-source, evidence-backed
knowledge graph** of your career — fully aligned with the design in
`plans/KNOWLEDGE_GRAPH_REDESIGN.md` — and emits it in two shapes that the
downstream MCP UI consumers (`careergraph-wiki-mcp-ui` → `khiw.dev`) can
ingest directly.

## What's new

| Layer                                  | Where                                          |
| -------------------------------------- | ---------------------------------------------- |
| Universal schema (26 node types,       | `app/schema/`                                  |
| 27 edge types, first-class Evidence)   |                                                |
| Builder that runs the existing AST,    | `app/builders/universal_builder.py`            |
| dependency, doc-link, deployment       |                                                |
| extractors and emits universal output  |                                                |
| LLM concept/skill extractor            | `app/extractors/llm_concept_extractor.py`      |
| (NVIDIA NIM, OpenAI-compatible)        |                                                |
| Two integration exporters              | `app/exporters/`                               |
| Pipeline orchestrator                  | `app/pipeline_universal.py`                    |
| Runnable build script                  | `scripts/build_universal_graph.py`             |
| MCP UI context endpoint                | `app/api/mcp_context.py`                       |
| End-to-end smoke test                  | `tests/test_universal_pipeline.py`             |

## Outputs (the integration contracts)

1. `data/graph/knowledge_graph.json` — exact shape consumed by
   `careergraph-wiki-mcp-ui/apps/api/app/connectors/graph_connector.py`
   (`{nodes:[{id,type,properties,...}], edges:[{from,to,type,...}]}`)
2. `data/wiki/` — Obsidian-style markdown vault with YAML frontmatter,
   `[[folder/slug|Label]]` wikilinks, automatic backlinks, and per-page
   evidence audit rows. Layout matches the wiki app's
   `wiki/{skills,projects,repos,vercel,cloudflare,career,docs,concepts,...}`
   convention.

## One-shot build

```bash
# Single repo (this one):
python scripts/build_universal_graph.py \
    --repo-root . \
    --owner khiwniti --name graph-rag-resume-agent \
    --person-login khiwniti --no-llm

# Many repos (one per subfolder under the dir):
python scripts/build_universal_graph.py \
    --repos-dir ./data/raw/repos \
    --person-login khiwniti

# Plus pre-collected Vercel / Cloudflare / conversations:
python scripts/build_universal_graph.py \
    --repos-dir ./data/raw/repos \
    --collected-json ./data/raw/collected.json \
    --person-login khiwniti
```

`--no-llm` disables the NVIDIA NIM augmentation. By default, `--llm-top-n 25`
caps how many repos get LLM-augmented to keep cost bounded. Set
`NVIDIA_API_KEY` in your env to enable it.

Last run on this repo against itself produced:

```
1,289 nodes / 3,584 edges / 531 evidence records / 148 wiki pages
```

(person, repo, 74 files, 857 functions, 208 classes, 142 technologies, 3
concepts, 1 route, 1 document, 1 section)

## MCP UI endpoint

The FastAPI app now exposes `POST /api/mcp/context` for the wiki/portfolio
to call. Given a query and/or a node id and a section hint, it returns:

- a focused subgraph (BFS bounded by `hops`, `limit_nodes`, `limit_edges`)
- the primary node id
- pre-rendered section markdown sized for one MCP UI card
- supporting evidence rows

```bash
curl -X POST http://localhost:8000/api/mcp/context \
  -H 'Content-Type: application/json' \
  -d '{"query":"fastapi","section_hint":"skill_panel","limit_nodes":10}'
```

Section hints: `project_card`, `skill_panel`, `repo_deep_dive`, `timeline`,
`concept_map`, `auto`.

## Why this is an improvement

The previous extraction collapsed each repo into a single node fed by the
README. The universal builder now produces:

- **Code structure depth**: every File / Class / Function as a node;
  `CONTAINS`, `DEFINES`, `IMPORTS`, `CALLS`, `HAS_MEMBER` edges.
- **Multi-evidence skills**: each Technology/Skill/Concept node carries
  multiple Evidence rows (source-code, dependency, config, deployment,
  doc, LLM-inference) and confidence is aggregated probabilistically, so
  the same claim from many places becomes a higher-confidence claim.
- **Documents are first-class**: every README is split into Sections, each
  Section linked to the source files it documents.
- **Deployments are graphed**: Vercel projects, Cloudflare workers, domains,
  routes are real nodes with `DEPLOYS_TO` / `SERVES` edges.
- **Conversations** plug in via `add_conversation(...)`.
- **LLM augmentation** runs *alongside* deterministic extraction. LLM
  confidence is capped (≤0.85) so it can never overrule concrete code
  evidence — it just surfaces methodologies & abstract concepts that AST
  cannot see.
- **Stable ids** mean re-runs merge cleanly instead of duplicating.

## Layered with the existing stack

The legacy `app/pipeline.py` (Neo4j + RAG narrative path) is untouched;
this is additive. You can run both. The new universal graph is the source
of truth for the wiki/MCP integration; the Neo4j path remains for richer
Cypher queries if you want them.

## Tests

```bash
python -m pytest tests/test_universal_pipeline.py -v
```

## Design doc

See `plans/KNOWLEDGE_GRAPH_REDESIGN.md` for the full spec, schema
rationale, and the next-step backlog (git-history collector, conversation
auto-import, MCP server wrapping, etc.).
