"""MCP context endpoint — /api/mcp/context.

Universal subgraph endpoint consumed by the MCP UI layer (e.g.
``careergraph-wiki-mcp-ui`` and ``khiw.dev``). Given a query string, a
section hint (``project_card``, ``skill_panel``, ``timeline``,
``repo_deep_dive``, ``concept_map``), and/or a focal node id, returns:

- a tightly scoped subgraph (nodes + edges sized for one UI section)
- a primary node id (the "main" thing the section is about)
- a pre-rendered markdown snippet (the section can render it directly when
  the frontend is just a chat surface)
- the supporting evidence rows

The endpoint loads the universal graph from
``data/graph/knowledge_graph.json`` (cached in memory) so it works against
the same artifact the wiki app's GraphConnector already reads.
"""
from __future__ import annotations

import logging
import os
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..schema import (
    Edge,
    EdgeType,
    Node,
    NodeType,
    UniversalGraph,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


# ── graph caching ─────────────────────────────────────────────────────────

_GRAPH_CACHE: Dict[str, Tuple[float, UniversalGraph]] = {}
DEFAULT_GRAPH_PATH = os.getenv(
    "UNIVERSAL_GRAPH_PATH", "data/graph/knowledge_graph.json"
)


def _load_graph(path: str = DEFAULT_GRAPH_PATH) -> UniversalGraph:
    p = Path(path)
    if not p.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Universal graph not built yet: {path} not found. "
                   "Run scripts/build_universal_graph.py.",
        )
    mtime = p.stat().st_mtime
    cached = _GRAPH_CACHE.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    g = UniversalGraph.load_json(p)
    _GRAPH_CACHE[path] = (mtime, g)
    return g


# ── request / response models ─────────────────────────────────────────────

SectionHint = Literal[
    "project_card",
    "skill_panel",
    "repo_deep_dive",
    "timeline",
    "concept_map",
    "auto",
]


class MCPContextRequest(BaseModel):
    query: Optional[str] = Field(
        None, description="Natural-language hint for the section"
    )
    node_id: Optional[str] = Field(
        None, description="Focal node id; takes precedence over query"
    )
    section_hint: SectionHint = "auto"
    limit_nodes: int = Field(30, ge=1, le=300)
    limit_edges: int = Field(60, ge=1, le=600)
    hops: int = Field(2, ge=1, le=4, description="BFS depth from focal node")


class MCPNodeOut(BaseModel):
    id: str
    type: str
    label: str
    slug: str
    tags: List[str] = []
    confidence: float = 1.0
    provider: Optional[str] = None
    properties: Dict[str, Any] = {}


class MCPEdgeOut(BaseModel):
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    type: str
    weight: float = 1.0
    evidence: List[str] = []

    class Config:
        populate_by_name = True


class MCPEvidenceOut(BaseModel):
    id: str
    evidence_type: str
    locator: str
    excerpt: str
    confidence: float


class MCPContextResponse(BaseModel):
    primary_node_id: Optional[str]
    section_hint: SectionHint
    nodes: List[MCPNodeOut]
    edges: List[MCPEdgeOut]
    evidence: List[MCPEvidenceOut]
    rendered_markdown: str
    summary: str
    stats: Dict[str, int]


# ── focal-node selection ─────────────────────────────────────────────────

def _pick_focal_node(g: UniversalGraph, req: MCPContextRequest) -> Optional[Node]:
    if req.node_id:
        n = g.get(req.node_id)
        if n:
            return n
        # fall through to query-based search
    if not req.query:
        # No query, no node — return the highest-degree REPO/PROJECT
        return _top_node_by_degree(g, {NodeType.REPO, NodeType.PROJECT, NodeType.PERSON})

    q = req.query.lower()
    # 1) section_hint biases the candidate types
    type_bias = {
        "project_card": {NodeType.PROJECT, NodeType.REPO},
        "skill_panel": {NodeType.SKILL, NodeType.TECHNOLOGY},
        "repo_deep_dive": {NodeType.REPO},
        "timeline": {NodeType.CAREER_PHASE, NodeType.TIMELINE_EVENT, NodeType.REPO},
        "concept_map": {NodeType.CONCEPT, NodeType.METHODOLOGY, NodeType.KNOWLEDGE_DOMAIN},
        "auto": set(NodeType),
    }.get(req.section_hint, set(NodeType))

    best: Optional[Node] = None
    best_score = -1.0
    for n in g.nodes.values():
        if n.type not in type_bias:
            continue
        score = _match_score(n, q)
        if score > best_score:
            best_score = score
            best = n
    return best if best_score > 0 else _top_node_by_degree(g, type_bias)


def _match_score(n: Node, q: str) -> float:
    score = 0.0
    label = (n.label or "").lower()
    if q == label:
        score += 5.0
    elif q in label or label in q:
        score += 3.0
    for tag in n.tags:
        if q == tag.lower():
            score += 2.0
        elif q in tag.lower():
            score += 1.0
    desc = str(n.properties.get("description", "")).lower()
    if q in desc:
        score += 1.5
    summary = str(n.properties.get("llm_summary", "")).lower()
    if q in summary:
        score += 1.0
    if score > 0:
        score *= max(0.5, n.confidence)
    return score


def _top_node_by_degree(g: UniversalGraph, types: Set[NodeType]) -> Optional[Node]:
    best, best_deg = None, -1
    for n in g.nodes.values():
        if n.type not in types:
            continue
        deg = len(g._adj_out.get(n.id, [])) + len(g._adj_in.get(n.id, []))
        if deg > best_deg:
            best_deg = deg
            best = n
    return best


# ── subgraph extraction ──────────────────────────────────────────────────

def _bfs_subgraph(
    g: UniversalGraph,
    focal: Node,
    *,
    hops: int,
    limit_nodes: int,
    limit_edges: int,
    section_hint: SectionHint,
) -> Tuple[List[Node], List[Edge]]:
    """Bounded BFS that biases towards edge types most useful for the section."""
    preferred_edges = _preferred_edges_for(section_hint)
    visited: Set[str] = {focal.id}
    out_nodes: List[Node] = [focal]
    out_edges: List[Edge] = []
    queue = deque([(focal.id, 0)])

    while queue and len(out_nodes) < limit_nodes and len(out_edges) < limit_edges:
        node_id, depth = queue.popleft()
        if depth >= hops:
            continue
        edges = g.edges_for(node_id)
        # rank edges by section preference + weight
        edges.sort(key=lambda e: (
            0 if e.type in preferred_edges else 1,
            -e.weight,
        ))
        for e in edges:
            if len(out_edges) >= limit_edges:
                break
            other = e.target if e.source == node_id else e.source
            if other not in visited and len(out_nodes) < limit_nodes:
                node = g.get(other)
                if node:
                    out_nodes.append(node)
                    visited.add(other)
                    queue.append((other, depth + 1))
            if other in visited:
                out_edges.append(e)
    return out_nodes, out_edges


def _preferred_edges_for(section_hint: SectionHint) -> Set[EdgeType]:
    return {
        "project_card": {EdgeType.USES, EdgeType.IMPLEMENTS, EdgeType.DEPLOYS_TO,
                         EdgeType.CONTAINS, EdgeType.AUTHORED, EdgeType.DOCUMENTS},
        "skill_panel": {EdgeType.EVIDENCES, EdgeType.USES, EdgeType.IMPLEMENTS,
                        EdgeType.BELONGS_TO_DOMAIN},
        "repo_deep_dive": {EdgeType.CONTAINS, EdgeType.DEFINES, EdgeType.IMPORTS,
                           EdgeType.CALLS, EdgeType.USES, EdgeType.DOCUMENTS},
        "timeline": {EdgeType.OCCURRED_DURING, EdgeType.PRECEDES,
                     EdgeType.EVOLVED_INTO, EdgeType.AUTHORED},
        "concept_map": {EdgeType.IMPLEMENTS, EdgeType.RELATED_TO,
                        EdgeType.BELONGS_TO_DOMAIN, EdgeType.MENTIONS},
    }.get(section_hint, {EdgeType.USES, EdgeType.IMPLEMENTS, EdgeType.CONTAINS,
                         EdgeType.EVIDENCES})


# ── markdown rendering per section type ──────────────────────────────────

def _render_markdown(
    section_hint: SectionHint,
    focal: Node,
    nodes: List[Node],
    edges: List[Edge],
    g: UniversalGraph,
) -> Tuple[str, str]:
    by_id: Dict[str, Node] = {n.id: n for n in nodes}

    def fmt(node_id: str) -> str:
        n = by_id.get(node_id) or g.get(node_id)
        return n.label if n else node_id

    def edges_of(t: EdgeType, *, source: bool) -> List[Edge]:
        return [e for e in edges if e.type == t and (
            (source and e.source == focal.id) or (not source and e.target == focal.id))]

    summary_bits: List[str] = []
    md: List[str] = []

    if section_hint in ("project_card", "auto") and focal.type in (NodeType.REPO, NodeType.PROJECT):
        md.append(f"## {focal.label}")
        desc = focal.properties.get("description") or focal.properties.get("llm_summary")
        if desc:
            md.append(str(desc))
        techs = sorted({fmt(e.target) for e in edges_of(EdgeType.USES, source=True)})
        if techs:
            md.append("\n**Stack**: " + ", ".join(techs[:12]))
        concepts = sorted({fmt(e.target) for e in edges_of(EdgeType.IMPLEMENTS, source=True)})
        if concepts:
            md.append("\n**Implements**: " + ", ".join(concepts[:8]))
        deploys = [fmt(e.target) for e in edges_of(EdgeType.DEPLOYS_TO, source=True)]
        if deploys:
            md.append("\n**Deployed to**: " + ", ".join(deploys[:5]))
        summary_bits = [focal.label, *techs[:5]]

    elif section_hint == "skill_panel" or focal.type in (NodeType.SKILL, NodeType.TECHNOLOGY):
        md.append(f"## {focal.label}")
        md.append(f"**Confidence:** {focal.confidence:.2f}")
        # incoming evidence (USES / EVIDENCES / IMPLEMENTS pointing at this)
        incoming = [e for e in edges if e.target == focal.id]
        backers = sorted({fmt(e.source) for e in incoming})
        if backers:
            md.append("\n**Backed by:**")
            for b in backers[:15]:
                md.append(f"- {b}")
        summary_bits = [focal.label, f"used in {len(backers)} project(s)"]

    elif section_hint == "repo_deep_dive" or focal.type == NodeType.REPO:
        md.append(f"## {focal.label} — deep dive")
        files = [fmt(e.target) for e in edges_of(EdgeType.CONTAINS, source=True)
                 if (by_id.get(e.target) or g.get(e.target) or focal).type == NodeType.FILE]
        if files:
            md.append(f"\n**Files** ({len(files)} surfaced): " + ", ".join(files[:15]))
        techs = sorted({fmt(e.target) for e in edges_of(EdgeType.USES, source=True)})
        if techs:
            md.append("\n**Stack**: " + ", ".join(techs[:20]))
        summary_bits = [focal.label, "deep dive"]

    elif section_hint == "concept_map" or focal.type in (NodeType.CONCEPT, NodeType.METHODOLOGY, NodeType.KNOWLEDGE_DOMAIN):
        md.append(f"## {focal.label}")
        related = [fmt(e.target) for e in edges if e.source == focal.id and e.type == EdgeType.RELATED_TO]
        backers = [fmt(e.source) for e in edges if e.target == focal.id]
        if backers:
            md.append("\n**Where it shows up:**")
            for b in sorted(set(backers))[:12]:
                md.append(f"- {b}")
        if related:
            md.append("\n**Related concepts:** " + ", ".join(sorted(set(related))[:10]))
        summary_bits = [focal.label]

    else:
        md.append(f"## {focal.label}")
        md.append(f"_Type: {focal.type.value}_")
        for e in edges[:15]:
            md.append(f"- {fmt(e.source)} —{e.type.value}→ {fmt(e.target)}")
        summary_bits = [focal.label]

    return "\n".join(md).strip(), " · ".join(summary_bits)


# ── route ────────────────────────────────────────────────────────────────

@router.post("/context", response_model=MCPContextResponse)
def mcp_context(req: MCPContextRequest) -> MCPContextResponse:
    g = _load_graph()
    focal = _pick_focal_node(g, req)
    if focal is None:
        raise HTTPException(status_code=404, detail="No focal node found for query")

    sub_nodes, sub_edges = _bfs_subgraph(
        g, focal,
        hops=req.hops,
        limit_nodes=req.limit_nodes,
        limit_edges=req.limit_edges,
        section_hint=req.section_hint,
    )

    # Auto-pick a section if requested
    section = req.section_hint
    if section == "auto":
        section = _auto_section(focal)

    md, summary = _render_markdown(section, focal, sub_nodes, sub_edges, g)

    # Collect evidence rows referenced by the returned edges
    ev_ids: Set[str] = set()
    for e in sub_edges:
        for evid in e.evidence:
            ev_ids.add(evid)
    ev_rows = []
    for eid in list(ev_ids)[:50]:
        ev = g.evidence.get(eid)
        if ev:
            ev_rows.append(MCPEvidenceOut(
                id=ev.id,
                evidence_type=ev.evidence_type.value,
                locator=ev.locator,
                excerpt=ev.excerpt,
                confidence=ev.confidence or 0.0,
            ))

    return MCPContextResponse(
        primary_node_id=focal.id,
        section_hint=section,
        nodes=[MCPNodeOut(
            id=n.id, type=n.type.value, label=n.label, slug=n.slug,
            tags=list(n.tags), confidence=n.confidence,
            provider=n.provider, properties=n.properties,
        ) for n in sub_nodes],
        edges=[MCPEdgeOut(
            **{"from": e.source, "to": e.target},
            type=e.type.value, weight=e.weight, evidence=list(e.evidence),
        ) for e in sub_edges],
        evidence=ev_rows,
        rendered_markdown=md,
        summary=summary,
        stats={"nodes": len(sub_nodes), "edges": len(sub_edges),
               "evidence": len(ev_rows)},
    )


def _auto_section(n: Node) -> SectionHint:
    return {
        NodeType.REPO: "repo_deep_dive",
        NodeType.PROJECT: "project_card",
        NodeType.SKILL: "skill_panel",
        NodeType.TECHNOLOGY: "skill_panel",
        NodeType.CONCEPT: "concept_map",
        NodeType.METHODOLOGY: "concept_map",
        NodeType.KNOWLEDGE_DOMAIN: "concept_map",
        NodeType.CAREER_PHASE: "timeline",
        NodeType.TIMELINE_EVENT: "timeline",
    }.get(n.type, "project_card")


@router.get("/health")
def mcp_health() -> Dict[str, Any]:
    """Quick sanity check + graph stats."""
    try:
        g = _load_graph()
        return {"status": "ok", "stats": g.stats()}
    except HTTPException as e:
        return {"status": "no_graph", "detail": e.detail}
