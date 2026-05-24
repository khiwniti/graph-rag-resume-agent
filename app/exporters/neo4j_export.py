"""Neo4j exporter for the UniversalGraph.

Pushes nodes / edges / evidence directly to a Neo4j database (Aura cloud or
self-hosted). Uses the universal schema as Neo4j labels and relationship
types — no translation needed.

Mapping:
    NodeType.value (e.g. "repo", "skill")  -> Label  "Repo", "Skill"
    EdgeType.value (e.g. "USES")           -> Relationship type "USES"

Every node gets the secondary label ``:UniversalNode`` so you can wipe just
the universal-graph data without touching anything else::

    MATCH (n:UniversalNode) DETACH DELETE n;

Evidence rows become ``:Evidence`` nodes connected via
``(:Evidence)-[:SUPPORTS]->(...)`` to whichever node the original evidence's
``source_node_id`` pointed to, AND attached to the edges they back via an
``evidence_ids`` array property on the edge itself.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..schema import Edge, NodeType, UniversalGraph

logger = logging.getLogger(__name__)

try:
    from neo4j import GraphDatabase, Driver
    _NEO4J_AVAILABLE = True
except ImportError:  # pragma: no cover
    GraphDatabase = None
    Driver = None
    _NEO4J_AVAILABLE = False


# Batch sizes (Aura free tier handles ~10k transactions/s for small payloads)
_NODE_BATCH = 500
_EDGE_BATCH = 500
_EV_BATCH = 500


def _label(node_type: NodeType) -> str:
    return "".join(part.capitalize() for part in node_type.value.split("_"))


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
    """Push the universal graph to Neo4j. Returns stats.

    Credentials default to ``NEO4J_URI`` / ``NEO4J_USER`` / ``NEO4J_PASSWORD`` /
    ``NEO4J_DATABASE`` from the environment.
    """
    if not _NEO4J_AVAILABLE:
        raise RuntimeError("neo4j driver not installed: pip install neo4j")

    uri = uri or os.getenv("NEO4J_URI")
    user = user or os.getenv("NEO4J_USER")
    password = password or os.getenv("NEO4J_PASSWORD")
    database = database or os.getenv("NEO4J_DATABASE", "neo4j")
    if not (uri and user and password):
        raise RuntimeError("NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD are required")

    logger.info("Connecting to Neo4j at %s (db=%s)", uri, database)
    driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
    stats = {"nodes": 0, "edges": 0, "evidence": 0}

    try:
        with driver.session(database=database) as session:
            session.run("RETURN 1").consume()  # connectivity check

            if wipe_first:
                logger.warning("Wiping :UniversalNode subgraph first")
                session.run("MATCH (n:UniversalNode) DETACH DELETE n").consume()
                session.run("MATCH (e:Evidence) DETACH DELETE e").consume()

            _ensure_constraints(session)

            # 1) Nodes — one batched UNWIND per label so we can apply the
            # correct label statically.
            nodes_by_label: Dict[str, List[Dict[str, Any]]] = {}
            for node in graph.nodes.values():
                nodes_by_label.setdefault(_label(node.type), []).append({
                    "id": node.id,
                    "label": node.label,
                    "slug": node.slug,
                    "tags": list(node.tags),
                    "provider": node.provider,
                    "confidence": float(node.confidence),
                    "career_value": node.career_value,
                    "created": node.created.isoformat() if node.created else None,
                    "updated": node.updated.isoformat() if node.updated else None,
                    "props": _flatten_props(node.properties),
                })

            for label, batch in nodes_by_label.items():
                for chunk in _chunks(batch, _NODE_BATCH):
                    session.run(
                        f"""
                        UNWIND $rows AS row
                        MERGE (n:UniversalNode:{label} {{id: row.id}})
                        SET n.label = row.label,
                            n.slug = row.slug,
                            n.tags = row.tags,
                            n.provider = row.provider,
                            n.confidence = row.confidence,
                            n.career_value = row.career_value,
                            n.created = row.created,
                            n.updated = row.updated,
                            n += row.props
                        """,
                        rows=chunk,
                    ).consume()
                    stats["nodes"] += len(chunk)

            # 2) Edges — group by relationship type for the same reason.
            edges_by_type: Dict[str, List[Dict[str, Any]]] = {}
            for edge in graph.edges.values():
                edges_by_type.setdefault(edge.type.value, []).append({
                    "from": edge.source,
                    "to": edge.target,
                    "weight": float(edge.weight),
                    "evidence_ids": list(edge.evidence),
                    "props": _flatten_props(edge.properties),
                })

            for rel_type, batch in edges_by_type.items():
                for chunk in _chunks(batch, _EDGE_BATCH):
                    session.run(
                        f"""
                        UNWIND $rows AS row
                        MATCH (a:UniversalNode {{id: row.from}})
                        MATCH (b:UniversalNode {{id: row.to}})
                        MERGE (a)-[r:`{rel_type}`]->(b)
                        SET r.weight = row.weight,
                            r.evidence_ids = row.evidence_ids,
                            r += row.props
                        """,
                        rows=chunk,
                    ).consume()
                    stats["edges"] += len(chunk)

            # 3) Evidence nodes (optional)
            if include_evidence and graph.evidence:
                ev_rows = [{
                    "id": e.id,
                    "evidence_type": e.evidence_type.value,
                    "source_node_id": e.source_node_id,
                    "locator": e.locator,
                    "excerpt": (e.excerpt or "")[:1024],
                    "confidence": float(e.confidence or 0.0),
                    "extracted_at": e.extracted_at.isoformat() if e.extracted_at else None,
                } for e in graph.evidence.values()]
                for chunk in _chunks(ev_rows, _EV_BATCH):
                    session.run(
                        """
                        UNWIND $rows AS row
                        MERGE (ev:Evidence {id: row.id})
                        SET ev.evidence_type = row.evidence_type,
                            ev.locator = row.locator,
                            ev.excerpt = row.excerpt,
                            ev.confidence = row.confidence,
                            ev.extracted_at = row.extracted_at,
                            ev.source_node_id = row.source_node_id
                        WITH ev, row
                        OPTIONAL MATCH (src:UniversalNode {id: row.source_node_id})
                        FOREACH (_ IN CASE WHEN src IS NULL THEN [] ELSE [1] END |
                            MERGE (ev)-[:SUPPORTS]->(src)
                        )
                        """,
                        rows=chunk,
                    ).consume()
                    stats["evidence"] += len(chunk)
    finally:
        driver.close()

    logger.info("Neo4j export complete: %s", stats)
    return stats


# ── helpers ───────────────────────────────────────────────────────────────


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


def _ensure_constraints(session) -> None:
    # Single unique-id constraint covers every label thanks to :UniversalNode.
    session.run(
        "CREATE CONSTRAINT universal_node_id IF NOT EXISTS "
        "FOR (n:UniversalNode) REQUIRE n.id IS UNIQUE"
    ).consume()
    session.run(
        "CREATE CONSTRAINT evidence_id IF NOT EXISTS "
        "FOR (e:Evidence) REQUIRE e.id IS UNIQUE"
    ).consume()
    # Helpful lookup indexes
    session.run(
        "CREATE INDEX universal_node_slug IF NOT EXISTS "
        "FOR (n:UniversalNode) ON (n.slug)"
    ).consume()
    session.run(
        "CREATE INDEX universal_node_provider IF NOT EXISTS "
        "FOR (n:UniversalNode) ON (n.provider)"
    ).consume()


def _flatten_props(props: Dict[str, Any]) -> Dict[str, Any]:
    """Neo4j only accepts primitives & lists-of-primitives as property values.

    JSON-serialise anything more complex.
    """
    import json
    out: Dict[str, Any] = {}
    for k, v in (props or {}).items():
        if v is None or isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, list):
            if all(isinstance(x, (str, int, float, bool)) or x is None for x in v):
                out[k] = v
            else:
                out[k] = json.dumps(v, default=str)
        else:
            out[k] = json.dumps(v, default=str)
    return out


def _chunks(seq: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]
