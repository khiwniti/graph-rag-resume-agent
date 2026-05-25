"""UniversalGraph — the canonical in-memory store.

A thin wrapper around dictionaries (and optionally NetworkX) that all
extractors emit into via ``add_node`` / ``add_edge`` / ``add_evidence``.

Exporters consume a UniversalGraph and write it out as graph JSON, markdown
vault, Neo4j, etc. The exporters never touch raw extractor data — only this
graph.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from .nodes import Node, NodeType
from .edges import Edge, EdgeType
from .evidence import Evidence, aggregate_confidence

logger = logging.getLogger(__name__)


@dataclass
class UniversalGraph:
    """Canonical in-memory knowledge graph."""

    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: Dict[str, Edge] = field(default_factory=dict)
    evidence: Dict[str, Evidence] = field(default_factory=dict)
    # adjacency (computed lazily / on demand)
    _adj_out: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    _adj_in: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── mutation ─────────────────────────────────────────────────────────

    def add_node(self, node: Node) -> Node:
        if node.id in self.nodes:
            return self.nodes[node.id].merge(node)
        self.nodes[node.id] = node
        return node

    def add_edge(self, edge: Edge) -> Edge:
        # Tolerate edges added before their endpoints (extractors are async)
        if edge.key in self.edges:
            self.edges[edge.key].merge(edge)
            return self.edges[edge.key]
        self.edges[edge.key] = edge
        self._adj_out[edge.source].append(edge.key)
        self._adj_in[edge.target].append(edge.key)
        return edge

    def add_evidence(self, ev: Evidence) -> Evidence:
        if ev.id in self.evidence:
            return self.evidence[ev.id]
        self.evidence[ev.id] = ev
        return ev

    def attach_evidence(self, edge_key: str, ev: Evidence) -> None:
        self.add_evidence(ev)
        edge = self.edges.get(edge_key)
        if edge and ev.id not in edge.evidence:
            edge.evidence.append(ev.id)

    # ── query helpers ────────────────────────────────────────────────────

    def get(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def by_type(self, t: NodeType) -> Iterator[Node]:
        return (n for n in self.nodes.values() if n.type == t)

    def neighbors(
        self,
        node_id: str,
        *,
        edge_type: Optional[EdgeType] = None,
        direction: str = "both",
    ) -> List[str]:
        out: List[str] = []
        if direction in ("out", "both"):
            for k in self._adj_out.get(node_id, []):
                e = self.edges.get(k)
                if e and (edge_type is None or e.type == edge_type):
                    out.append(e.target)
        if direction in ("in", "both"):
            for k in self._adj_in.get(node_id, []):
                e = self.edges.get(k)
                if e and (edge_type is None or e.type == edge_type):
                    out.append(e.source)
        return out

    def edges_for(self, node_id: str) -> List[Edge]:
        keys = list(self._adj_out.get(node_id, [])) + list(self._adj_in.get(node_id, []))
        return [self.edges[k] for k in keys if k in self.edges]

    # ── derived metrics ──────────────────────────────────────────────────

    def recompute_node_confidences(self) -> None:
        """For Skill / Technology / Concept nodes, set confidence = aggregate
        over incoming EVIDENCES / USES / IMPLEMENTS edges' weights."""
        for node in self.nodes.values():
            if node.type not in (
                NodeType.SKILL,
                NodeType.TECHNOLOGY,
                NodeType.CONCEPT,
                NodeType.METHODOLOGY,
            ):
                continue
            in_keys = self._adj_in.get(node.id, [])
            weights = []
            for k in in_keys:
                e = self.edges.get(k)
                if not e:
                    continue
                if e.type in (EdgeType.EVIDENCES, EdgeType.USES, EdgeType.IMPLEMENTS):
                    weights.append(e.weight)
            if weights:
                node.confidence = aggregate_confidence(weights)

    # ── serialization ────────────────────────────────────────────────────

    def stats(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for n in self.nodes.values():
            counts[f"node:{n.type.value}"] += 1
        for e in self.edges.values():
            counts[f"edge:{e.type.value}"] += 1
        counts["nodes_total"] = len(self.nodes)
        counts["edges_total"] = len(self.edges)
        counts["evidence_total"] = len(self.evidence)
        return dict(counts)

    def to_dict(self, *, include_evidence: bool = True) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
            "metadata": dict(self.metadata),
        }
        if include_evidence:
            out["evidence"] = [ev.to_dict() for ev in self.evidence.values()]
        return out

    def save_json(self, path: str | Path, *, include_evidence: bool = True) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(include_evidence=include_evidence), indent=2))
        logger.info("Saved universal graph to %s (%s nodes, %s edges)",
                    path, len(self.nodes), len(self.edges))
        return path

    @classmethod
    def load_json(cls, path: str | Path) -> "UniversalGraph":
        data = json.loads(Path(path).read_text())
        g = cls()
        for nd in data.get("nodes", []):
            g.add_node(Node(
                id=nd["id"],
                type=NodeType(nd["type"]),
                label=nd.get("label", nd["id"]),
                slug=nd.get("slug", ""),
                properties=nd.get("properties", {}),
                tags=nd.get("tags", []),
                confidence=nd.get("confidence", 1.0),
                career_value=nd.get("career_value"),
                provider=nd.get("provider"),
            ))
        for ed in data.get("edges", []):
            g.add_edge(Edge(
                source=ed["from"],
                target=ed["to"],
                type=EdgeType(ed["type"]),
                weight=ed.get("weight", 1.0),
                properties=ed.get("properties", {}),
                evidence=ed.get("evidence", []),
            ))
        for ev in data.get("evidence", []):
            from .evidence import EvidenceType  # local
            g.add_evidence(Evidence(
                evidence_type=EvidenceType(ev["evidence_type"]),
                source_node_id=ev["source_node_id"],
                locator=ev["locator"],
                excerpt=ev.get("excerpt", ""),
                confidence=ev.get("confidence"),
                extra=ev.get("extra", {}),
                id=ev.get("id", ""),
            ))
        return g
