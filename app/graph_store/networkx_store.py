"""NetworkX in-memory knowledge graph store — drop-in Neo4j fallback for Kaggle.

Supports the same node types and relationships as Neo4jStore but stores
everything in NetworkX graphs + Python dicts. No external service needed.

Node types: Person, Project, Skill, Technology, Deployment, Narrative,
            File, Function, Class, Module, Route, Config, Domain

Usage:
    from app.graph_store.networkx_store import NetworkXStore
    store = NetworkXStore()
    store.create_indexes()        # no-op, for compatibility
    store.upsert_project(...)     # same API as Neo4jStore
    stats = store.get_stats()     # dict of counts
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    nx = None
    _NX_AVAILABLE = False

logger = logging.getLogger(__name__)


class NetworkXStore:
    """NetworkX-based knowledge graph store with API matching Neo4jStore.

    All data lives in memory — ideal for Kaggle, Colab, or local testing
    without a Neo4j container.
    """

    # ── node labels (mirrors Neo4jStore) ──────────────────────────────────
    PERSON = "Person"
    PROJECT = "Project"
    SKILL = "Skill"
    TECHNOLOGY = "Technology"
    DEPLOYMENT = "Deployment"
    NARRATIVE = "Narrative"
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    MODULE = "Module"
    ROUTE = "Route"
    CONFIG = "Config"
    DOMAIN = "Domain"

    # ── relationship types ────────────────────────────────────────────────
    OWNS = "OWNS"
    HAS_SKILL = "HAS_SKILL"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    DEPLOYED_ON = "DEPLOYED_ON"
    REQUIRES_SKILL = "REQUIRES_SKILL"
    RELATED_TO = "RELATED_TO"
    DESCRIBED_BY = "DESCRIBED_BY"
    MENTIONS = "MENTIONS"
    CONTAINS_FILE = "CONTAINS_FILE"
    CONTAINS = "CONTAINS"
    CONTAINS_METHOD = "CONTAINS_METHOD"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPORTS = "IMPORTS"
    EXPOSES = "EXPOSES"
    HANDLED_BY = "HANDLED_BY"
    CONFIGURES = "CONFIGURES"
    HAS_DOMAIN = "HAS_DOMAIN"
    DOCUMENTED_BY = "DOCUMENTED_BY"

    def __init__(self, config: Any = None):
        """Initialize NetworkX store. config is accepted for API compat but unused."""
        if not _NX_AVAILABLE:
            raise ImportError(
                "networkx is required. Install with: pip install networkx"
            )
        self._graph = nx.DiGraph()
        self._connected = True

    # ── connection helpers (API compat) ────────────────────────────────────
    def connect(self) -> None:
        """No-op: NetworkX is always in memory."""

    def close(self) -> None:
        """No-op."""

    def clear(self) -> None:
        """Remove all nodes and edges."""
        self._graph.clear()

    @property
    def driver(self):
        """Return self for API compat with context-manager usage."""
        return self

    # ── schema setup (API compat) ──────────────────────────────────────────
    def create_indexes(self) -> None:
        """No-op."""

    def create_constraints(self) -> None:
        """No-op."""

    # ── person ─────────────────────────────────────────────────────────────
    def upsert_person(self, person_id: str, name: str = "",
                      email: str = "", properties: Dict = None) -> None:
        self._upsert_node("Person", {
            "id": person_id, "name": name, "email": email,
            "properties": properties or {},
        })

    # ── project ────────────────────────────────────────────────────────────
    def upsert_project(self, project_id: str, name: str, source: str = "",
                       url: str = "", description: str = "",
                       properties: Dict = None) -> None:
        self._upsert_node("Project", {
            "id": project_id, "name": name, "source": source,
            "url": url, "description": description,
            "properties": properties or {},
        })

    def link_person_to_project(self, person_id: str, project_id: str) -> None:
        self._add_edge("Person", person_id, "Project", project_id, self.OWNS)

    # ── skill ──────────────────────────────────────────────────────────────
    def _skill_key(self, name: str, category: str = "skill") -> str:
        """Consistent skill node ID."""
        return f"{name}|{category}"

    def upsert_skill(self, name: str, category: str = "skill",
                     confidence: float = 1.0, evidence: Any = None) -> None:
        key = self._skill_key(name, category)
        self._upsert_node("Skill", {
            "id": key, "name": name, "category": category,
            "confidence": confidence, "evidence": evidence,
        })

    def link_person_to_skill(self, person_id: str, skill_name: str,
                             skill_category: str = "skill",
                             confidence: float = 1.0,
                             evidence: str = "") -> None:
        skill_key = self._skill_key(skill_name, skill_category)
        self.upsert_skill(skill_name, skill_category, confidence)
        self._add_edge(
            "Person", person_id, "Skill", skill_key, self.HAS_SKILL,
            {"confidence": confidence, "evidence": evidence}
        )

    def link_skill_to_project(self, skill_name: str, skill_category: str,
                               project_id: str, evidence: str = "") -> None:
        skill_key = self._skill_key(skill_name, skill_category)
        self.upsert_skill(skill_name, skill_category)
        self._add_edge(
            "Project", project_id, "Skill", skill_key, self.REQUIRES_SKILL,
            {"evidence": evidence}
        )

    def get_person_skills(self, person_id: str) -> List[Dict[str, Any]]:
        """Get all skills linked to a person via HAS_SKILL edges."""
        results = []
        g = self._graph
        person_node = ("Person", person_id)
        if person_node not in g:
            return results
        for _, target, data in g.out_edges(person_node, data=True):
            if data.get("type") == self.HAS_SKILL and target[0] == "Skill":
                node = g.nodes.get(target, {})
                results.append({
                    "name": node.get("name", target[1].split("|")[0] if "|" in target[1] else target[1]),
                    "category": node.get("category", "skill"),
                    "confidence": data.get("confidence", node.get("confidence", 1.0)),
                    "evidence": data.get("evidence", ""),
                })
        return results

    def search_skills(self, category: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """Search skills, optionally filtered by category."""
        results = []
        for node_id, data in self._graph.nodes(data=True):
            if node_id[0] == "Skill":
                if not category or data.get("category", "") == category:
                    results.append(data)
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return results[:limit]

    def get_graph(self):
        """Public accessor for the NetworkX graph (preferred over _graph)."""
        return self._graph

    # ── technology ─────────────────────────────────────────────────────────
    def _tech_key(self, name: str) -> str:
        """Consistent technology node ID."""
        return name

    def upsert_technology(self, name: str, tech_type: str = "") -> None:
        key = self._tech_key(name)
        self._upsert_node("Technology", {
            "id": key, "name": name, "type": tech_type,
        })

    def link_project_to_technology(self, project_id: str, tech_name: str,
                                    evidence_type: str = "usage") -> None:
        tech_key = self._tech_key(tech_name)
        self.upsert_technology(tech_name)
        self._add_edge(
            "Project", project_id, "Technology", tech_key, self.USES_TECHNOLOGY,
            {"evidence_type": evidence_type}
        )

    # ── deployment ─────────────────────────────────────────────────────────
    def upsert_deployment(self, deployment_id: str, url: str = "",
                          platform: str = "", properties: Dict = None) -> None:
        self._upsert_node("Deployment", {
            "id": deployment_id, "url": url, "platform": platform,
            "properties": properties or {},
        })

    def link_project_to_deployment(self, project_id: str,
                                    deployment_id: str) -> None:
        self._add_edge(
            "Project", project_id, "Deployment", deployment_id, self.DEPLOYED_ON
        )

    # ── narrative ──────────────────────────────────────────────────────────
    def upsert_narrative(self, narrative_id: str, text: str,
                         source_project_id: str = "",
                         period_start: str = "", period_end: str = "",
                         properties: Dict = None) -> None:
        self._upsert_node("Narrative", {
            "id": narrative_id, "text": text,
            "source_project_id": source_project_id,
            "period_start": period_start, "period_end": period_end,
            "properties": properties or {},
        })
        if source_project_id:
            self._add_edge(
                "Project", source_project_id, "Narrative", narrative_id,
                self.DESCRIBED_BY
            )

    def link_narrative_to_skill(self, narrative_id: str, skill_name: str,
                                 skill_category: str = "skill") -> None:
        skill_key = self._skill_key(skill_name, skill_category)
        self._add_edge(
            "Narrative", narrative_id, "Skill", skill_key, self.MENTIONS
        )

    def link_narrative_to_technology(self, narrative_id: str,
                                      technology_name: str) -> None:
        tech_key = self._tech_key(technology_name)
        self._add_edge(
            "Narrative", narrative_id, "Technology", tech_key, self.MENTIONS
        )

    # ── File ───────────────────────────────────────────────────────────────
    def upsert_file(self, file_id: str, path: str,
                    project_id: str = "", properties: Dict = None) -> None:
        self._upsert_node("File", {
            "id": file_id, "path": path, "project_id": project_id,
            "properties": properties or {},
        })
        if project_id:
            self._add_edge(
                "Project", project_id, "File", file_id, self.CONTAINS_FILE
            )

    def link_file_import(self, source_file_id: str,
                          imported_file_id: str) -> None:
        self._add_edge(
            "File", source_file_id, "File", imported_file_id, self.IMPORTS
        )

    def link_file_to_documentation(self, file_id: str,
                                    narrative_id: str) -> None:
        self._add_edge(
            "File", file_id, "Narrative", narrative_id, self.DOCUMENTED_BY
        )

    # ── Function ───────────────────────────────────────────────────────────
    def upsert_function(self, function_id: str, name: str, file_id: str = "",
                        signature: str = "", line_start: int = 0,
                        line_end: int = 0, properties: Dict = None) -> None:
        self._upsert_node("Function", {
            "id": function_id, "name": name, "file_id": file_id,
            "signature": signature, "line_start": line_start,
            "line_end": line_end, "properties": properties or {},
        })
        if file_id:
            self._add_edge(
                "File", file_id, "Function", function_id, self.CONTAINS
            )

    def link_function_call(self, caller_id: str, callee_id: str) -> None:
        self._add_edge(
            "Function", caller_id, "Function", callee_id, self.CALLS
        )

    # ── Class ──────────────────────────────────────────────────────────────
    def upsert_class(self, class_id: str, name: str, file_id: str = "",
                     bases: List[str] = None, line_start: int = 0,
                     line_end: int = 0, properties: Dict = None) -> None:
        self._upsert_node("Class", {
            "id": class_id, "name": name, "file_id": file_id,
            "bases": bases or [], "line_start": line_start,
            "line_end": line_end, "properties": properties or {},
        })
        if file_id:
            self._add_edge(
                "File", file_id, "Class", class_id, self.CONTAINS
            )

    def link_class_to_method(self, class_id: str, method_id: str) -> None:
        self._add_edge(
            "Class", class_id, "Function", method_id, self.CONTAINS_METHOD
        )

    def link_class_inheritance(self, child_class_id: str,
                                parent_class_id: str) -> None:
        self._add_edge(
            "Class", child_class_id, "Class", parent_class_id, self.INHERITS
        )

    # ── Route ──────────────────────────────────────────────────────────────
    def upsert_route(self, route_id: str, method: str = "GET",
                     path: str = "/", properties: Dict = None) -> None:
        self._upsert_node("Route", {
            "id": route_id, "method": method, "path": path,
            "properties": properties or {},
        })

    def link_project_to_route(self, project_id: str, route_id: str) -> None:
        self._add_edge(
            "Project", project_id, "Route", route_id, self.EXPOSES
        )

    # ── Config ─────────────────────────────────────────────────────────────
    def upsert_config(self, config_id: str, key: str = "", value: str = "",
                      config_type: str = "", properties: Dict = None) -> None:
        self._upsert_node("Config", {
            "id": config_id, "key": key, "value": value,
            "config_type": config_type, "properties": properties or {},
        })

    def link_project_to_config(self, project_id: str, config_id: str) -> None:
        self._add_edge(
            "Project", project_id, "Config", config_id, self.CONFIGURES
        )

    # ── Domain ─────────────────────────────────────────────────────────────
    def upsert_domain(self, name: str, properties: Dict = None) -> None:
        self._upsert_node("Domain", {
            "id": f"Domain|{name}", "name": name,
            "properties": properties or {},
        })

    def link_project_to_domain(self, project_id: str, domain_name: str) -> None:
        domain_key = f"Domain|{domain_name}"
        self.upsert_domain(domain_name)
        self._add_edge(
            "Project", project_id, "Domain", domain_key, self.HAS_DOMAIN
        )

    # ── stats ──────────────────────────────────────────────────────────────
    def get_stats(self) -> Dict[str, int]:
        """Return node counts by label."""
        counts: Dict[str, int] = defaultdict(int)
        for node_id in self._graph.nodes:
            label = node_id[0].lower()
            counts[label] += 1

        total_edges = self._graph.number_of_edges()
        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_relationships": total_edges,
            "persons": counts.get("person", 0),
            "projects": counts.get("project", 0),
            "skills": counts.get("skill", 0),
            "technologies": counts.get("technology", 0),
            "deployments": counts.get("deployment", 0),
            "narratives": counts.get("narrative", 0),
            "files": counts.get("file", 0),
            "functions": counts.get("function", 0),
            "classes": counts.get("class", 0),
            "modules": counts.get("module", 0),
            "routes": counts.get("route", 0),
            "configs": counts.get("config", 0),
            "domains": counts.get("domain", 0),
        }

    # ── export / viz helpers ───────────────────────────────────────────────
    def to_networkx(self) -> "nx.DiGraph":
        """Return the raw NetworkX DiGraph for visualization."""
        return self._graph

    def export_json(self) -> Dict[str, Any]:
        """Export graph as JSON-serializable dict."""
        nodes = []
        for node_id, data in self._graph.nodes(data=True):
            nodes.append({"id": "|".join(node_id), "label": node_id[0], **data})

        edges = []
        for u, v, data in self._graph.edges(data=True):
            edges.append({
                "source": "|".join(u), "target": "|".join(v),
                "type": data.get("type", ""),
            })

        return {"nodes": nodes, "edges": edges}

    # ── internal helpers ───────────────────────────────────────────────────
    def _upsert_node(self, label: str, data: Dict[str, Any]) -> None:
        """Insert or update a node."""
        node_id_key = data.get("id") or data.get("name", "")
        node_tuple = (label, node_id_key)
        if node_tuple in self._graph:
            self._graph.nodes[node_tuple].update(data)
        else:
            self._graph.add_node(node_tuple, **data)

    def _add_edge(self, src_label: str, src_id: str, tgt_label: str,
                  tgt_id: str, rel_type: str, data: Dict = None) -> None:
        """Add a typed relationship edge."""
        src = (src_label, src_id)
        tgt = (tgt_label, tgt_id)
        self._graph.add_edge(src, tgt, type=rel_type, **(data or {}))

    def __enter__(self) -> "NetworkXStore":
        return self

    def __exit__(self, *args) -> None:
        self.close()
