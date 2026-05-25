"""LLM-driven concept / skill / methodology extractor.

Asks an LLM (default: NVIDIA NIM, OpenAI-compatible endpoint) to read a
repository's README + key file excerpts and emit a structured JSON of
domain-level entities that static analysis cannot easily detect:
methodologies, knowledge domains, abstract concepts ("RAG", "Service mesh",
"Event sourcing", ...), and high-level skill claims with the locator that
*supports* each one.

The output integrates with :class:`app.builders.universal_builder.UniversalGraphBuilder`
by emitting nodes & edges directly into a UniversalGraph, with each new fact
backed by an :class:`Evidence` of type ``LLM_INFERENCE``.

Privacy note: only README + small file excerpts (head of file) are sent. No
secrets, no full repo contents.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

from ..schema import (
    Edge,
    EdgeType,
    Evidence,
    EvidenceType,
    Node,
    NodeType,
    UniversalGraph,
    canonical_concept,
    canonical_slug,
    concept_id,
    domain_id,
    skill_id,
    technology_id,
)

logger = logging.getLogger(__name__)

# NVIDIA NIM OpenAI-compatible endpoint
NVIDIA_BASE_URL = os.getenv(
    "NVIDIA_BASE_URL",
    "https://integrate.api.nvidia.com/v1",
)


_SYSTEM_PROMPT = """You are a senior knowledge-graph extractor specializing in software project analysis.

You will be given a repository's README and small excerpts from key files.
Your job is to emit a strict JSON object describing what the project actually
demonstrates about its author's skills, NOT what it claims. Be conservative:
prefer fewer high-confidence items over many speculative ones.

Output JSON schema (return EXACTLY this structure, no markdown fences, no prose):

{
  "summary": "<3-5 sentence factual summary of what was built>",
  "knowledge_domains": [
    {"name": "<broad area, e.g. 'AI/ML', 'Web Backend', 'DevOps'>",
     "confidence": 0.0-1.0,
     "evidence": "<short quote/locator from inputs>"}
  ],
  "concepts": [
    {"name": "<abstract concept, e.g. 'Retrieval-Augmented Generation', 'Vector Search', 'Event Sourcing'>",
     "confidence": 0.0-1.0,
     "evidence": "<short quote/locator>"}
  ],
  "methodologies": [
    {"name": "<practice, e.g. 'Test-Driven Development', 'GitOps', 'Microservices'>",
     "confidence": 0.0-1.0,
     "evidence": "<short quote/locator>"}
  ],
  "technologies": [
    {"name": "<specific tech only mentioned in README/code, e.g. 'FastAPI', 'Neo4j'>",
     "confidence": 0.0-1.0,
     "evidence": "<short quote/locator>"}
  ],
  "skills": [
    {"name": "<demonstrable skill, e.g. 'Distributed Systems Design', 'Knowledge Graph Engineering'>",
     "confidence": 0.0-1.0,
     "evidence": "<short quote/locator>"}
  ]
}

Rules:
- Confidence 0.9+ only when the input clearly proves the claim.
- "evidence" must be a brief quote (<=160 chars) or "<filename>:<line>".
- Never invent technologies. If unsure, omit.
- Limit each list to <=10 entries.
"""


@dataclass
class LLMExtractionConfig:
    api_key: Optional[str] = None
    base_url: str = NVIDIA_BASE_URL
    model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    max_tokens: int = 1024
    temperature: float = 0.2
    timeout: int = 60
    max_input_chars: int = 12000


@dataclass
class LLMExtraction:
    summary: str = ""
    raw: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.raw is None:
            self.raw = {}


class LLMConceptExtractor:
    """Calls an OpenAI-compatible LLM endpoint and parses JSON output.

    Default endpoint is NVIDIA NIM. Set ``NVIDIA_API_KEY`` (or pass
    ``api_key`` to the constructor) to enable. When no key is configured,
    :meth:`extract` is a no-op that returns ``None``.
    """

    def __init__(self, config: Optional[LLMExtractionConfig] = None):
        self.config = config or LLMExtractionConfig()
        self.config.api_key = self.config.api_key or os.getenv("NVIDIA_API_KEY")

    @property
    def available(self) -> bool:
        return bool(self.config.api_key)

    # ── public API ────────────────────────────────────────────────────────

    def extract(
        self,
        *,
        repo_label: str,
        readme: str,
        code_excerpts: Optional[List[Dict[str, str]]] = None,
        languages: Optional[Iterable[str]] = None,
    ) -> Optional[LLMExtraction]:
        """Run extraction. Returns parsed LLMExtraction, or None when not available."""
        if not self.available:
            logger.info("LLMConceptExtractor: NVIDIA_API_KEY not set, skipping")
            return None

        user_prompt = self._build_user_prompt(repo_label, readme, code_excerpts, languages)
        try:
            text = self._call_llm(user_prompt)
        except Exception as e:
            logger.warning("LLM call failed for %s: %s", repo_label, e)
            return None

        data = self._parse_json(text)
        if not data:
            logger.warning("LLM produced unparseable output for %s", repo_label)
            return None

        return LLMExtraction(summary=data.get("summary", ""), raw=data)

    def emit_into_graph(
        self,
        graph: UniversalGraph,
        repo_node_id: str,
        result: LLMExtraction,
    ) -> Dict[str, int]:
        """Add LLM-extracted entities into the universal graph as nodes/edges
        with LLM_INFERENCE evidence. Returns count summary."""
        counts = {"technologies": 0, "concepts": 0, "skills": 0,
                  "methodologies": 0, "domains": 0}
        if not result or not result.raw:
            return counts

        # Persist summary on the repo node
        repo_node = graph.get(repo_node_id)
        if repo_node and result.summary:
            repo_node.properties.setdefault("llm_summary", result.summary)

        for tech in result.raw.get("technologies", [])[:20]:
            if self._add_kn(graph, repo_node_id, tech, NodeType.TECHNOLOGY,
                            EdgeType.USES, default_weight=0.45):
                counts["technologies"] += 1

        for c in result.raw.get("concepts", [])[:20]:
            if self._add_kn(graph, repo_node_id, c, NodeType.CONCEPT,
                            EdgeType.IMPLEMENTS, default_weight=0.5):
                counts["concepts"] += 1

        for m in result.raw.get("methodologies", [])[:20]:
            if self._add_kn(graph, repo_node_id, m, NodeType.METHODOLOGY,
                            EdgeType.IMPLEMENTS, default_weight=0.45):
                counts["methodologies"] += 1

        for s in result.raw.get("skills", [])[:20]:
            if self._add_kn(graph, repo_node_id, s, NodeType.SKILL,
                            EdgeType.EVIDENCES, default_weight=0.5):
                counts["skills"] += 1

        for d in result.raw.get("knowledge_domains", [])[:10]:
            if self._add_kn(graph, repo_node_id, d, NodeType.KNOWLEDGE_DOMAIN,
                            EdgeType.BELONGS_TO_DOMAIN, default_weight=0.55):
                counts["domains"] += 1

        graph.recompute_node_confidences()
        return counts

    # ── internals ─────────────────────────────────────────────────────────

    def _build_user_prompt(
        self,
        repo_label: str,
        readme: str,
        code_excerpts: Optional[List[Dict[str, str]]],
        languages: Optional[Iterable[str]],
    ) -> str:
        lang_str = ", ".join(languages or []) or "unknown"
        parts: List[str] = [
            f"Repository: {repo_label}",
            f"Languages: {lang_str}",
            "",
            "=== README ===",
            (readme or "")[: self.config.max_input_chars // 2],
        ]
        if code_excerpts:
            parts.append("")
            parts.append("=== KEY FILE EXCERPTS ===")
            budget = self.config.max_input_chars // 2
            for exc in code_excerpts:
                chunk = f"\n--- {exc.get('path','')} ---\n{exc.get('excerpt','')[:1200]}"
                if len(chunk) > budget:
                    chunk = chunk[:budget]
                parts.append(chunk)
                budget -= len(chunk)
                if budget <= 0:
                    break
        parts.append("")
        parts.append("Return JSON only.")
        return "\n".join(parts)

    def _call_llm(self, user_prompt: str) -> str:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": 0.9,
            "stream": False,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
        resp.raise_for_status()
        body = resp.json()
        choices = body.get("choices", [])
        if not choices:
            raise RuntimeError(f"LLM returned no choices: {body}")
        return choices[0].get("message", {}).get("content", "")

    @staticmethod
    def _parse_json(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        # 1) direct
        for candidate in (text, _strip_code_fences(text)):
            try:
                return json.loads(candidate)
            except Exception:
                pass
        # 2) extract first {...} block
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

    @staticmethod
    def _add_kn(
        graph: UniversalGraph,
        repo_node_id: str,
        entry: Dict[str, Any],
        node_type: NodeType,
        edge_type: EdgeType,
        *,
        default_weight: float,
    ) -> bool:
        name = (entry or {}).get("name", "").strip()
        if not name or len(name) > 100:
            return False

        # Pick the right id helper
        if node_type == NodeType.TECHNOLOGY:
            n_id = technology_id(name)
        elif node_type == NodeType.SKILL:
            n_id = skill_id(name)
        elif node_type == NodeType.KNOWLEDGE_DOMAIN:
            n_id = domain_id(name)
        else:
            n_id = concept_id(name)

        graph.add_node(Node(
            id=n_id,
            type=node_type,
            label=name,
            slug=canonical_slug(name),
            provider="llm",
        ))

        try:
            conf = float(entry.get("confidence", default_weight))
        except (TypeError, ValueError):
            conf = default_weight
        # cap LLM-derived confidence so it never outweighs concrete code evidence
        conf = max(0.05, min(0.85, conf))

        edge = graph.add_edge(Edge(
            source=repo_node_id, target=n_id, type=edge_type, weight=conf,
        ))
        evidence_text = (entry.get("evidence") or "")[:480]
        ev = Evidence(
            evidence_type=EvidenceType.LLM_INFERENCE,
            source_node_id=repo_node_id,
            locator=f"llm://{node_type.value}/{canonical_concept(name)}",
            excerpt=evidence_text,
            confidence=conf,
            extra={"extractor": "LLMConceptExtractor"},
        )
        graph.attach_evidence(edge.key, ev)
        return True


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # ```json\n ... ```
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s
