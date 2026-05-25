"""Markdown wiki vault exporter — Obsidian-style.

Walks a UniversalGraph and writes one ``.md`` page per node whose type maps
to a wiki folder (see ``NODE_TYPE_TO_WIKI_FOLDER``). Each page has:

  * YAML frontmatter (``title, type, slug, tags, provider, confidence,
    career_value, created, updated, synced_at``) — schema mirrors what
    careergraph-wiki-mcp-ui's parser expects.
  * Body sections built from outgoing/incoming edges, each formatted with
    ``[[wikilinks]]`` to other vault pages so the wiki graph viewer
    auto-discovers the link structure.
  * An ``Evidence`` section (when applicable) listing the audit trail.

Vault layout::

    data/wiki/
      index.md
      SCHEMA.md
      skills/<slug>.md
      concepts/<slug>.md
      projects/<slug>.md
      repos/<slug>.md
      docs/<slug>.md
      conversations/<slug>.md
      vercel/<slug>.md          (deployment provider subfolders)
      cloudflare/<slug>.md
      career/<slug>.md

Cross-page links are produced as ``[[<folder>/<slug>|<label>]]``. We use
relative paths (folder/slug) so the wiki app's parser can resolve them
unambiguously regardless of which page is rendered.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ..schema import (
    Edge,
    EdgeType,
    Evidence,
    Node,
    NodeType,
    NODE_TYPE_TO_WIKI_FOLDER,
    UniversalGraph,
)

logger = logging.getLogger(__name__)

DEFAULT_VAULT_DIR = Path("data/wiki")


# Edge -> (header, direction, target-must-be-in-vault?)
# For a given page (the "self" node), we walk its edges and group them under
# nicely-titled sections in the rendered markdown.
EDGE_RENDER_PLAN: Dict[EdgeType, Tuple[str, str]] = {
    # outgoing
    EdgeType.USES: ("Technologies / Stack", "out"),
    EdgeType.IMPLEMENTS: ("Concepts Implemented", "out"),
    EdgeType.EVIDENCES: ("Skills Evidenced", "out"),
    EdgeType.BELONGS_TO_DOMAIN: ("Knowledge Domains", "out"),
    EdgeType.DEPLOYS_TO: ("Deployments", "out"),
    EdgeType.SERVES: ("Serves", "out"),
    EdgeType.CONFIGURED_BY: ("Configured By", "out"),
    EdgeType.CONTAINS: ("Contains", "out"),
    EdgeType.AUTHORED: ("Authored", "out"),
    EdgeType.CONTRIBUTED_TO: ("Contributed To", "out"),
    EdgeType.OWNS: ("Owns", "out"),
    EdgeType.DOCUMENTS: ("Documents", "out"),
    EdgeType.MENTIONS: ("Mentions", "out"),
    EdgeType.LINKS_TO: ("Outgoing Links", "out"),
    EdgeType.RELATED_TO: ("Related", "out"),
    EdgeType.EVOLVED_INTO: ("Evolved Into", "out"),
    EdgeType.PRECEDES: ("Followed By", "out"),
    # incoming variants get rendered as "Backlinks" + per-type subsections
}


def export_wiki_vault(
    graph: UniversalGraph,
    output_dir: Optional[str | Path] = None,
    *,
    write_index: bool = True,
    write_schema: bool = True,
    max_evidence_per_section: int = 8,
) -> Path:
    """Render the universal graph as an Obsidian-style markdown vault.

    Returns the vault root directory.
    """
    vault = Path(output_dir) if output_dir else DEFAULT_VAULT_DIR
    vault.mkdir(parents=True, exist_ok=True)

    # 1. Build a slug index so edges can resolve to wiki paths.
    page_index = _build_page_index(graph)

    # 2. Write per-node pages.
    written = 0
    for node in graph.nodes.values():
        loc = page_index.get(node.id)
        if not loc:
            continue  # node type not surfaced as a wiki page
        folder, slug = loc
        page_dir = vault / folder
        page_dir.mkdir(parents=True, exist_ok=True)
        md = _render_node_page(
            node, graph, page_index,
            max_evidence_per_section=max_evidence_per_section,
        )
        (page_dir / f"{slug}.md").write_text(md, encoding="utf-8")
        written += 1

    # 3. Top-level index + schema files (compatibility with the wiki app).
    if write_index:
        (vault / "index.md").write_text(_render_index(graph, page_index), encoding="utf-8")
    if write_schema:
        (vault / "SCHEMA.md").write_text(_SCHEMA_MD, encoding="utf-8")

    logger.info("Exported wiki vault: %s pages -> %s", written, vault)
    return vault


# ── page index ────────────────────────────────────────────────────────────

def _provider_subfolder(node: Node, base: str) -> str:
    """Deployments split into provider subfolders (vercel/, cloudflare/)."""
    if node.type == NodeType.DEPLOYMENT and node.provider:
        return node.provider
    return base


def _build_page_index(graph: UniversalGraph) -> Dict[str, Tuple[str, str]]:
    """Map node-id -> (folder, slug) for every node that has a wiki page."""
    out: Dict[str, Tuple[str, str]] = {}
    seen_paths: set[Tuple[str, str]] = set()
    for node in graph.nodes.values():
        folder = NODE_TYPE_TO_WIKI_FOLDER.get(node.type)
        if not folder:
            continue
        folder = _provider_subfolder(node, folder)
        slug = node.slug or _fallback_slug(node)
        # de-dup slugs within a folder
        path_key = (folder, slug)
        n = 2
        while path_key in seen_paths:
            path_key = (folder, f"{slug}-{n}")
            n += 1
        seen_paths.add(path_key)
        out[node.id] = path_key
    return out


_FALLBACK_RE = re.compile(r"[^a-z0-9]+")


def _fallback_slug(node: Node) -> str:
    base = (node.label or node.id).lower()
    base = _FALLBACK_RE.sub("-", base).strip("-")
    return base or node.id.replace(":", "-").replace("/", "-")


# ── page rendering ────────────────────────────────────────────────────────

def _yaml_frontmatter(node: Node) -> str:
    fm: Dict[str, object] = {
        "title": node.label or node.id,
        "type": _wiki_type_label(node.type),
        "slug": node.slug or _fallback_slug(node),
    }
    if node.tags:
        fm["tags"] = list(node.tags)
    if node.provider:
        fm["provider"] = node.provider
    if node.confidence is not None:
        fm["confidence"] = round(float(node.confidence), 4)
    if node.career_value is not None:
        fm["career_value"] = round(float(node.career_value), 4)
    if node.created:
        fm["created"] = node.created.isoformat() if hasattr(node.created, "isoformat") else node.created
    if node.updated:
        fm["updated"] = node.updated.isoformat() if hasattr(node.updated, "isoformat") else node.updated
    fm["synced_at"] = datetime.now(timezone.utc).isoformat()

    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            joined = ", ".join(f"'{_yaml_escape(str(x))}'" for x in v)
            lines.append(f"{k}: [{joined}]")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: '{_yaml_escape(str(v))}'")
    lines.append("---")
    return "\n".join(lines)


def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "''")


def _wiki_type_label(t: NodeType) -> str:
    """Map internal NodeType to the consumer's frontmatter ``type`` value.

    The careergraph-wiki app uses values like ``skill``, ``project``,
    ``vercel_project``. We map to those when natural.
    """
    return {
        NodeType.PERSON: "profile",
        NodeType.PROJECT: "project",
        NodeType.REPO: "repo",
        NodeType.DEPLOYMENT: "deployment",
        NodeType.SKILL: "skill",
        NodeType.TECHNOLOGY: "technology",
        NodeType.CONCEPT: "concept",
        NodeType.METHODOLOGY: "methodology",
        NodeType.KNOWLEDGE_DOMAIN: "domain",
        NodeType.DOCUMENT: "doc",
        NodeType.CONVERSATION: "conversation",
        NodeType.ARTIFACT: "artifact",
        NodeType.CAREER_PHASE: "career_phase",
        NodeType.TIMELINE_EVENT: "career_event",
        NodeType.ORGANIZATION: "organization",
    }.get(t, t.value)


def _wikilink(folder: str, slug: str, label: Optional[str] = None) -> str:
    target = f"{folder}/{slug}"
    if label and label != slug:
        return f"[[{target}|{label}]]"
    return f"[[{target}]]"


def _render_node_page(
    node: Node,
    graph: UniversalGraph,
    page_index: Dict[str, Tuple[str, str]],
    *,
    max_evidence_per_section: int,
) -> str:
    out: List[str] = [_yaml_frontmatter(node), ""]

    out.append(f"# {node.label or node.id}")
    out.append("")

    # Description / summary
    desc = node.properties.get("description") or node.properties.get("summary")
    if desc:
        out.append(str(desc).strip())
        out.append("")

    # Property table
    prop_table = _render_properties_table(node)
    if prop_table:
        out.append("## Info")
        out.append("")
        out.append(prop_table)
        out.append("")

    # Outgoing edges, grouped
    out_groups: Dict[EdgeType, List[Edge]] = defaultdict(list)
    in_groups: Dict[EdgeType, List[Edge]] = defaultdict(list)
    for edge in graph.edges_for(node.id):
        if edge.source == node.id:
            out_groups[edge.type].append(edge)
        if edge.target == node.id:
            in_groups[edge.type].append(edge)

    for etype, edges in out_groups.items():
        plan = EDGE_RENDER_PLAN.get(etype)
        title = plan[0] if plan else _humanize_edge(etype)
        rows = _render_edge_list(edges, graph, page_index, side="target")
        if rows:
            out.append(f"## {title}")
            out.append("")
            out.extend(rows)
            out.append("")

    # Backlinks (incoming)
    if in_groups:
        out.append("## Backlinks")
        out.append("")
        for etype, edges in in_groups.items():
            sub = _humanize_edge(etype, incoming=True)
            rows = _render_edge_list(edges, graph, page_index, side="source")
            if rows:
                out.append(f"### {sub}")
                out.append("")
                out.extend(rows)
                out.append("")

    # Evidence audit trail
    ev_rows = _collect_evidence_rows(node, graph, max_evidence_per_section * 3)
    if ev_rows:
        out.append("## Evidence")
        out.append("")
        for row in ev_rows[: max_evidence_per_section * 3]:
            out.append(f"- {row}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _render_properties_table(node: Node) -> str:
    skip = {"description", "summary"}
    rows: List[str] = []
    for k, v in sorted(node.properties.items()):
        if k in skip:
            continue
        val = _format_prop_value(v)
        if not val:
            continue
        rows.append(f"| {_md_escape(k)} | {val} |")
    if not rows:
        return ""
    return "| Property | Value |\n|----------|-------|\n" + "\n".join(rows)


def _format_prop_value(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        if not v:
            return ""
        return ", ".join(_md_escape(str(x)) for x in v[:8])
    if isinstance(v, dict):
        return _md_escape(", ".join(f"{k}={vv}" for k, vv in list(v.items())[:5]))
    return _md_escape(str(v))


_MD_PIPE = re.compile(r"\|")


def _md_escape(s: str) -> str:
    return _MD_PIPE.sub(r"\\|", s).replace("\n", " ").strip()


def _render_edge_list(
    edges: List[Edge],
    graph: UniversalGraph,
    page_index: Dict[str, Tuple[str, str]],
    *,
    side: str,
) -> List[str]:
    rows: List[str] = []
    seen: set[str] = set()
    edges = sorted(edges, key=lambda e: -e.weight)
    for edge in edges:
        other_id = edge.target if side == "target" else edge.source
        if other_id in seen:
            continue
        seen.add(other_id)
        other = graph.get(other_id)
        if not other:
            rows.append(f"- `{other_id}` _(weight {edge.weight:.2f})_")
            continue
        loc = page_index.get(other_id)
        if loc:
            link = _wikilink(loc[0], loc[1], other.label)
        else:
            link = f"`{other.label or other_id}` ({other.type.value})"
        suffix = f" _(weight {edge.weight:.2f})_" if edge.weight < 0.99 else ""
        rows.append(f"- {link}{suffix}")
    return rows


def _humanize_edge(t: EdgeType, *, incoming: bool = False) -> str:
    base = t.value.replace("_", " ").title()
    return f"Incoming {base}" if incoming else base


def _collect_evidence_rows(node: Node, graph: UniversalGraph, limit: int) -> List[str]:
    out: List[str] = []
    for edge in graph.edges_for(node.id):
        for ev_id in edge.evidence:
            ev = graph.evidence.get(ev_id)
            if not ev:
                continue
            row = (
                f"`{ev.evidence_type.value}` `{ev.locator}`"
                f" — {_md_escape(ev.excerpt[:160])}"
                f" _(conf {ev.confidence:.2f})_"
            )
            out.append(row)
            if len(out) >= limit:
                return out
    return out


# ── index + schema files (consumed by the wiki app) ───────────────────────

def _render_index(graph: UniversalGraph, page_index: Dict[str, Tuple[str, str]]) -> str:
    counts: Dict[str, int] = defaultdict(int)
    for nid in page_index:
        node = graph.get(nid)
        if node:
            counts[_wiki_type_label(node.type)] += 1
    sections = [
        "---",
        "title: Home",
        "type: index",
        "---",
        "",
        "# Career Graph — Second Brain",
        "",
        "Auto-generated knowledge graph rendered as an Obsidian-style vault.",
        "Each page is one node; sections are edges; backlinks reflect incoming edges.",
        "",
        "## Sections",
        "",
        "- [[skills/]] — Skills, technologies, methodologies",
        "- [[concepts/]] — Concepts and ideas",
        "- [[projects/]] — Projects (logical units)",
        "- [[repos/]] — Source repositories",
        "- [[vercel/]], [[cloudflare/]] — Deployments",
        "- [[docs/]] — Documents (READMEs, plans, blog posts)",
        "- [[conversations/]] — Captured conversations & artifacts",
        "- [[career/]] — Career timeline & profile",
        "",
        "## Stats",
        "",
    ]
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        sections.append(f"- **{k}**: {v}")
    sections.append("")
    sections.append(f"_Generated at {datetime.now(timezone.utc).isoformat()}_")
    sections.append("")
    return "\n".join(sections)


_SCHEMA_MD = """# Wiki Schema

This vault is auto-generated by `graph-rag-resume-agent`. Pages mirror nodes
in a universal knowledge graph; folders mirror node types.

## Frontmatter

```yaml
---
title: Page Title
type: skill | technology | concept | methodology | project | repo |
      deployment | doc | conversation | artifact | profile | career_phase |
      career_event | domain | organization
slug: url-safe-id
tags: [tag1, tag2]
provider: github | vercel | cloudflare | conversation | manual | llm
confidence: 0.0 - 1.0
career_value: 0.0 - 1.0
created: ISO-8601
updated: ISO-8601
synced_at: ISO-8601
---
```

## Wikilinks

`[[<folder>/<slug>]]` and `[[<folder>/<slug>|Label]]` are used. The graph
viewer parses these to render edges. Backlinks are computed automatically.

## Page sections

Each page contains an `Info` table from node properties, one section per
outgoing edge type, a `Backlinks` section grouped by incoming edge type, and
an `Evidence` section listing the audit trail (evidence_type, locator,
excerpt, confidence).
"""
