"""Graph JSON exporter — matches careergraph-wiki-mcp-ui GraphConnector.

Emits ``data/graph/knowledge_graph.json`` in the shape::

    {
      "nodes": [
        {"id": "...", "type": "...", "label": "...", "slug": "...",
         "tags": [...], "provider": "...", "confidence": 0.9,
         "career_value": 0.8,
         "properties": { ...arbitrary fields... }}
      ],
      "edges": [
        {"from": "...", "to": "...", "type": "...",
         "weight": 0.7, "properties": {...}, "evidence": ["ev:..."]}
      ],
      "evidence": [
        {"id": "ev:...", "evidence_type": "...", "source_node_id": "...",
         "locator": "...", "excerpt": "...", "confidence": 0.7}
      ],
      "metadata": {...}
    }

Compatible with::

    careergraph-wiki-mcp-ui/apps/api/app/connectors/graph_connector.py

which iterates over ``graph["nodes"]`` looking at ``node["id"]``,
``node["type"]``, ``node["properties"]`` and over ``graph["edges"]`` using
``edge["from"]`` / ``edge["to"]`` / ``edge["type"]``.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..schema import UniversalGraph

logger = logging.getLogger(__name__)


DEFAULT_OUTPUT = Path("data/graph/knowledge_graph.json")


def export_graph_json(
    graph: UniversalGraph,
    output_path: Optional[str | Path] = None,
    *,
    include_evidence: bool = True,
) -> Path:
    """Serialize the universal graph to the GraphConnector-compatible JSON file.

    Parameters
    ----------
    graph : UniversalGraph
        The canonical graph.
    output_path : str | Path | None
        Destination file. Defaults to ``data/graph/knowledge_graph.json``.
    include_evidence : bool
        If True, evidence rows are also dumped (recommended; the wiki app
        ignores extra keys safely).
    """
    out = Path(output_path) if output_path else DEFAULT_OUTPUT
    return graph.save_json(out, include_evidence=include_evidence)
