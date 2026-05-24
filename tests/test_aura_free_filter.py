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
    g.add_node(s1)
    g.add_node(s2)
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


def test_resolve_profile_accepts_full_default():
    from app.exporters.neo4j_export import _resolve_profile
    assert _resolve_profile(None, env=None) == "full"


def test_resolve_profile_accepts_explicit_aura_free():
    from app.exporters.neo4j_export import _resolve_profile
    assert _resolve_profile("aura_free", env=None) == "aura_free"


def test_resolve_profile_reads_env_when_kwarg_missing():
    from app.exporters.neo4j_export import _resolve_profile
    assert _resolve_profile(None, env="aura_free") == "aura_free"


def test_resolve_profile_kwarg_overrides_env():
    from app.exporters.neo4j_export import _resolve_profile
    assert _resolve_profile("full", env="aura_free") == "full"


def test_resolve_profile_rejects_unknown_value():
    from app.exporters.neo4j_export import _resolve_profile
    import pytest
    with pytest.raises(ValueError, match="unknown profile"):
        _resolve_profile("nonsense", env=None)
