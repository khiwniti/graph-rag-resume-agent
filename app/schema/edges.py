"""Universal edge taxonomy."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class EdgeType(str, Enum):
    # Authorship / ownership
    AUTHORED = "AUTHORED"
    CONTRIBUTED_TO = "CONTRIBUTED_TO"
    OWNS = "OWNS"

    # Composition
    CONTAINS = "CONTAINS"               # Repo->File, Project->Repo, Doc->Section
    HAS_MEMBER = "HAS_MEMBER"           # Class->Function, Module->Class
    DEFINES = "DEFINES"                 # File-> (Class | Function)

    # Code structure
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"

    # VCS
    MODIFIES = "MODIFIES"               # Commit->File
    MERGED_VIA = "MERGED_VIA"           # Commit<->PullRequest
    CLOSED_BY = "CLOSED_BY"             # Issue-> (PR | Commit)

    # Knowledge
    USES = "USES"                       # (Repo|Project|File) -> Technology
    IMPLEMENTS = "IMPLEMENTS"           # (Project|File|Function) -> Concept
    EVIDENCES = "EVIDENCES"             # (File|Commit|Doc|Conversation) -> Skill
    BELONGS_TO_DOMAIN = "BELONGS_TO_DOMAIN"
    RELATED_TO = "RELATED_TO"           # symmetric similarity

    # Hosting / deployment
    DEPLOYS_TO = "DEPLOYS_TO"           # (Repo|Project) -> Deployment
    SERVES = "SERVES"                   # Deployment -> (Domain|Route)
    CONFIGURED_BY = "CONFIGURED_BY"     # Deployment -> File

    # Documents
    DOCUMENTS = "DOCUMENTS"             # (Document|Section) -> any
    MENTIONS = "MENTIONS"               # (Document|Section|Conversation) -> any
    LINKS_TO = "LINKS_TO"               # Section -> Section (wikilink)

    # Time
    OCCURRED_DURING = "OCCURRED_DURING"
    PRECEDES = "PRECEDES"
    EVOLVED_INTO = "EVOLVED_INTO"

    # Tagging
    TAGGED_WITH = "TAGGED_WITH"


# Edge types that should also generate a reverse edge in undirected views.
BIDIRECTIONAL_EDGES: Set[EdgeType] = {
    EdgeType.RELATED_TO,
    EdgeType.MERGED_VIA,
}


@dataclass
class Edge:
    """A universal graph edge.

    Attributes
    ----------
    source     : source node id
    target     : target node id
    type       : EdgeType
    weight     : aggregate strength of the relationship (0..1)
    properties : extra fields (e.g. ``call_site``, ``line``)
    evidence   : list of evidence ids backing this edge
    """

    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """Unique key for de-dup / merge."""
        return f"{self.source}|{self.type.value}|{self.target}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.source,
            "to": self.target,
            "type": self.type.value,
            "weight": self.weight,
            "properties": dict(self.properties),
            "evidence": list(self.evidence),
        }

    def merge(self, other: "Edge") -> "Edge":
        if other.key != self.key:
            raise ValueError(f"Cannot merge edges with different keys: {self.key} vs {other.key}")
        # union evidence
        seen = set(self.evidence)
        for ev in other.evidence:
            if ev not in seen:
                self.evidence.append(ev)
                seen.add(ev)
        # weight: probabilistic OR (1 - prod(1 - w))
        self.weight = 1.0 - (1.0 - self.weight) * (1.0 - other.weight)
        # union properties
        for k, v in other.properties.items():
            self.properties.setdefault(k, v)
        return self
