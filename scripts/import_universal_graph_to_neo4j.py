"""Import a compact UniversalGraph JSON into Neo4j for API-backed skills/projects.

This is intentionally "Aura Free Tier" friendly:
- Imports only Person, Project, Skill and their relationships.
- Does NOT import file/function/class nodes.

Source of truth: data/graph/knowledge_graph.json (UniversalGraph JSON).

Usage:
  python scripts/import_universal_graph_to_neo4j.py \
    --graph data/graph/knowledge_graph.json \
    --person-id me \
    --person-name "Me" \
    --clear

Notes:
- Conversation artifacts are not imported (they're absent from the UniversalGraph runner).
- Idempotent via MERGE; optional --clear wipes Neo4j first.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Dict, Any

# Ensure repo root is on sys.path when running as a script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.graph_store import Neo4jStore, KnowledgeGraphConfig
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
from app.schema.graph import UniversalGraph
from app.schema.nodes import NodeType
from app.schema.edges import EdgeType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def build_skill_usage_counts(g: UniversalGraph) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in g.edges.values():
        if e.type == EdgeType.USES:
            counts[e.target] = counts.get(e.target, 0) + 1
    return counts


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--graph", default="data/graph/knowledge_graph.json")
    p.add_argument("--person-id", default="me")
    p.add_argument("--person-name", default="me")
    p.add_argument("--clear", action="store_true", help="DANGEROUS: delete all nodes/edges in Neo4j first")
    args = p.parse_args()

    g = UniversalGraph.load_json(args.graph)
    usage_counts = build_skill_usage_counts(g)

    cfg = KnowledgeGraphConfig(
        uri=NEO4J_URI or "bolt://localhost:7687",
        user=NEO4J_USER or "neo4j",
        password=NEO4J_PASSWORD or "",
        database=NEO4J_DATABASE or "neo4j",
    )

    with Neo4jStore(cfg) as store:
        store.create_constraints()
        store.create_indexes()

        if args.clear:
            logger.warning("Clearing Neo4j database (MATCH (n) DETACH DELETE n)")
            store.clear()

        def chunks(seq, size: int):
            for i in range(0, len(seq), size):
                yield seq[i : i + size]

        # Person
        store.upsert_person(person_id=args.person_id, name=args.person_name)

        # -------------------------------
        # Projects (batch UNWIND)
        # -------------------------------
        project_nodes = [n for n in g.nodes.values() if n.type in (NodeType.REPO, NodeType.DEPLOYMENT)]
        projects_payload = []
        for n in project_nodes:
            props = n.properties or {}
            projects_payload.append(
                {
                    "id": n.id,
                    "name": n.label,
                    "description": _safe_str(props.get("description") or props.get("summary") or ""),
                    "source": n.provider or ("github" if n.type == NodeType.REPO else "deployment"),
                    "url": _safe_str(props.get("url") or props.get("html_url") or props.get("production_url") or ""),
                    "pushed_at": _safe_str(props.get("pushed_at") or props.get("updated_at") or props.get("updated") or ""),
                }
            )

        logger.info("Importing %d projects", len(projects_payload))
        project_query = f"""
        UNWIND $rows AS row
        MERGE (p:{store.PROJECT} {{id: row.id}})
        SET p.name = row.name,
            p.description = row.description,
            p.source = row.source,
            p.url = row.url,
            p.pushed_at = row.pushed_at,
            p.updated_at = datetime()
        WITH p
        MATCH (me:{store.PERSON} {{id: $person_id}})
        MERGE (me)-[r:{store.OWNS}]->(p)
        SET r.created_at = coalesce(r.created_at, datetime())
        """
        with store.driver.session() as session:
            for batch in chunks(projects_payload, 500):
                session.run(project_query, {"rows": batch, "person_id": args.person_id}).consume()

        # -------------------------------
        # Skills + Person->Skill (batch UNWIND)
        # -------------------------------
        tech_nodes = [n for n in g.nodes.values() if n.type == NodeType.TECHNOLOGY]
        skills_payload = []
        for n in tech_nodes:
            category = n.id  # stable unique category (e.g., tech:react)
            count = usage_counts.get(n.id, 0)
            skills_payload.append(
                {
                    "name": n.label,
                    "category": category,
                    "confidence": float(n.confidence or 0.0),
                    "evidence": f"Used in {count} projects" if count else "",
                }
            )

        logger.info("Importing %d skills (from Technology nodes)", len(skills_payload))
        skill_query = f"""
        UNWIND $rows AS row
        MERGE (s:{store.SKILL} {{name: row.name, category: row.category}})
        SET s.confidence = row.confidence,
            s.updated_at = datetime()
        WITH s, row
        MATCH (me:{store.PERSON} {{id: $person_id}})
        MERGE (me)-[r:{store.HAS_SKILL}]->(s)
        SET r.confidence = row.confidence,
            r.evidence = row.evidence,
            r.updated_at = datetime()
        """
        with store.driver.session() as session:
            for batch in chunks(skills_payload, 500):
                session.run(skill_query, {"rows": batch, "person_id": args.person_id}).consume()

        # -------------------------------
        # Project -> Skill edges (from uses edges) (batch UNWIND)
        # -------------------------------
        edges_payload = []
        for e in g.edges.values():
            if e.type != EdgeType.USES:
                continue
            tech_node = g.nodes.get(e.target)
            if not tech_node or tech_node.type != NodeType.TECHNOLOGY:
                continue
            edges_payload.append(
                {
                    "project_id": e.source,
                    "skill_name": tech_node.label,
                    "category": tech_node.id,
                    "evidence": _safe_str((e.properties or {}).get("evidence") or ""),
                }
            )

        logger.info("Linking %d project->skill edges", len(edges_payload))
        edge_query = f"""
        UNWIND $rows AS row
        MATCH (p:{store.PROJECT} {{id: row.project_id}})
        MATCH (s:{store.SKILL} {{name: row.skill_name, category: row.category}})
        MERGE (p)-[r:{store.REQUIRES_SKILL}]->(s)
        SET r.evidence = coalesce(r.evidence, row.evidence),
            r.updated_at = datetime()
        """
        with store.driver.session() as session:
            for batch in chunks(edges_payload, 1000):
                session.run(edge_query, {"rows": batch}).consume()

        stats = store.get_stats()
        logger.info("Neo4j stats after import: %s", stats)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
