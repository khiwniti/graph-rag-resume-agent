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
