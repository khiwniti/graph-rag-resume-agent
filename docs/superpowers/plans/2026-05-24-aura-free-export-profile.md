# Aura Free Export Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in `profile="aura_free"` filter to `export_to_neo4j()` that fits the universal graph inside Aura Free's 200K-node / 400K-rel cap without touching the pipeline or schema.

**Architecture:** A pure filter function builds three "kept" id sets (nodes, edges, evidence) from a `UniversalGraph`. The existing batched-UNWIND export loops skip rows whose ids aren't in those sets. `profile="full"` (default) preserves current behavior byte-identically.

**Tech Stack:** Python 3, pytest, `neo4j` driver (only imported in the live export path, not in tests).

**Spec:** `docs/superpowers/specs/2026-05-24-aura-free-export-profile-design.md`

---

## File Structure

- Modify: `app/exporters/neo4j_export.py` — add `profile`, `implements_top_n`, `documents_top_n` kwargs; two new private helpers; membership-set guards in the existing write loops.
- Create: `tests/test_aura_free_filter.py` — unit tests for the filter helper. No live Neo4j.
- Modify: `DEPLOY.md` — short paragraph on the new profile and Aura Free pause behavior.

---

## Task 1: Add filter helper with all-pass behavior, prove tests run

**Goal:** Establish the test file and the helper signature. The helper exists but returns the trivial "keep everything" projection. This locks the function shape before any filter logic lands.

**Files:**
- Modify: `app/exporters/neo4j_export.py`
- Create: `tests/test_aura_free_filter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_aura_free_filter.py`:

```python
"""Tests for the aura_free export-time filter.

The filter is a pure function over UniversalGraph that returns three id
sets — nodes, edges, evidence — that survive the projection. No Neo4j
involvement.
"""
from __future__ import annotations

from app.schema import (
    UniversalGraph,
    Node,
    NodeType,
    Edge,
    EdgeType,
    Evidence,
    EvidenceType,
)
from app.exporters.neo4j_export import _apply_aura_free_filter


def _g() -> UniversalGraph:
    g = UniversalGraph()
    repo = Node(id="repo:a", type=NodeType.REPO, label="a", slug="a")
    file_ = Node(id="file:a/x.py", type=NodeType.FILE, label="x.py", slug="a-x-py")
    g.add_node(repo)
    g.add_node(file_)
    g.add_edge(Edge(source=repo.id, target=file_.id, type=EdgeType.CONTAINS))
    return g


def test_filter_returns_three_sets_with_all_ids_when_graph_is_trivial():
    g = _g()
    kept_nodes, kept_edges, kept_evidence = _apply_aura_free_filter(
        g, implements_top_n=10, documents_top_n=10
    )
    assert kept_nodes == {"repo:a", "file:a/x.py"}
    assert len(kept_edges) == 1
    assert kept_evidence == set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aura_free_filter.py::test_filter_returns_three_sets_with_all_ids_when_graph_is_trivial -v`
Expected: FAIL with `ImportError` or `AttributeError` — `_apply_aura_free_filter` doesn't exist yet.

- [ ] **Step 3: Add the helper as a trivial all-pass function**

In `app/exporters/neo4j_export.py`, add this block immediately above the existing `_ensure_constraints` function (around line 195):

```python
def _apply_aura_free_filter(
    graph: "UniversalGraph",
    *,
    implements_top_n: int,
    documents_top_n: int,
) -> Tuple[set, set, set]:
    """Project a UniversalGraph down to the subset that fits Aura Free.

    Returns (kept_node_ids, kept_edge_keys, kept_evidence_ids). Pure function.
    """
    kept_nodes = set(graph.nodes.keys())
    kept_edges = set(graph.edges.keys())
    kept_evidence: set = set()
    return kept_nodes, kept_edges, kept_evidence
```

Also add `Tuple` to the existing `typing` import line at the top of the file:

```python
from typing import Any, Dict, Iterable, List, Optional, Tuple
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_aura_free_filter.py app/exporters/neo4j_export.py
git commit -m "feat(exporter): scaffold aura_free filter helper with all-pass behavior"
```

---

## Task 2: Drop CALLS edges

**Files:**
- Modify: `app/exporters/neo4j_export.py`
- Modify: `tests/test_aura_free_filter.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_aura_free_filter.py`:

```python
def test_filter_drops_calls_edges():
    g = UniversalGraph()
    fn_a = Node(id="fn:a", type=NodeType.FUNCTION, label="a", slug="a")
    fn_b = Node(id="fn:b", type=NodeType.FUNCTION, label="b", slug="b")
    file_ = Node(id="file:x", type=NodeType.FILE, label="x", slug="x")
    for n in (fn_a, fn_b, file_):
        g.add_node(n)
    calls_edge = Edge(source=fn_a.id, target=fn_b.id, type=EdgeType.CALLS)
    defines_edge = Edge(source=file_.id, target=fn_a.id, type=EdgeType.DEFINES)
    g.add_edge(calls_edge)
    g.add_edge(defines_edge)

    _, kept_edges, _ = _apply_aura_free_filter(
        g, implements_top_n=10, documents_top_n=10
    )
    assert calls_edge.key not in kept_edges
    assert defines_edge.key in kept_edges
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aura_free_filter.py::test_filter_drops_calls_edges -v`
Expected: FAIL — CALLS edge is still in `kept_edges`.

- [ ] **Step 3: Implement CALLS exclusion**

Replace the body of `_apply_aura_free_filter` in `app/exporters/neo4j_export.py` with:

```python
def _apply_aura_free_filter(
    graph: "UniversalGraph",
    *,
    implements_top_n: int,
    documents_top_n: int,
) -> Tuple[set, set, set]:
    """Project a UniversalGraph down to the subset that fits Aura Free.

    Returns (kept_node_ids, kept_edge_keys, kept_evidence_ids). Pure function.
    """
    from ..schema import EdgeType  # local import to avoid cycles at module load

    kept_edges: set = set()
    for key, edge in graph.edges.items():
        if edge.type is EdgeType.CALLS:
            continue
        kept_edges.add(key)

    kept_nodes = set(graph.nodes.keys())
    kept_evidence: set = set()
    return kept_nodes, kept_edges, kept_evidence
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_aura_free_filter.py app/exporters/neo4j_export.py
git commit -m "feat(exporter): drop CALLS edges in aura_free profile"
```

---

## Task 3: Cap IMPLEMENTS and DOCUMENTS top-N per source

**Files:**
- Modify: `app/exporters/neo4j_export.py`
- Modify: `tests/test_aura_free_filter.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_aura_free_filter.py`:

```python
def test_filter_caps_implements_per_source_by_weight():
    g = UniversalGraph()
    src = Node(id="file:x", type=NodeType.FILE, label="x", slug="x")
    g.add_node(src)
    targets = []
    for i in range(5):
        t = Node(id=f"concept:{i}", type=NodeType.CONCEPT, label=str(i), slug=str(i))
        g.add_node(t)
        targets.append(t)
        g.add_edge(
            Edge(source=src.id, target=t.id, type=EdgeType.IMPLEMENTS, weight=float(i))
        )

    _, kept_edges, _ = _apply_aura_free_filter(
        g, implements_top_n=2, documents_top_n=10
    )
    impl_kept = [e for e in g.edges.values()
                 if e.key in kept_edges and e.type is EdgeType.IMPLEMENTS]
    assert len(impl_kept) == 2
    kept_targets = {e.target for e in impl_kept}
    assert kept_targets == {"concept:4", "concept:3"}  # top-2 by weight


def test_filter_caps_documents_per_source_by_weight():
    g = UniversalGraph()
    src = Node(id="doc:x", type=NodeType.DOCUMENT, label="x", slug="x")
    g.add_node(src)
    for i in range(4):
        t = Node(id=f"file:{i}", type=NodeType.FILE, label=str(i), slug=str(i))
        g.add_node(t)
        g.add_edge(
            Edge(source=src.id, target=t.id, type=EdgeType.DOCUMENTS, weight=float(i))
        )

    _, kept_edges, _ = _apply_aura_free_filter(
        g, implements_top_n=10, documents_top_n=1
    )
    doc_kept = [e for e in g.edges.values()
                if e.key in kept_edges and e.type is EdgeType.DOCUMENTS]
    assert len(doc_kept) == 1
    assert doc_kept[0].target == "file:3"


def test_filter_caps_are_per_source_not_global():
    g = UniversalGraph()
    s1 = Node(id="file:a", type=NodeType.FILE, label="a", slug="a")
    s2 = Node(id="file:b", type=NodeType.FILE, label="b", slug="b")
    g.add_node(s1); g.add_node(s2)
    for src in (s1, s2):
        for i in range(3):
            t = Node(id=f"concept:{src.id}-{i}", type=NodeType.CONCEPT,
                     label=str(i), slug=str(i))
            g.add_node(t)
            g.add_edge(Edge(source=src.id, target=t.id,
                            type=EdgeType.IMPLEMENTS, weight=float(i)))

    _, kept_edges, _ = _apply_aura_free_filter(
        g, implements_top_n=2, documents_top_n=10
    )
    impl_kept = [e for e in g.edges.values()
                 if e.key in kept_edges and e.type is EdgeType.IMPLEMENTS]
    assert len(impl_kept) == 4  # 2 per source × 2 sources
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: the three new tests FAIL (still 5 IMPLEMENTS / 4 DOCUMENTS in `kept_edges`).

- [ ] **Step 3: Implement the per-source top-N cap**

Replace the body of `_apply_aura_free_filter` in `app/exporters/neo4j_export.py` with:

```python
def _apply_aura_free_filter(
    graph: "UniversalGraph",
    *,
    implements_top_n: int,
    documents_top_n: int,
) -> Tuple[set, set, set]:
    """Project a UniversalGraph down to the subset that fits Aura Free.

    Returns (kept_node_ids, kept_edge_keys, kept_evidence_ids). Pure function.

    Rules applied:
      1. Drop EdgeType.CALLS entirely.
      2. For each source node, keep only the top-N IMPLEMENTS and DOCUMENTS
         edges by weight (ties broken by target id for determinism).
    """
    from ..schema import EdgeType

    capped_types = {
        EdgeType.IMPLEMENTS: implements_top_n,
        EdgeType.DOCUMENTS: documents_top_n,
    }

    by_source_capped: Dict[Tuple[str, EdgeType], List[Tuple[float, str, str]]] = {}
    kept_edges: set = set()

    for key, edge in graph.edges.items():
        if edge.type is EdgeType.CALLS:
            continue
        if edge.type in capped_types:
            bucket = by_source_capped.setdefault((edge.source, edge.type), [])
            bucket.append((edge.weight, edge.target, key))
            continue
        kept_edges.add(key)

    for (source, etype), bucket in by_source_capped.items():
        # Descending weight, then ascending target for deterministic ties.
        bucket.sort(key=lambda row: (-row[0], row[1]))
        for _, _, key in bucket[: capped_types[etype]]:
            kept_edges.add(key)

    kept_nodes = set(graph.nodes.keys())
    kept_evidence: set = set()
    return kept_nodes, kept_edges, kept_evidence
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: all five tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_aura_free_filter.py app/exporters/neo4j_export.py
git commit -m "feat(exporter): cap IMPLEMENTS/DOCUMENTS top-N per source in aura_free"
```

---

## Task 4: Skip orphaned `:function` nodes

**Files:**
- Modify: `app/exporters/neo4j_export.py`
- Modify: `tests/test_aura_free_filter.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_aura_free_filter.py`:

```python
def test_filter_drops_function_nodes_orphaned_after_calls_removal():
    """A function only referenced by CALLS edges should not survive.

    A function still referenced by DEFINES / HAS_MEMBER / etc. must survive.
    Non-function orphans must always survive (this rule is function-only).
    """
    g = UniversalGraph()
    file_ = Node(id="file:x", type=NodeType.FILE, label="x", slug="x")
    fn_kept = Node(id="fn:kept", type=NodeType.FUNCTION, label="kept", slug="kept")
    fn_orphan = Node(id="fn:orphan", type=NodeType.FUNCTION,
                     label="orphan", slug="orphan")
    fn_caller = Node(id="fn:caller", type=NodeType.FUNCTION,
                     label="caller", slug="caller")
    concept_orphan = Node(id="concept:orphan", type=NodeType.CONCEPT,
                          label="o", slug="o")
    for n in (file_, fn_kept, fn_orphan, fn_caller, concept_orphan):
        g.add_node(n)

    g.add_edge(Edge(source=file_.id, target=fn_kept.id, type=EdgeType.DEFINES))
    # fn_orphan and fn_caller are only connected via CALLS — both should drop.
    g.add_edge(Edge(source=fn_caller.id, target=fn_orphan.id, type=EdgeType.CALLS))

    kept_nodes, _, _ = _apply_aura_free_filter(
        g, implements_top_n=10, documents_top_n=10
    )
    assert "fn:kept" in kept_nodes
    assert "fn:orphan" not in kept_nodes
    assert "fn:caller" not in kept_nodes
    assert "file:x" in kept_nodes
    assert "concept:orphan" in kept_nodes  # not a function, never pruned
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aura_free_filter.py::test_filter_drops_function_nodes_orphaned_after_calls_removal -v`
Expected: FAIL — `fn:orphan` and `fn:caller` are still in `kept_nodes`.

- [ ] **Step 3: Implement orphan-function pruning**

In `app/exporters/neo4j_export.py`, replace this block at the end of `_apply_aura_free_filter`:

```python
    kept_nodes = set(graph.nodes.keys())
    kept_evidence: set = set()
    return kept_nodes, kept_edges, kept_evidence
```

with:

```python
    from ..schema import NodeType

    referenced_by_kept_edge: set = set()
    for key in kept_edges:
        edge = graph.edges[key]
        referenced_by_kept_edge.add(edge.source)
        referenced_by_kept_edge.add(edge.target)

    kept_nodes: set = set()
    for node_id, node in graph.nodes.items():
        if node.type is NodeType.FUNCTION and node_id not in referenced_by_kept_edge:
            continue
        kept_nodes.add(node_id)

    kept_evidence: set = set()
    return kept_nodes, kept_edges, kept_evidence
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: all six tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_aura_free_filter.py app/exporters/neo4j_export.py
git commit -m "feat(exporter): drop orphan function nodes after CALLS removal"
```

---

## Task 5: Restrict evidence to retained subgraph

**Files:**
- Modify: `app/exporters/neo4j_export.py`
- Modify: `tests/test_aura_free_filter.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_aura_free_filter.py`:

```python
def test_filter_keeps_only_evidence_referenced_by_retained_subgraph():
    """Evidence survives iff its source_node_id is retained OR it's cited
    by a retained edge's evidence_ids."""
    g = UniversalGraph()
    repo = Node(id="repo:a", type=NodeType.REPO, label="a", slug="a")
    file_ = Node(id="file:x", type=NodeType.FILE, label="x", slug="x")
    fn_orphan = Node(id="fn:orphan", type=NodeType.FUNCTION,
                     label="orphan", slug="orphan")
    fn_caller = Node(id="fn:caller", type=NodeType.FUNCTION,
                     label="caller", slug="caller")
    for n in (repo, file_, fn_orphan, fn_caller):
        g.add_node(n)

    ev_kept_by_node = Evidence(
        id="ev:1", evidence_type=EvidenceType.SOURCE_CODE,
        source_node_id="file:x", locator="x.py:1",
    )
    ev_kept_by_edge = Evidence(
        id="ev:2", evidence_type=EvidenceType.SOURCE_CODE,
        source_node_id="fn:orphan",  # node will be pruned
        locator="x.py:5",
    )
    ev_orphan = Evidence(
        id="ev:3", evidence_type=EvidenceType.SOURCE_CODE,
        source_node_id="fn:orphan", locator="x.py:9",
    )
    for ev in (ev_kept_by_node, ev_kept_by_edge, ev_orphan):
        g.add_evidence(ev)

    e_contains = Edge(source=repo.id, target=file_.id, type=EdgeType.CONTAINS,
                      evidence=["ev:2"])
    e_calls = Edge(source=fn_caller.id, target=fn_orphan.id,
                   type=EdgeType.CALLS, evidence=["ev:3"])
    g.add_edge(e_contains)
    g.add_edge(e_calls)

    _, _, kept_evidence = _apply_aura_free_filter(
        g, implements_top_n=10, documents_top_n=10
    )
    assert kept_evidence == {"ev:1", "ev:2"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aura_free_filter.py::test_filter_keeps_only_evidence_referenced_by_retained_subgraph -v`
Expected: FAIL — `kept_evidence` is still empty.

- [ ] **Step 3: Implement evidence restriction**

In `app/exporters/neo4j_export.py`, replace the final `kept_evidence: set = set()` line in `_apply_aura_free_filter` with:

```python
    cited_by_kept_edge: set = set()
    for key in kept_edges:
        cited_by_kept_edge.update(graph.edges[key].evidence)

    kept_evidence: set = set()
    for ev_id, ev in graph.evidence.items():
        if ev.source_node_id in kept_nodes or ev_id in cited_by_kept_edge:
            kept_evidence.add(ev_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: all seven tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_aura_free_filter.py app/exporters/neo4j_export.py
git commit -m "feat(exporter): restrict evidence to retained subgraph"
```

---

## Task 6: Wire `profile` kwarg into `export_to_neo4j` and add projection log

**Files:**
- Modify: `app/exporters/neo4j_export.py`
- Modify: `tests/test_aura_free_filter.py`

- [ ] **Step 1: Write the failing test for unknown-profile rejection**

Append to `tests/test_aura_free_filter.py`:

```python
import pytest
from app.exporters.neo4j_export import _resolve_profile


def test_resolve_profile_accepts_full_default():
    assert _resolve_profile(None, env=None) == "full"


def test_resolve_profile_accepts_explicit_aura_free():
    assert _resolve_profile("aura_free", env=None) == "aura_free"


def test_resolve_profile_reads_env_when_kwarg_missing():
    assert _resolve_profile(None, env="aura_free") == "aura_free"


def test_resolve_profile_kwarg_overrides_env():
    assert _resolve_profile("full", env="aura_free") == "full"


def test_resolve_profile_rejects_unknown_value():
    with pytest.raises(ValueError, match="unknown profile"):
        _resolve_profile("nonsense", env=None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: the five new tests FAIL with `ImportError` for `_resolve_profile`.

- [ ] **Step 3: Add the profile-resolver helper**

Add this helper to `app/exporters/neo4j_export.py` immediately below `_apply_aura_free_filter`:

```python
_VALID_PROFILES = {"full", "aura_free"}


def _resolve_profile(kwarg: Optional[str], *, env: Optional[str]) -> str:
    """Pick the export profile from kwarg > env > default('full').

    Raises ValueError on unknown values.
    """
    raw = kwarg if kwarg is not None else env
    profile = raw if raw is not None else "full"
    if profile not in _VALID_PROFILES:
        raise ValueError(
            f"unknown profile {profile!r}; expected one of {sorted(_VALID_PROFILES)}"
        )
    return profile


def _log_projection(
    profile: str,
    kept_nodes: set,
    kept_edges: set,
    kept_evidence: set,
) -> None:
    """Emit one INFO line per export with projected counts; WARN if over cap."""
    logger.info(
        "Neo4j export projection profile=%s nodes=%d edges=%d evidence=%d",
        profile, len(kept_nodes), len(kept_edges), len(kept_evidence),
    )
    if profile == "aura_free":
        if len(kept_nodes) > 200_000 or len(kept_edges) > 400_000:
            logger.warning(
                "aura_free projection still exceeds Aura Free caps "
                "(nodes>200k or edges>400k); lower implements_top_n/documents_top_n"
            )
```

- [ ] **Step 4: Run helper tests to verify they pass**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: all twelve tests PASS.

- [ ] **Step 5: Wire `profile` into `export_to_neo4j`**

In `app/exporters/neo4j_export.py`, change the `export_to_neo4j` signature from:

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
) -> Dict[str, int]:
```

to:

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
    profile: Optional[str] = None,
    implements_top_n: int = 10,
    documents_top_n: int = 10,
) -> Dict[str, int]:
```

Then, immediately after the existing credentials check (right before the `logger.info("Connecting to Neo4j ...` line), add:

```python
    resolved_profile = _resolve_profile(profile, env=os.getenv("NEO4J_PROFILE"))
    if resolved_profile == "aura_free":
        kept_nodes, kept_edges, kept_evidence = _apply_aura_free_filter(
            graph,
            implements_top_n=implements_top_n,
            documents_top_n=documents_top_n,
        )
    else:
        kept_nodes = set(graph.nodes.keys())
        kept_edges = set(graph.edges.keys())
        kept_evidence = set(graph.evidence.keys())
    _log_projection(resolved_profile, kept_nodes, kept_edges, kept_evidence)
```

- [ ] **Step 6: Add a smoke test for `export_to_neo4j` profile dispatch**

Append to `tests/test_aura_free_filter.py`:

```python
def test_export_to_neo4j_rejects_unknown_profile_before_any_io(monkeypatch):
    """profile validation happens before we touch the neo4j driver."""
    from app.exporters import neo4j_export

    # If the driver were touched, this would explode; we expect ValueError first.
    monkeypatch.setattr(neo4j_export, "GraphDatabase", None, raising=False)
    monkeypatch.setattr(neo4j_export, "_NEO4J_AVAILABLE", True, raising=False)

    with pytest.raises(ValueError, match="unknown profile"):
        neo4j_export.export_to_neo4j(
            UniversalGraph(),
            uri="bolt://x", user="u", password="p",
            profile="bogus",
        )
```

Note: this test relies on `_resolve_profile` being called before the driver is used. If the existing code orders the credentials check before profile resolution (which it does after step 5), provide credentials so we get past that check and reach the profile resolver.

- [ ] **Step 7: Run tests to verify they all pass**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: all thirteen tests PASS.

- [ ] **Step 8: Commit**

```bash
git add tests/test_aura_free_filter.py app/exporters/neo4j_export.py
git commit -m "feat(exporter): wire profile kwarg + projection log into export_to_neo4j"
```

---

## Task 7: Apply membership guards inside the write loops

**Goal:** Make the existing node / edge / evidence write loops skip rows whose ids aren't in the kept sets. This is the only behavioral change for non-`aura_free` callers, and it must be a no-op for `profile="full"` (the kept sets contain every id).

**Files:**
- Modify: `app/exporters/neo4j_export.py`

- [ ] **Step 1: Guard the node-write loop**

In `app/exporters/neo4j_export.py`, find the loop that begins:

```python
            nodes_by_label: Dict[str, List[Dict[str, Any]]] = {}
            for node in graph.nodes.values():
                nodes_by_label.setdefault(_label(node.type), []).append({
```

Change `for node in graph.nodes.values():` to:

```python
            for node in graph.nodes.values():
                if node.id not in kept_nodes:
                    continue
```

- [ ] **Step 2: Guard the edge-write loop**

Find the loop that begins:

```python
            edges_by_type: Dict[str, List[Dict[str, Any]]] = {}
            for edge in graph.edges.values():
                edges_by_type.setdefault(edge.type.value, []).append({
```

Change `for edge in graph.edges.values():` to:

```python
            for edge in graph.edges.values():
                if edge.key not in kept_edges:
                    continue
```

- [ ] **Step 3: Guard the evidence-write block**

Find the block that begins:

```python
            if include_evidence and graph.evidence:
                ev_rows = [{
                    "id": e.id,
```

Change `ev_rows = [{ ... } for e in graph.evidence.values()]` to:

```python
            if include_evidence and graph.evidence:
                ev_rows = [{
                    "id": e.id,
                    "evidence_type": e.evidence_type.value,
                    "source_node_id": e.source_node_id,
                    "locator": e.locator,
                    "excerpt": (e.excerpt or "")[:1024],
                    "confidence": float(e.confidence or 0.0),
                    "extracted_at": e.extracted_at.isoformat() if e.extracted_at else None,
                } for e in graph.evidence.values() if e.id in kept_evidence]
```

(The `if e.id in kept_evidence` filter is the only addition; the rest of the list comprehension is unchanged.)

- [ ] **Step 4: Run the filter tests to confirm they still pass**

Run: `pytest tests/test_aura_free_filter.py -v`
Expected: all thirteen tests still PASS (these tests don't hit the write loops, but they prove we didn't break the helper).

- [ ] **Step 5: Verify the file still imports cleanly**

Run: `python -c "from app.exporters.neo4j_export import export_to_neo4j; print('ok')"`
Expected: `ok` printed, no traceback.

- [ ] **Step 6: Commit**

```bash
git add app/exporters/neo4j_export.py
git commit -m "feat(exporter): membership-guard write loops behind aura_free filter"
```

---

## Task 8: Document the new profile and Aura Free pause behavior

**Files:**
- Modify: `DEPLOY.md`

- [ ] **Step 1: Append the section**

Open `DEPLOY.md`. Append (at end of file) the following section verbatim:

```markdown
## Neo4j Aura Free profile

`export_to_neo4j(graph, profile="aura_free")` ships a pruned subgraph that
fits inside Aura Free's 200,000-node / 400,000-relationship cap. The full
graph stays on disk in `data/graph/knowledge_graph.json`.

What the profile drops or caps:

- All `CALLS` edges (the largest edge type — ~78% of the full graph).
- `IMPLEMENTS` and `DOCUMENTS` edges, capped at `implements_top_n` / `documents_top_n`
  per source node (default 10, by descending weight).
- `:function` nodes orphaned by the `CALLS` removal.
- `Evidence` rows not referenced by any retained node or edge.

The profile can also be set via `NEO4J_PROFILE=aura_free` (kwarg wins).

A projection log is emitted before any write; if projected counts still
exceed Aura Free's caps the exporter logs a warning but does not abort.
Lower the `*_top_n` kwargs to trim further (the product page advertises a
stricter 50,000-node / 175,000-relationship cap in some regions).

Aura Free pauses an instance after 72 hours of inactivity; the first query
after resume can take a few minutes while the backup is restored. Build
retry/backoff into clients and consider a daily lightweight `RETURN 1`
query to keep the instance warm.
```

- [ ] **Step 2: Commit**

```bash
git add DEPLOY.md
git commit -m "docs: document aura_free export profile and pause behavior"
```

---

## Self-Review

**Spec coverage:**
- Filter rule 1 (drop CALLS) → Task 2 ✓
- Filter rule 2 (cap IMPLEMENTS/DOCUMENTS) → Task 3 ✓
- Filter rule 3 (orphan function pruning) → Task 4 ✓
- Filter rule 4 (evidence restricted to retained subgraph) → Task 5 ✓
- Filter rule 5 (pre-flight projection log + warn) → Task 6 (`_log_projection`) ✓
- `profile` kwarg + `NEO4J_PROFILE` env + `ValueError` on unknown → Task 6 ✓
- Membership-set guards in write loops → Task 7 ✓
- DEPLOY.md note on profile + 72h pause → Task 8 ✓
- "No regressions for `profile='full'` callers" → Task 7 (kept_* sets contain all ids when profile=full) ✓

**Placeholder scan:** No `TBD` / `TODO` / "add appropriate handling" / "similar to above" — every code change shows the actual code. ✓

**Type / name consistency:**
- `_apply_aura_free_filter` signature is identical across Tasks 1–5. ✓
- Return shape `(set, set, set)` consistent throughout. ✓
- `kept_nodes` / `kept_edges` / `kept_evidence` names consistent in helper and in `export_to_neo4j`. ✓
- `implements_top_n` / `documents_top_n` spelled identically in spec, helper, and signature. ✓

No issues to fix.
