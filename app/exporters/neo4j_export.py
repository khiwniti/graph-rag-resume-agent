"""Neo4j exporter for the UniversalGraph.

Pushes nodes / edges / evidence directly to a Neo4j database (Aura cloud or
self-hosted). Uses the universal schema as Neo4j labels and relationship
types — no translation needed.

Mapping:
NodeType.value (e.g. "repo", "skill") -> Label "Repo", "Skill"
EdgeType.value (e.g. "USES") -> Relationship type "USES"

Every node gets the secondary label ``:UniversalNode`` so you can wipe just
the universal-graph data without touching anything else::

    MATCH (n:UniversalNode) DETACH DELETE n;

Evidence rows become ``:Evidence`` nodes connected via
``(:Evidence)-[:SUPPORTS]->(...)`` to whichever node the original evidence's
``source_node_id`` pointed to, AND attached to the edges they back via an
``evidence_ids`` array property on the edge itself.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from ..schema import Edge, EdgeType, NodeType, UniversalGraph

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
    profile: Optional[str] = None,
    implements_top_n: int = 10,
    documents_top_n: int = 10,
) -> Dict[str, int]:
    """Push the universal graph to Neo4j. Returns stats.

    Credentials default to ``NEO4J_URI`` / ``NEO4J_USER`` / ``NEO4J_PASSWORD`` /
    ``NEO4J_DATABASE`` from the environment.

    Args:
        profile: Export profile - "full" (default) or "aura_free"
        implements_top_n: Max IMPLEMENTS edges per source (aura_free only)
        documents_top_n: Max DOCUMENTS edges per source (aura_free only)
    """
    if not _NEO4J_AVAILABLE:
        raise RuntimeError("neo4j driver not installed: pip install neo4j")

    uri = uri or os.getenv("NEO4J_URI")
    user = user or os.getenv("NEO4J_USER")
    password = password or os.getenv("NEO4J_PASSWORD")
    database = database or os.getenv("NEO4J_DATABASE", "neo4j")
    if not (uri and user and password):
        raise RuntimeError("NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD are required")

    # Resolve and validate profile before any IO
    resolved_profile = _resolve_profile(profile, env=os.getenv("NEO4J_PROFILE"))

    # Apply filter based on profile
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
                if node.id not in kept_nodes:
                    continue
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
                if edge.key not in kept_edges:
                    continue
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
                } for e in graph.evidence.values() if e.id in kept_evidence]
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
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Project a UniversalGraph down to the subset that fits Aura Free.

    Returns (kept_node_ids, kept_edge_keys, kept_evidence_ids). Pure function.

    Rules applied:
    1. Drop EdgeType.CALLS entirely.
    2. For each source node, keep only top-N IMPLEMENTS and DOCUMENTS edges by weight.
    3. Drop :function nodes that are orphaned after CALLS removal.
    4. Keep evidence only if its source_node_id is retained OR cited by a retained edge.
    """
    # Step 1: Drop CALLS edges, cap IMPLEMENTS/DOCUMENTS per source
    capped_types = {
        EdgeType.IMPLEMENTS: implements_top_n,
        EdgeType.DOCUMENTS: documents_top_n,
    }

    by_source_capped: Dict[Tuple[str, EdgeType], List[Tuple[float, str, str]]] = {}
    kept_edges: Set[str] = set()

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

    # Step 2: Prune orphan function nodes (only referenced by CALLS edges)
    referenced_by_kept_edge: Set[str] = set()
    for key in kept_edges:
        edge = graph.edges[key]
        referenced_by_kept_edge.add(edge.source)
        referenced_by_kept_edge.add(edge.target)

    kept_nodes: Set[str] = set()
    for node_id, node in graph.nodes.items():
        if node.type is NodeType.FUNCTION and node_id not in referenced_by_kept_edge:
            continue
        kept_nodes.add(node_id)

    # Step 3: Restrict evidence to retained subgraph
    cited_by_kept_edge: Set[str] = set()
    for key in kept_edges:
        cited_by_kept_edge.update(graph.edges[key].evidence)

    kept_evidence: Set[str] = set()
    for ev_id, ev in graph.evidence.items():
        if ev.source_node_id in kept_nodes or ev_id in cited_by_kept_edge:
            kept_evidence.add(ev_id)

    return kept_nodes, kept_edges, kept_evidence


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
    kept_nodes: Set[str],
    kept_edges: Set[str],
    kept_evidence: Set[str],
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
