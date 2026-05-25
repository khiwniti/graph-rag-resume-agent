"""Evidence model — auditable provenance for every claim."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class EvidenceType(str, Enum):
    SOURCE_CODE = "source_code"        # symbol used in actual source file
    DEPENDENCY = "dependency"          # package manifest entry
    CONFIG = "config"                  # config file (vercel.json, wrangler.toml, ...)
    DEPLOYMENT = "deployment"          # live deployment metadata
    COMMIT_MSG = "commit_msg"          # commit message
    PR_BODY = "pr_body"                # pull request body / title
    DOC = "doc"                        # README, blog, design doc
    CONVERSATION = "conversation"      # chat / agent transcript
    LLM_INFERENCE = "llm_inference"    # produced by a language model


# Default per-evidence-type weight when computing aggregate confidence.
EVIDENCE_WEIGHTS: Dict[EvidenceType, float] = {
    EvidenceType.SOURCE_CODE: 1.0,
    EvidenceType.DEPENDENCY: 0.7,
    EvidenceType.CONFIG: 0.6,
    EvidenceType.DEPLOYMENT: 0.5,
    EvidenceType.COMMIT_MSG: 0.4,
    EvidenceType.PR_BODY: 0.4,
    EvidenceType.DOC: 0.5,
    EvidenceType.CONVERSATION: 0.3,
    EvidenceType.LLM_INFERENCE: 0.35,
}


@dataclass
class Evidence:
    """A single piece of evidence backing a node or an edge.

    Attributes
    ----------
    id              : stable hash id, derived from (source_node_id, locator, excerpt[:64])
    evidence_type   : EvidenceType
    source_node_id  : id of the graph node that produced the evidence
                      (e.g. a File node id for source-code evidence)
    locator         : a precise pointer (path:line, commit sha, doc#section)
    excerpt         : short quoted text — keep small (<=512 chars)
    confidence      : 0..1 weight for this single piece (default = EVIDENCE_WEIGHTS)
    extracted_at    : when extraction ran
    extra           : free-form bag (e.g. extractor name)
    """

    evidence_type: EvidenceType
    source_node_id: str
    locator: str
    excerpt: str = ""
    confidence: Optional[float] = None
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extra: Dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if self.confidence is None:
            self.confidence = EVIDENCE_WEIGHTS.get(self.evidence_type, 0.5)
        if not self.id:
            h = hashlib.sha1()
            h.update(self.evidence_type.value.encode())
            h.update(b"|")
            h.update(self.source_node_id.encode())
            h.update(b"|")
            h.update(self.locator.encode())
            h.update(b"|")
            h.update(self.excerpt[:64].encode("utf-8", errors="replace"))
            self.id = "ev:" + h.hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "evidence_type": self.evidence_type.value,
            "source_node_id": self.source_node_id,
            "locator": self.locator,
            "excerpt": self.excerpt,
            "confidence": self.confidence,
            "extracted_at": self.extracted_at.isoformat(),
            "extra": dict(self.extra),
        }


def aggregate_confidence(weights: Iterable[float]) -> float:
    """Combine independent confidences via probabilistic OR.

    P(at-least-one-correct) = 1 - prod(1 - w_i)
    """
    p_none = 1.0
    for w in weights:
        p_none *= max(0.0, 1.0 - float(w))
    return 1.0 - p_none
