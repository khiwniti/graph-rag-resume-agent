"""Universal knowledge graph schema.

Single source of truth for node types, edge types, evidence, identity & slug
rules. All collectors, extractors, builders and exporters speak this schema.

See plans/KNOWLEDGE_GRAPH_REDESIGN.md for the full design.
"""
from .nodes import NodeType, Node, NODE_TYPE_TO_WIKI_FOLDER
from .edges import EdgeType, Edge, BIDIRECTIONAL_EDGES
from .evidence import Evidence, EvidenceType, EVIDENCE_WEIGHTS, aggregate_confidence
from .identity import (
    canonical_slug,
    canonical_concept,
    repo_id,
    file_id,
    function_id,
    class_id,
    skill_id,
    technology_id,
    concept_id,
    deployment_id,
    commit_id,
    document_id,
    section_id,
    conversation_id,
    person_id,
    domain_id,
)
from .graph import UniversalGraph

__all__ = [
    "NodeType",
    "Node",
    "NODE_TYPE_TO_WIKI_FOLDER",
    "EdgeType",
    "Edge",
    "BIDIRECTIONAL_EDGES",
    "Evidence",
    "EvidenceType",
    "EVIDENCE_WEIGHTS",
    "aggregate_confidence",
    "canonical_slug",
    "canonical_concept",
    "repo_id",
    "file_id",
    "function_id",
    "class_id",
    "skill_id",
    "technology_id",
    "concept_id",
    "deployment_id",
    "commit_id",
    "document_id",
    "section_id",
    "conversation_id",
    "person_id",
    "domain_id",
    "UniversalGraph",
]
