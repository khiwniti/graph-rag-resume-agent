#!/usr/bin/env python3
"""Neo4j Aura free-tier budget estimator for career graphs.

Reads a UniversalGraph JSON export (data/graph/knowledge_graph.json) and emits:
- node/edge counts by type
- recommended caps
- pass/fail and reduction hints

This is intentionally simple and fast; it does not require Neo4j.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


DEFAULT_MAX_NODES = 50_000
DEFAULT_MAX_EDGES = 100_000


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Neo4j Aura free-tier budget estimator")
    p.add_argument("--graph", default="data/graph/knowledge_graph.json")
    p.add_argument("--max-nodes", type=int, default=DEFAULT_MAX_NODES)
    p.add_argument("--max-edges", type=int, default=DEFAULT_MAX_EDGES)
    p.add_argument("--output", default="data/quality/neo4j_budget_report.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    graph_path = Path(args.graph)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    graph = json.loads(graph_path.read_text())
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    node_types = Counter(n.get("type", "unknown") for n in nodes)
    edge_types = Counter(e.get("type", "unknown") for e in edges)

    total_nodes = len(nodes)
    total_edges = len(edges)

    within = (total_nodes <= args.max_nodes) and (total_edges <= args.max_edges)

    hints = []
    if total_edges > args.max_edges:
        # common culprit in this repo is CALLS
        if edge_types.get("CALLS"):
            hints.append("Edges dominated by CALLS; disable parse_code or drop CALLS edges for Aura-free-tier export.")
        if edge_types.get("DEFINES") or edge_types.get("HAS_MEMBER"):
            hints.append("Many code-structure edges (DEFINES/HAS_MEMBER); disable parse_code in RepoSpec for compact mode.")
    if total_nodes > args.max_nodes:
        if node_types.get("function") or node_types.get("class"):
            hints.append("Nodes dominated by function/class; disable parse_code for compact mode.")
        if node_types.get("section"):
            hints.append("Many document sections; cap docs per repo or keep only README headings.")

    report = {
        "graph": str(graph_path),
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "node_counts_by_type": dict(node_types),
        "edge_counts_by_type": dict(edge_types),
        "limits": {"max_nodes": args.max_nodes, "max_edges": args.max_edges},
        "within_free_tier_budget": within,
        "hints": hints,
    }

    out_path.write_text(json.dumps(report, indent=2))

    status = "PASS" if within else "FAIL"
    print(f"[{status}] nodes={total_nodes:,} edges={total_edges:,} -> {out_path}")
    if hints:
        for h in hints:
            print(f"- {h}")

    return 0 if within else 3


if __name__ == "__main__":
    raise SystemExit(main())
