# Aura Free Export Profile

**Status:** Approved (design)
**Date:** 2026-05-24
**Scope:** `app/exporters/neo4j_export.py` only

## Problem

The universal graph currently builds to ~75K nodes and ~960K edges (see `data/universal_summary.json`). Neo4j Aura Free caps a single instance at 200K nodes / 400K relationships per the official FAQ, and the Aura product page advertises a stricter 50K / 175K. Today's exporter pushes the full graph unconditionally, so any attempt to ship to Aura Free fails or silently truncates once the cap is hit. The `CALLS` edge type alone (~748K) exceeds every published limit.

## Goal

Fit a meaningful subset of the universal graph inside Aura Free's ceiling without changing the universal-graph build, schema, or local export paths. Optimization is surgical: a single new code path in the exporter, opt-in via a profile argument.

Non-goals:
- No edge aggregation or weighted-summary collapse.
- No changes to `app/builders/`, `app/schema/`, or any pipeline stage.
- No keep-alive / wake-from-pause infrastructure.
- No new CLI on `scripts/build_universal_graph.py`.

## Design

Add a `profile: str = "full"` keyword argument to `export_to_neo4j()` with two accepted values:

- `"full"` — current behavior. Default. No regressions for existing callers.
- `"aura_free"` — apply a deterministic filter to nodes, edges, and evidence before any write.

The filter runs entirely in memory against the already-built `UniversalGraph`, produces a projected view, and feeds that view through the existing batched UNWIND writes. No new Cypher, no schema change.

### Filter rules (applied in order)

1. **Drop `CALLS` edges entirely.** Highest-volume edge type, lowest career-relevance signal on a remote graph. Removes the largest source of relationship pressure (~748K of ~960K).
2. **Cap `IMPLEMENTS` and `DOCUMENTS` per source node.** For each source node, keep the top-N edges of that type by `weight`, ties broken by target id for determinism. Default N = 10. Tunable via the kwargs `implements_top_n` and `documents_top_n`.
3. **Skip orphaned `:function` nodes.** After steps 1–2, drop any `function`-typed node that no longer appears as either endpoint of a retained edge. Function nodes are still referenced locally via `DEFINES` from files, but on Aura Free they add ~35K nodes for no remaining query value.
4. **Restrict evidence to the retained subgraph.** Push only `Evidence` whose `source_node_id` survives or which is cited by a retained edge's `evidence_ids`. The full evidence set remains on disk.
5. **Pre-flight projection log.** Before any write, log projected counts and warn (do not abort) if projected nodes > 200K or projected edges > 400K. Operator decides whether to proceed.

### Function signature

```python
def export_to_neo4j(
    graph: UniversalGraph,
    *,
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    wipe_first: bool = False,
    include_evidence: bool = True,
    profile: str = "full",            # NEW
    implements_top_n: int = 10,       # NEW, used only when profile == "aura_free"
    documents_top_n: int = 10,        # NEW, used only when profile == "aura_free"
) -> Dict[str, int]:
```

`profile` may also be supplied via the `NEO4J_PROFILE` env var (falls back to `"full"` when unset). Explicit kwarg wins over env var. Unknown profile values raise `ValueError`.

### Internal structure

Two new private helpers in the same file:

- `_apply_aura_free_filter(graph, *, implements_top_n, documents_top_n) -> tuple[set[str], set[str], set[str]]` — returns `(kept_node_ids, kept_edge_ids, kept_evidence_ids)`. Pure function over the graph; no I/O.
- `_log_projection(profile, kept_node_ids, kept_edge_ids, kept_evidence_ids) -> None` — emits a single INFO line with counts and a WARN if projected counts exceed Aura Free thresholds.

The existing node/edge/evidence write loops gain a single membership check (`if node.id not in kept_node_ids: continue`, etc.). No restructuring of the write loops.

### Estimated projection

Against current `data/universal_summary.json`:

- Edges: 960,252 − 748,480 (CALLS) − ~capped(IMPLEMENTS, DOCUMENTS at 10/source) ≈ **~200–220K**
- Nodes: 75,416 − ~35,000 (orphaned functions) ≈ **~40K**
- Evidence: scoped to retained subgraph, expect significant reduction from 71K.

Comfortably under the 200K / 400K FAQ limit. Tight against the 50K / 175K product-page limit — `implements_top_n` and `documents_top_n` can be dropped to 5 or 3 if needed; both are kwargs.

## Testing

- Unit-level: build a small synthetic `UniversalGraph` (a few repos, files, functions, plus a `CALLS`-heavy subgraph) and assert that `_apply_aura_free_filter` returns the expected `kept_*` sets. No live Neo4j needed.
- Smoke: existing callers using `profile="full"` (default) produce byte-identical writes — verifiable by counting `session.run` invocations.
- Integration (manual, optional): a follow-up run against an Aura Free instance to confirm the projected counts hold.

## Risks and mitigations

- **Risk:** removing `CALLS` weakens function-level queries on Aura.
  **Mitigation:** the full graph remains in `data/graph/knowledge_graph.json` for any local or paid-tier deployment; profile is per-export.
- **Risk:** product-page 50K/175K limit may apply in some regions despite the FAQ number.
  **Mitigation:** kwargs let operators trim further without a code change; the projection log warns before write.
- **Risk:** Aura Free auto-pauses after 72h idle and the first query post-pause can take minutes.
  **Mitigation:** out of scope here; document in `DEPLOY.md` as a follow-up.

## Out of scope

- Edge aggregation, weighted-summary collapse.
- Pipeline-time pruning.
- Keep-alive ping infrastructure.
- CLI surface changes.
