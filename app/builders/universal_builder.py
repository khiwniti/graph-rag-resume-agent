"""UniversalGraphBuilder — bridges existing extractors to the universal schema.

This is the orchestration layer. It does not do extraction itself — it owns a
``UniversalGraph`` and delegates to the extractor modules already in
``app/extractors/``, then *adapts* their typed outputs into universal
``Node`` / ``Edge`` / ``Evidence`` records.

Typical usage::

    builder = UniversalGraphBuilder(person_login="khiwniti")
    builder.add_repo(RepoSpec(
        owner="khiwniti",
        name="graph-rag-resume-agent",
        local_path="/repos/graph-rag-resume-agent",
        metadata={"description": "...", "language": "Python", "stars": 12,
                  "url": "https://github.com/...", "languages": {...},
                  "created_at": "...", "pushed_at": "...",
                  "readme": "..."},
    ))
    builder.add_vercel_project({...})           # raw vercel collector data
    builder.add_cloudflare_worker({...})
    builder.add_conversation({...})
    graph = builder.finalize()

The graph is then handed to ``app.exporters`` for serialization.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from ..extractors.code_structure import (
    CodeStructureExtractor,
    CodeStructure,
    CodeEntity,
    CodeRelationship,
)
from ..extractors.cross_file_linker import CrossFileLinker
from ..extractors.dependency_parser import DependencyParser, Dependency
from ..extractors.deployment_analyzer import DeploymentAnalyzer, DeploymentAnalysis
from ..extractors.doc_code_linker import DocCodeLinker, ReadmeSection, DocLink
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
    class_id,
    commit_id,
    concept_id,
    conversation_id,
    deployment_id,
    document_id,
    file_id,
    function_id,
    person_id,
    repo_id,
    section_id,
    skill_id,
    technology_id,
)

logger = logging.getLogger(__name__)


# ── canonical alias map for technologies (very small starter — can be loaded
# from data/canonical/aliases.json later) ─────────────────────────────────
_TECH_ALIASES: Dict[str, str] = {
    "fastapi": "FastAPI",
    "fast-api": "FastAPI",
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "py": "Python",
    "python3": "Python",
    "ts": "TypeScript",
    "js": "JavaScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "react": "React",
    "vue": "Vue",
    "neo4j": "Neo4j",
    "torch": "PyTorch",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "faiss": "FAISS",
    "qdrant": "Qdrant",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "chromadb": "Chroma",
    "redis": "Redis",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "vercel": "Vercel",
    "cloudflare": "Cloudflare",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
}


def canonicalize_technology(raw: str) -> str:
    """Map a raw dep / package name to a canonical display label."""
    if not raw:
        return raw
    key = raw.lower().strip()
    return _TECH_ALIASES.get(key, raw)


# ── inputs ────────────────────────────────────────────────────────────────


@dataclass
class RepoSpec:
    """Single repository to be added to the graph."""

    owner: str
    name: str
    local_path: Optional[str] = None      # path on disk if cloned, else None
    metadata: Dict[str, Any] = field(default_factory=dict)
    readme: str = ""
    max_files: int = 200
    parse_code: bool = True               # AST/regex code structure
    parse_dependencies: bool = True
    parse_docs: bool = True
    parse_deployment_configs: bool = True


# ── builder ───────────────────────────────────────────────────────────────


class UniversalGraphBuilder:
    """Stateful builder that emits into a single ``UniversalGraph``."""

    # Manifests we know how to parse for dependencies → Technology nodes
    DEP_MANIFESTS = {
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
    }

    # Deployment config files we recognise inside repos
    DEPLOY_CONFIGS = {
        "vercel.json",
        "wrangler.toml",
        "netlify.toml",
        "fly.toml",
        "railway.json",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    }

    def __init__(
        self,
        *,
        person_login: Optional[str] = None,
        graph: Optional[UniversalGraph] = None,
    ):
        self.graph = graph or UniversalGraph()
        self.person_id: Optional[str] = None
        if person_login:
            person_node = Node(
                id=person_id(person_login),
                type=NodeType.PERSON,
                label=person_login,
                slug=canonical_slug(person_login),
                provider="manual",
            )
            self.graph.add_node(person_node)
            self.person_id = person_node.id

    # ── repo ingestion ────────────────────────────────────────────────────

    def add_repo(self, spec: RepoSpec) -> str:
        """Add a repo and everything we can extract from it. Returns the
        repo node id."""
        rid = repo_id(spec.owner, spec.name)
        meta = spec.metadata or {}
        readme = spec.readme or meta.get("readme", "")

        # 1. The Repo node itself
        repo_node = Node(
            id=rid,
            type=NodeType.REPO,
            label=spec.name,
            slug=f"{canonical_slug(spec.owner)}--{canonical_slug(spec.name)}",
            provider="github",
            properties={
                k: v for k, v in {
                    "owner": spec.owner,
                    "url": meta.get("url") or meta.get("html_url"),
                    "description": meta.get("description"),
                    "language": meta.get("language"),
                    "languages": list((meta.get("languages") or {}).keys())[:10],
                    "stars": meta.get("stars") or meta.get("stargazers_count"),
                    "forks": meta.get("forks") or meta.get("forks_count"),
                    "topics": meta.get("topics", []),
                    "default_branch": meta.get("default_branch"),
                    "license": meta.get("license"),
                }.items() if v not in (None, "", [])
            },
            tags=list(meta.get("topics", []))[:8],
            created=_parse_dt(meta.get("created_at")),
            updated=_parse_dt(meta.get("pushed_at") or meta.get("updated_at")),
        )
        self.graph.add_node(repo_node)

        # 2. AUTHORED edge from person
        if self.person_id:
            self.graph.add_edge(Edge(
                source=self.person_id,
                target=rid,
                type=EdgeType.AUTHORED,
                weight=1.0,
            ))

        # 3. Languages → Technology nodes
        for lang in (meta.get("languages") or {}):
            self._link_technology(rid, lang, EvidenceType.SOURCE_CODE,
                                  locator=f"{rid}#languages",
                                  excerpt=f"Reported language: {lang}",
                                  weight=0.9)

        # 4. Walk the repo on disk if available
        if spec.local_path and Path(spec.local_path).exists():
            self._ingest_repo_filesystem(spec, rid)
        elif readme:
            # Even without disk, we still ingest the README as a Document
            self._ingest_readme(rid, readme, repo_path=spec.local_path or "")

        # 5. Topics as concepts
        for topic in (meta.get("topics") or [])[:20]:
            self._link_concept(rid, topic, EvidenceType.CONFIG,
                               locator=f"{rid}#topics",
                               excerpt=f"GitHub topic: {topic}",
                               weight=0.5)

        return rid

    # ── filesystem walk ───────────────────────────────────────────────────

    def _ingest_repo_filesystem(self, spec: RepoSpec, rid: str) -> None:
        root = Path(spec.local_path)

        # 4a. Code structure (AST/regex)
        if spec.parse_code:
            try:
                struct = CodeStructureExtractor.extract_directory(
                    str(root), max_files=spec.max_files
                )
                self._adapt_code_structure(rid, root, struct)
            except Exception as e:
                logger.warning("code_structure failed for %s: %s", rid, e)

        # 4b. Cross-file imports (currently emitted as IMPORTS edges)
        if spec.parse_code:
            try:
                cfm = CrossFileLinker.build_dependency_map(
                    str(root), max_files=spec.max_files
                )
                self._adapt_imports(rid, root, cfm)
            except Exception as e:
                logger.warning("cross_file_linker failed for %s: %s", rid, e)

        # 4c. Dependency manifests → Technology nodes
        if spec.parse_dependencies:
            parser = DependencyParser()
            for manifest in self._find_files(root, self.DEP_MANIFESTS):
                try:
                    deps = parser.parse_file(str(manifest))
                except Exception as e:
                    logger.debug("dep parse failed %s: %s", manifest, e)
                    continue
                self._adapt_dependencies(rid, root, manifest, deps)

        # 4d. Deployment configs found in the repo
        if spec.parse_deployment_configs:
            for cfg in self._find_files(root, self.DEPLOY_CONFIGS):
                self._adapt_repo_deployment_config(rid, root, cfg)

        # 4e. ALL markdown docs (not just README) — every doc becomes its own
        # Document/Section subtree. Repos without READMEs but with other docs
        # (e.g. ARCHITECTURE.md, docs/design.md) still get coverage.
        if spec.parse_docs:
            doc_count = 0
            for doc_path in self._find_doc_files(root):
                if doc_count >= 25:                # safety cap per repo
                    break
                try:
                    text = doc_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if not text or len(text) > 500_000:
                    continue
                self._ingest_readme(
                    rid, text,
                    repo_path=str(root),
                    readme_rel_path=str(doc_path.relative_to(root)),
                )
                doc_count += 1
            logger.debug("Ingested %d doc(s) for %s", doc_count, rid)

    # ── code structure adapter ────────────────────────────────────────────

    def _adapt_code_structure(self, rid: str, root: Path, struct: CodeStructure) -> None:
        # Group entities by file
        files_seen: Set[str] = set()
        for ent in struct.entities:
            rel = self._rel(root, ent.file_path)
            f_id = file_id(rid, rel)
            if rel not in files_seen:
                self.graph.add_node(Node(
                    id=f_id,
                    type=NodeType.FILE,
                    label=rel,
                    slug=canonical_slug(rel),
                    provider="github",
                    properties={"path": rel, "repo": rid},
                ))
                self.graph.add_edge(Edge(
                    source=rid, target=f_id, type=EdgeType.CONTAINS, weight=1.0,
                ))
                files_seen.add(rel)

            if ent.entity_type == "function":
                fn_id = function_id(rid, rel, ent.name)
                self.graph.add_node(Node(
                    id=fn_id,
                    type=NodeType.FUNCTION,
                    label=ent.name,
                    slug=canonical_slug(f"{rel}-{ent.name}"),
                    properties={
                        "signature": ent.signature,
                        "line_start": ent.line_start,
                        "line_end": ent.line_end,
                        "decorators": ent.decorators,
                        "docstring": (ent.docstring or "")[:512],
                    },
                ))
                self.graph.add_edge(Edge(
                    source=f_id, target=fn_id, type=EdgeType.DEFINES, weight=1.0,
                ))
            elif ent.entity_type == "class":
                c_id = class_id(rid, rel, ent.name)
                self.graph.add_node(Node(
                    id=c_id,
                    type=NodeType.CLASS,
                    label=ent.name,
                    slug=canonical_slug(f"{rel}-{ent.name}"),
                    properties={
                        "signature": ent.signature,
                        "line_start": ent.line_start,
                        "line_end": ent.line_end,
                        "bases": ent.bases,
                        "decorators": ent.decorators,
                        "docstring": (ent.docstring or "")[:512],
                    },
                ))
                self.graph.add_edge(Edge(
                    source=f_id, target=c_id, type=EdgeType.DEFINES, weight=1.0,
                ))

        # Code relationships → CALLS / INHERITS / CONTAINS_METHOD
        for rel in struct.relationships:
            src = self._translate_code_id(rid, root, rel.source_id)
            tgt = self._translate_code_id(rid, root, rel.target_id)
            if not src or not tgt:
                continue
            etype = {
                "CALLS": EdgeType.CALLS,
                "INHERITS": EdgeType.INHERITS,
                "CONTAINS_METHOD": EdgeType.HAS_MEMBER,
                "CONTAINS": EdgeType.HAS_MEMBER,
            }.get(rel.rel_type)
            if not etype:
                continue
            self.graph.add_edge(Edge(source=src, target=tgt, type=etype, weight=1.0))

    @staticmethod
    def _translate_code_id(rid: str, root: Path, raw_id: str) -> Optional[str]:
        """Translate the extractor's `function:path:name` ids to universal ids."""
        parts = raw_id.split(":", 2)
        if len(parts) != 3:
            return None
        kind, path, name = parts
        if path == "*" or not name:
            return None
        rel = path
        try:
            rel = str(Path(path).resolve().relative_to(root.resolve()))
        except Exception:
            pass
        if kind == "function":
            return function_id(rid, rel, name)
        if kind == "class":
            return class_id(rid, rel, name)
        return None

    # ── imports adapter ───────────────────────────────────────────────────

    def _adapt_imports(self, rid: str, root: Path, cfm) -> None:
        # CrossFileMap: cfm.imports is List[FileImport]
        for imp in getattr(cfm, "imports", []):
            src_rel = self._rel(root, imp.source_file)
            src = file_id(rid, src_rel)
            # Try to resolve import target as a sibling File node;
            # otherwise, encode as an external Module node.
            target = imp.imported_module or ""
            if not target:
                continue
            # Heuristic: if target looks like a relative path, resolve to File
            tgt_rel = target.replace(".", "/")
            candidate = root / tgt_rel
            if candidate.with_suffix(".py").exists() or candidate.with_suffix(".ts").exists() \
                    or candidate.with_suffix(".js").exists() or (candidate / "__init__.py").exists():
                tgt_path = str(candidate.relative_to(root)) + ".py"  # best-effort
                tgt = file_id(rid, tgt_path)
            else:
                # External module → Technology node (top-level package)
                top = target.split(".")[0].split("/")[0]
                self._link_technology(
                    src, top, EvidenceType.SOURCE_CODE,
                    locator=f"{src_rel}",
                    excerpt=f"import {target}",
                    weight=0.6,
                )
                continue
            self.graph.add_edge(Edge(
                source=src, target=tgt, type=EdgeType.IMPORTS, weight=1.0,
            ))

    # ── dependency adapter ────────────────────────────────────────────────

    def _adapt_dependencies(
        self, rid: str, root: Path, manifest: Path, deps: Iterable[Dependency]
    ) -> None:
        rel = self._rel(root, manifest)
        f_id = file_id(rid, rel)
        # Ensure manifest file is a node
        self.graph.add_node(Node(
            id=f_id,
            type=NodeType.FILE,
            label=rel,
            slug=canonical_slug(rel),
            provider="github",
            properties={"path": rel, "repo": rid, "is_manifest": True},
        ))
        self.graph.add_edge(Edge(
            source=rid, target=f_id, type=EdgeType.CONTAINS, weight=1.0,
        ))

        for dep in deps:
            self._link_technology(
                rid, dep.name, EvidenceType.DEPENDENCY,
                locator=rel,
                excerpt=f"{dep.name} {dep.version_spec or ''}{dep.version or ''}".strip(),
                weight=0.7,
                target_label=canonicalize_technology(dep.name),
                extra_props={"version": dep.version, "dev": dep.dev},
            )

    # ── deployment configs found inside a repo ────────────────────────────

    def _adapt_repo_deployment_config(self, rid: str, root: Path, cfg: Path) -> None:
        rel = self._rel(root, cfg)
        f_id = file_id(rid, rel)
        self.graph.add_node(Node(
            id=f_id,
            type=NodeType.FILE,
            label=rel,
            slug=canonical_slug(rel),
            provider="github",
            properties={"path": rel, "repo": rid, "is_deploy_config": True},
        ))
        self.graph.add_edge(Edge(
            source=rid, target=f_id, type=EdgeType.CONTAINS, weight=1.0,
        ))

        # Emit a USES technology link for the platform implied by the file
        platform = self._platform_from_filename(cfg.name)
        if platform:
            self._link_technology(
                rid, platform, EvidenceType.CONFIG,
                locator=rel,
                excerpt=f"Found {cfg.name}",
                weight=0.6,
            )

        # vercel.json / wrangler.toml: produce parsed routes
        try:
            if cfg.name == "vercel.json":
                a = DeploymentAnalyzer.analyze_vercel_json(str(cfg))
            elif cfg.name == "wrangler.toml":
                a = DeploymentAnalyzer.analyze_wrangler_toml(str(cfg))
            else:
                a = None
        except Exception:
            a = None
        if a:
            self._adapt_deployment_analysis(rid, a, source_locator=rel,
                                            evidence_type=EvidenceType.CONFIG)

    @staticmethod
    def _platform_from_filename(name: str) -> Optional[str]:
        return {
            "vercel.json": "Vercel",
            "wrangler.toml": "Cloudflare",
            "netlify.toml": "Netlify",
            "fly.toml": "Fly.io",
            "railway.json": "Railway",
            "Dockerfile": "Docker",
            "docker-compose.yml": "Docker",
            "docker-compose.yaml": "Docker",
        }.get(name)

    # ── README → Document/Section + DOCUMENTS edges ───────────────────────

    def _ingest_readme(
        self,
        rid: str,
        content: str,
        *,
        repo_path: str = "",
        readme_rel_path: str = "README.md",
    ) -> None:
        d_id = document_id(rid, readme_rel_path)
        repo_node = self.graph.get(rid)
        repo_label = repo_node.label if repo_node else rid
        self.graph.add_node(Node(
            id=d_id,
            type=NodeType.DOCUMENT,
            label=f"{repo_label} — {readme_rel_path}",
            slug=canonical_slug(f"{repo_label}-{readme_rel_path}"),
            provider="github",
            properties={"repo": rid, "path": readme_rel_path,
                        "length_chars": len(content)},
        ))
        self.graph.add_edge(Edge(
            source=d_id, target=rid, type=EdgeType.DOCUMENTS, weight=1.0,
        ))
        self.graph.add_edge(Edge(
            source=rid, target=d_id, type=EdgeType.CONTAINS, weight=1.0,
        ))

        # Sections via DocCodeLinker.parse_readme
        sections = DocCodeLinker.parse_readme(content)
        for section in sections:
            s_id = section_id(d_id, section.heading)
            self.graph.add_node(Node(
                id=s_id,
                type=NodeType.SECTION,
                label=section.heading,
                slug=canonical_slug(f"{readme_rel_path}-{section.heading}"),
                properties={
                    "heading": section.heading,
                    "level": section.level,
                    "keywords": list(section.keywords)[:30],
                    "preview": (section.content or "")[:300],
                },
            ))
            self.graph.add_edge(Edge(
                source=d_id, target=s_id, type=EdgeType.CONTAINS, weight=1.0,
            ))

            # Section keywords → Concept nodes (light-touch)
            for kw in list(section.keywords)[:8]:
                if len(kw) < 4:
                    continue
                self._link_concept(s_id, kw, EvidenceType.DOC,
                                   locator=f"{readme_rel_path}#{section.heading}",
                                   excerpt=section.heading,
                                   weight=0.35)

            # Match section to source files (DocLinks)
            if repo_path:
                try:
                    links = DocCodeLinker.match_section_to_files(section, repo_path)
                except Exception:
                    links = []
                for dl in links[:5]:
                    rel_target = self._rel(Path(repo_path), dl.file_path)
                    tgt = file_id(rid, rel_target)
                    self.graph.add_edge(Edge(
                        source=s_id, target=tgt,
                        type=EdgeType.DOCUMENTS, weight=0.8,
                        properties={"match_type": getattr(dl, "match_type", "")},
                    ))

    # ── deployment from collector data ────────────────────────────────────

    def add_vercel_project(self, project_data: Dict[str, Any]) -> str:
        """Add a Vercel project (raw collector dict) to the graph."""
        analysis = DeploymentAnalyzer.analyze_vercel_project(project_data)
        name = project_data.get("name") or project_data.get("id") or "vercel-project"
        ident = project_data.get("id") or project_data.get("name") or canonical_slug(name)
        d_id = deployment_id("vercel", name, ident)
        prod_url = (
            (project_data.get("targets") or {}).get("production", {}).get("url")
            or project_data.get("url")
        )
        domains = [d.name for d in analysis.domains]
        node = Node(
            id=d_id,
            type=NodeType.DEPLOYMENT,
            label=name,
            slug=canonical_slug(name),
            provider="vercel",
            properties={
                "framework": analysis.framework,
                "production_url": prod_url,
                "domains": domains,
                "env_count": sum(1 for c in analysis.configs if c.config_type == "env_var"),
            },
            tags=["vercel"] + ([analysis.framework] if analysis.framework else []),
            created=_parse_dt(project_data.get("createdAt")),
            updated=_parse_dt(project_data.get("updatedAt")),
        )
        self.graph.add_node(node)
        if self.person_id:
            self.graph.add_edge(Edge(
                source=self.person_id, target=d_id, type=EdgeType.OWNS, weight=1.0,
            ))
        # Link to repo if Vercel knows the linked GitHub repo
        repo_link = project_data.get("link") or {}
        if isinstance(repo_link, dict):
            repo_full = repo_link.get("repo") or repo_link.get("fullName")
            if repo_full and "/" in repo_full:
                owner, rname = repo_full.split("/", 1)
                self.graph.add_edge(Edge(
                    source=repo_id(owner, rname),
                    target=d_id,
                    type=EdgeType.DEPLOYS_TO,
                    weight=1.0,
                ))
        # Vercel as a technology
        self._link_technology(d_id, "Vercel", EvidenceType.DEPLOYMENT,
                              locator=f"vercel://{ident}",
                              excerpt=f"Hosted on Vercel: {name}",
                              weight=0.9)
        if analysis.framework:
            self._link_technology(d_id, analysis.framework, EvidenceType.DEPLOYMENT,
                                  locator=f"vercel://{ident}",
                                  excerpt=f"Framework: {analysis.framework}",
                                  weight=0.7)
        self._adapt_deployment_analysis(d_id, analysis,
                                        source_locator=f"vercel://{ident}",
                                        evidence_type=EvidenceType.DEPLOYMENT)
        return d_id

    def add_cloudflare_worker(self, worker_data: Dict[str, Any]) -> str:
        analysis = DeploymentAnalyzer.analyze_cloudflare_worker(worker_data)
        name = worker_data.get("id") or worker_data.get("name") or "cf-worker"
        d_id = deployment_id("cloudflare", name, name)
        node = Node(
            id=d_id,
            type=NodeType.DEPLOYMENT,
            label=name,
            slug=canonical_slug(name),
            provider="cloudflare",
            properties={
                "kind": "worker",
                "domains": [d.name for d in analysis.domains],
            },
            tags=["cloudflare", "worker"],
            updated=_parse_dt(worker_data.get("modified_on")),
        )
        self.graph.add_node(node)
        if self.person_id:
            self.graph.add_edge(Edge(
                source=self.person_id, target=d_id, type=EdgeType.OWNS, weight=1.0,
            ))
        self._link_technology(d_id, "Cloudflare", EvidenceType.DEPLOYMENT,
                              locator=f"cf://{name}",
                              excerpt=f"Worker: {name}", weight=0.9)
        self._link_technology(d_id, "Cloudflare Workers", EvidenceType.DEPLOYMENT,
                              locator=f"cf://{name}",
                              excerpt=f"Worker: {name}", weight=0.8)
        self._adapt_deployment_analysis(d_id, analysis,
                                        source_locator=f"cf://{name}",
                                        evidence_type=EvidenceType.DEPLOYMENT)
        return d_id

    def _adapt_deployment_analysis(
        self,
        owner_id: str,
        analysis: DeploymentAnalysis,
        *,
        source_locator: str,
        evidence_type: EvidenceType,
    ) -> None:
        # Domains → Domain nodes + SERVES edges
        for d in analysis.domains:
            if not d.name:
                continue
            dom_id = f"domain:{canonical_slug(d.name)}"
            self.graph.add_node(Node(
                id=dom_id,
                type=NodeType.DOMAIN,
                label=d.name,
                slug=canonical_slug(d.name),
                provider="manual",
                properties={"verified": bool(d.verified)},
            ))
            self.graph.add_edge(Edge(
                source=owner_id, target=dom_id, type=EdgeType.SERVES, weight=1.0,
            ))
        # Routes
        for r in analysis.routes:
            if not r.source:
                continue
            r_id = f"route:{canonical_slug(owner_id + r.source)}"
            self.graph.add_node(Node(
                id=r_id, type=NodeType.ROUTE,
                label=r.source,
                slug=canonical_slug(r.source),
                properties={"source": r.source, "destination": r.destination},
            ))
            self.graph.add_edge(Edge(
                source=owner_id, target=r_id, type=EdgeType.SERVES, weight=1.0,
            ))

    # ── conversation/artifact ingestion ───────────────────────────────────

    def add_conversation(self, data: Dict[str, Any]) -> str:
        provider = data.get("provider", "manual")
        ident = data.get("id") or data.get("slug") or canonical_slug(data.get("title", "conversation"))
        c_id = conversation_id(provider, ident)
        title = data.get("title") or ident
        body = data.get("text") or data.get("body") or ""
        node = Node(
            id=c_id,
            type=NodeType.CONVERSATION,
            label=title,
            slug=canonical_slug(title),
            provider=provider,
            properties={
                "summary": (data.get("summary") or body[:300]),
                "length_chars": len(body),
            },
            tags=list(data.get("tags", [])),
            created=_parse_dt(data.get("created_at")),
            updated=_parse_dt(data.get("updated_at")),
        )
        self.graph.add_node(node)
        if self.person_id:
            self.graph.add_edge(Edge(
                source=self.person_id, target=c_id, type=EdgeType.AUTHORED, weight=0.6,
            ))
        # Optional: link to mentioned repos by id
        for mentioned in data.get("mentions_repos", []):
            if "/" in mentioned:
                o, r = mentioned.split("/", 1)
                self.graph.add_edge(Edge(
                    source=c_id, target=repo_id(o, r),
                    type=EdgeType.MENTIONS, weight=0.5,
                ))
        return c_id

    # ── primitives shared by many adapters ────────────────────────────────

    def _link_technology(
        self,
        source_node_id: str,
        raw_name: str,
        ev_type: EvidenceType,
        *,
        locator: str,
        excerpt: str,
        weight: float = 0.7,
        target_label: Optional[str] = None,
        extra_props: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not raw_name or len(raw_name) > 80:
            return ""
        label = target_label or canonicalize_technology(raw_name)
        t_id = technology_id(label)
        self.graph.add_node(Node(
            id=t_id,
            type=NodeType.TECHNOLOGY,
            label=label,
            slug=canonical_slug(label),
            properties={**(extra_props or {})},
        ))
        edge = self.graph.add_edge(Edge(
            source=source_node_id, target=t_id, type=EdgeType.USES, weight=weight,
        ))
        ev = Evidence(
            evidence_type=ev_type, source_node_id=source_node_id,
            locator=locator, excerpt=excerpt[:512],
        )
        self.graph.attach_evidence(edge.key, ev)
        return t_id

    def _link_concept(
        self,
        source_node_id: str,
        raw_name: str,
        ev_type: EvidenceType,
        *,
        locator: str,
        excerpt: str,
        weight: float = 0.4,
    ) -> str:
        if not raw_name or len(raw_name) > 80:
            return ""
        c_id = concept_id(raw_name)
        self.graph.add_node(Node(
            id=c_id,
            type=NodeType.CONCEPT,
            label=raw_name,
            slug=canonical_slug(raw_name),
        ))
        edge = self.graph.add_edge(Edge(
            source=source_node_id, target=c_id, type=EdgeType.IMPLEMENTS, weight=weight,
        ))
        ev = Evidence(
            evidence_type=ev_type, source_node_id=source_node_id,
            locator=locator, excerpt=excerpt[:512],
        )
        self.graph.attach_evidence(edge.key, ev)
        return c_id

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _rel(root: Path, p: str | Path) -> str:
        try:
            return str(Path(p).resolve().relative_to(root.resolve()))
        except Exception:
            return str(p)

    @staticmethod
    def _find_files(root: Path, names: Set[str]) -> List[Path]:
        from ..extractors._walk import iter_files, SKIP_DIRS  # noqa: F401
        out: List[Path] = []
        for p in iter_files(root, extensions=None, max_visit=10000):
            if p.name in names:
                out.append(p)
        return out

    # Doc discovery: any markdown that documents the repo, prioritised so the
    # most important docs are ingested first (per-repo budget).
    _PRIORITY_DOCS = (
        "README.md", "Readme.md", "readme.md", "README.MD", "README",
        "ARCHITECTURE.md", "DESIGN.md", "CONTRIBUTING.md",
        "OVERVIEW.md", "GETTING_STARTED.md", "QUICKSTART.md",
        "USAGE.md", "ROADMAP.md", "CHANGELOG.md",
    )
    # Folders worth scanning for additional docs.
    _DOC_FOLDERS = ("docs", "doc", "documentation", "wiki", "guides", ".github")

    @classmethod
    def _find_doc_files(cls, root: Path) -> List[Path]:
        from ..extractors._walk import iter_files
        seen: Set[Path] = set()
        out: List[Path] = []

        def _add(p: Path) -> None:
            try:
                rp = p.resolve()
            except Exception:
                return
            if rp in seen or not p.is_file():
                return
            seen.add(rp)
            out.append(p)

        # 1. Top-level priority docs first
        for name in cls._PRIORITY_DOCS:
            _add(root / name)
        # 2. Any markdown in known doc folders
        for folder in cls._DOC_FOLDERS:
            d = root / folder
            if d.is_dir():
                for p in iter_files(d, extensions=(".md", ".mdx"), max_visit=2000):
                    _add(p)
        # 3. Top-level README/CONTRIBUTING in subprojects (capped)
        scanned = 0
        for p in iter_files(root, extensions=(".md", ".mdx"), max_visit=2000):
            if scanned >= 30:
                break
            name = p.name.lower()
            if name.startswith("readme") or name in (
                "contributing.md", "architecture.md", "design.md",
                "overview.md", "roadmap.md",
            ):
                _add(p)
                scanned += 1
        return out

    # ── finalize ──────────────────────────────────────────────────────────

    def finalize(self) -> UniversalGraph:
        self.graph.recompute_node_confidences()
        self.graph.metadata["built_at"] = datetime.now(timezone.utc).isoformat()
        self.graph.metadata["builder_version"] = "1.0"
        return self.graph


# ── helpers ───────────────────────────────────────────────────────────────


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val)
    try:
        # Tolerate trailing Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None
