"""Universal node taxonomy.

Every node in the graph is one of these types. New types must be added here
first, then handled by exporters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    # Identity
    PERSON = "person"
    ORGANIZATION = "organization"

    # Project surface
    PROJECT = "project"
    REPO = "repo"
    DEPLOYMENT = "deployment"
    DOMAIN = "domain"            # DNS domain
    ROUTE = "route"

    # Code
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"

    # VCS history
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    BRANCH = "branch"
    RELEASE = "release"

    # Documents
    DOCUMENT = "document"
    SECTION = "section"

    # Conversation
    CONVERSATION = "conversation"
    ARTIFACT = "artifact"

    # Knowledge
    SKILL = "skill"
    TECHNOLOGY = "technology"
    CONCEPT = "concept"
    METHODOLOGY = "methodology"
    KNOWLEDGE_DOMAIN = "knowledge_domain"

    # Time
    TIMELINE_EVENT = "timeline_event"
    CAREER_PHASE = "career_phase"


# Maps node types to the markdown vault folder used by careergraph-wiki-mcp-ui.
# Types absent from this map are NOT surfaced as wiki pages by default
# (they still live in the JSON graph for queries).
NODE_TYPE_TO_WIKI_FOLDER: Dict[NodeType, str] = {
    NodeType.PERSON: "career",
    NodeType.ORGANIZATION: "career",
    NodeType.PROJECT: "projects",
    NodeType.REPO: "repos",
    NodeType.DEPLOYMENT: "deployments",        # vercel/cloudflare subfolders chosen by provider
    NodeType.DOCUMENT: "docs",
    NodeType.CONVERSATION: "conversations",
    NodeType.ARTIFACT: "artifacts",
    NodeType.SKILL: "skills",
    NodeType.TECHNOLOGY: "skills",             # technologies share /skills (alias index)
    NodeType.CONCEPT: "concepts",
    NodeType.METHODOLOGY: "concepts",
    NodeType.KNOWLEDGE_DOMAIN: "domains",
    NodeType.CAREER_PHASE: "career",
    NodeType.TIMELINE_EVENT: "career",
}


@dataclass
class Node:
    """A universal graph node.

    Attributes
    ----------
    id        : Stable deterministic id, e.g. ``repo:owner/name``.
                See app.schema.identity for builders.
    type      : NodeType.
    label     : Human-readable name (used as wiki page title).
    slug      : URL-safe slug (used as wiki page filename when applicable).
    properties: Free-form bag of additional fields (description, url, ...).
    tags      : Tag list for filtering/UI.
    confidence: Aggregate confidence for the node's *existence* (1.0 for
                concrete sources, lower for LLM-inferred concepts).
    career_value: Optional UI hint for graph importance (0..1).
    provider  : Source provider (github, vercel, cloudflare, conversation, llm).
    created   : First-seen timestamp.
    updated   : Last-updated timestamp.
    """

    id: str
    type: NodeType
    label: str
    slug: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    career_value: Optional[float] = None
    provider: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "slug": self.slug,
            "properties": dict(self.properties),
            "tags": list(self.tags),
            "confidence": self.confidence,
        }
        if self.career_value is not None:
            out["career_value"] = self.career_value
        if self.provider:
            out["provider"] = self.provider
        if self.created:
            out["created"] = self.created.isoformat()
        if self.updated:
            out["updated"] = self.updated.isoformat()
        return out

    def merge(self, other: "Node") -> "Node":
        """Merge another node with same id into self (in place). Returns self.

        Newer ``updated`` wins for scalar fields; tags & properties are unioned;
        confidence is taken as max.
        """
        if other.id != self.id:
            raise ValueError(f"Cannot merge nodes with different ids: {self.id} vs {other.id}")

        # union tags
        merged_tags = list(dict.fromkeys(list(self.tags) + list(other.tags)))
        self.tags = merged_tags

        # union properties (other wins on collision if other.updated is newer)
        other_newer = (other.updated and self.updated and other.updated > self.updated) or (
            other.updated and not self.updated
        )
        for k, v in other.properties.items():
            if k not in self.properties or other_newer:
                self.properties[k] = v

        # confidence: max (more evidence is better)
        self.confidence = max(self.confidence, other.confidence)

        # career_value: max if either is set
        if other.career_value is not None:
            self.career_value = max(self.career_value or 0.0, other.career_value)

        # provider: prefer existing; record alternates
        if other.provider and other.provider != self.provider:
            alts = self.properties.setdefault("alt_providers", [])
            if other.provider not in alts and other.provider != self.provider:
                alts.append(other.provider)

        # timestamps: keep earliest created, latest updated
        if other.created and (not self.created or other.created < self.created):
            self.created = other.created
        if other.updated and (not self.updated or other.updated > self.updated):
            self.updated = other.updated

        # label: prefer non-empty / longer human-readable
        if not self.label or (other.label and len(other.label) > len(self.label)):
            self.label = other.label

        return self
