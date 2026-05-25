"""Universal-schema pipeline orchestrator.

Runs the full flow:
    collectors -> universal_builder -> [optional LLM extractor] -> exporters

Outputs:
    data/graph/knowledge_graph.json   (consumed by careergraph-wiki-mcp-ui
                                       GraphConnector)
    data/wiki/                         (Obsidian-style markdown vault for
                                       the wiki app)

The legacy ``app/pipeline.py`` (Neo4j-centric, narrative+RAG path) is
preserved untouched. This new pipeline is *additive* and is the entry point
for everything aligned with the redesigned schema.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .builders import RepoSpec, UniversalGraphBuilder
from .exporters import export_graph_json, export_wiki_vault
from .extractors.llm_concept_extractor import LLMConceptExtractor, LLMExtractionConfig
from .schema import UniversalGraph

logger = logging.getLogger(__name__)


@dataclass
class UniversalPipelineConfig:
    person_login: Optional[str] = None
    output_graph_path: str = "data/graph/knowledge_graph.json"
    output_vault_dir: str = "data/wiki"
    use_llm: bool = True                    # set False to skip LLM augmentation
    llm_top_n_repos: int = 25               # avoid runaway costs
    llm_excerpt_files: int = 4              # how many code excerpts per repo
    llm_excerpt_chars: int = 1200
    repo_specs: List[RepoSpec] = field(default_factory=list)
    vercel_projects: List[Dict[str, Any]] = field(default_factory=list)
    cloudflare_workers: List[Dict[str, Any]] = field(default_factory=list)
    conversations: List[Dict[str, Any]] = field(default_factory=list)


class UniversalPipeline:
    def __init__(self, config: UniversalPipelineConfig):
        self.config = config
        self.builder = UniversalGraphBuilder(person_login=config.person_login)
        self.llm = LLMConceptExtractor(LLMExtractionConfig()) if config.use_llm else None

    # ── public API ────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Execute the pipeline; returns a stats dict and writes outputs."""
        stats: Dict[str, Any] = {"repos_added": 0, "vercel_added": 0,
                                 "cloudflare_added": 0, "conversations_added": 0,
                                 "llm_augmentations": 0, "llm_skipped": 0}

        # 1. Repos (deep extraction)
        for spec in self.config.repo_specs:
            try:
                repo_node_id = self.builder.add_repo(spec)
                stats["repos_added"] += 1
            except Exception as e:
                logger.exception("Failed to add repo %s/%s: %s",
                                 spec.owner, spec.name, e)
                continue

            # 2. LLM augmentation per-repo (top-N)
            if (
                self.llm
                and self.llm.available
                and stats["repos_added"] <= self.config.llm_top_n_repos
            ):
                excerpts = self._collect_code_excerpts(spec)
                readme = spec.readme or (spec.metadata or {}).get("readme", "")
                if readme or excerpts:
                    result = self.llm.extract(
                        repo_label=f"{spec.owner}/{spec.name}",
                        readme=readme,
                        code_excerpts=excerpts,
                        languages=list((spec.metadata or {}).get("languages", {}).keys()),
                    )
                    if result:
                        emitted = self.llm.emit_into_graph(
                            self.builder.graph, repo_node_id, result
                        )
                        stats["llm_augmentations"] += sum(emitted.values())
                    else:
                        stats["llm_skipped"] += 1

        # 3. Vercel
        for vp in self.config.vercel_projects:
            try:
                self.builder.add_vercel_project(vp)
                stats["vercel_added"] += 1
            except Exception as e:
                logger.warning("vercel project ingest failed: %s", e)

        # 4. Cloudflare
        for cw in self.config.cloudflare_workers:
            try:
                self.builder.add_cloudflare_worker(cw)
                stats["cloudflare_added"] += 1
            except Exception as e:
                logger.warning("cloudflare worker ingest failed: %s", e)

        # 5. Conversations
        for conv in self.config.conversations:
            try:
                self.builder.add_conversation(conv)
                stats["conversations_added"] += 1
            except Exception as e:
                logger.warning("conversation ingest failed: %s", e)

        # 6. Finalize + export
        graph: UniversalGraph = self.builder.finalize()
        json_path = export_graph_json(graph, self.config.output_graph_path)
        vault_path = export_wiki_vault(graph, self.config.output_vault_dir)

        stats["graph_stats"] = graph.stats()
        stats["graph_json"] = str(json_path)
        stats["wiki_vault"] = str(vault_path)
        return stats

    # ── helpers ───────────────────────────────────────────────────────────

    def _collect_code_excerpts(self, spec: RepoSpec) -> List[Dict[str, str]]:
        """Pick a few representative files (heuristically: top-level *.md, main entry,
        first source files) and grab heads as LLM context."""
        if not spec.local_path:
            return []
        root = Path(spec.local_path)
        if not root.exists():
            return []

        candidates: List[Path] = []
        # entry-points first
        for cand in [
            "main.py", "app.py", "src/main.py", "src/app.py", "src/index.ts",
            "src/index.js", "index.ts", "index.js", "package.json",
            "pyproject.toml", "Cargo.toml", "go.mod", "main.go", "lib.rs",
        ]:
            p = root / cand
            if p.is_file():
                candidates.append(p)
        # fallback: first few source files we haven't already grabbed
        if len(candidates) < self.config.llm_excerpt_files:
            for ext in (".py", ".ts", ".js", ".go", ".rs"):
                for p in root.rglob(f"*{ext}"):
                    if p in candidates:
                        continue
                    candidates.append(p)
                    if len(candidates) >= self.config.llm_excerpt_files:
                        break
                if len(candidates) >= self.config.llm_excerpt_files:
                    break

        out: List[Dict[str, str]] = []
        for p in candidates[: self.config.llm_excerpt_files]:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            out.append({
                "path": str(p.relative_to(root)),
                "excerpt": text[: self.config.llm_excerpt_chars],
            })
        return out


# ── convenience entry point ───────────────────────────────────────────────


def run_for_local_repo(
    *,
    repo_root: str,
    owner: str,
    name: str,
    person_login: Optional[str] = None,
    use_llm: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    output_graph_path: str = "data/graph/knowledge_graph.json",
    output_vault_dir: str = "data/wiki",
) -> Dict[str, Any]:
    """One-shot helper: build + export from a single local repo."""
    cfg = UniversalPipelineConfig(
        person_login=person_login,
        use_llm=use_llm,
        output_graph_path=output_graph_path,
        output_vault_dir=output_vault_dir,
        repo_specs=[RepoSpec(
            owner=owner, name=name, local_path=repo_root,
            metadata=metadata or {},
        )],
    )
    return UniversalPipeline(cfg).run()
