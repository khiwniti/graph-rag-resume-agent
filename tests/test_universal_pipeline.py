"""End-to-end smoke test: builds a universal graph from an in-memory fixture
repo, runs the exporters, and asserts both integration contracts hold.

The fixture repo is materialised on a tmp_path so the AST/dependency/doc
extractors all see real files.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.builders import RepoSpec, UniversalGraphBuilder
from app.exporters import export_graph_json, export_wiki_vault
from app.schema import NodeType, EdgeType


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """A small but representative repo: code + manifest + README + vercel.json."""
    root = tmp_path / "demo-repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "from .utils import greet\n"
        "\n"
        "app = FastAPI()\n"
        "\n"
        "class GreetingService:\n"
        "    def hello(self, name: str) -> str:\n"
        "        return greet(name)\n"
        "\n"
        "@app.get('/')\n"
        "def root():\n"
        "    return GreetingService().hello('world')\n"
    )
    (root / "src" / "utils.py").write_text(
        "def greet(name: str) -> str:\n"
        "    return f'hello {name}'\n"
    )
    (root / "requirements.txt").write_text(
        "fastapi==0.110.0\nuvicorn==0.27.0\nneo4j==5.18.0\n"
    )
    (root / "README.md").write_text(
        "# Demo Repo\n\n"
        "A tiny FastAPI service that demonstrates RAG over a knowledge graph.\n\n"
        "## Architecture\n\n"
        "Uses Neo4j for the graph and FAISS for vector search.\n\n"
        "## Endpoints\n\n"
        "- `GET /` returns a greeting from `src/main.py`.\n"
    )
    (root / "vercel.json").write_text(
        '{"version":2, "routes":[{"src":"/(.*)", "dest":"/api/main"}]}'
    )
    return root


def _build_graph(fixture_repo: Path):
    b = UniversalGraphBuilder(person_login="testuser")
    b.add_repo(RepoSpec(
        owner="testuser", name="demo-repo",
        local_path=str(fixture_repo),
        metadata={"description": "demo", "language": "Python",
                  "languages": {"Python": 1000}, "topics": ["rag", "graph"]},
        max_files=50,
    ))
    return b.finalize()


def test_universal_graph_produces_expected_node_types(fixture_repo: Path) -> None:
    g = _build_graph(fixture_repo)
    types = {n.type for n in g.nodes.values()}
    # Core types must be present
    for required in (
        NodeType.PERSON, NodeType.REPO, NodeType.FILE, NodeType.FUNCTION,
        NodeType.CLASS, NodeType.TECHNOLOGY, NodeType.DOCUMENT,
        NodeType.SECTION,
    ):
        assert required in types, f"missing node type: {required}"


def test_dependency_evidence_attached_to_uses_edges(fixture_repo: Path) -> None:
    g = _build_graph(fixture_repo)
    # Find the FastAPI tech node + USES edge from the repo with dependency evidence
    fastapi_uses = [
        e for e in g.edges.values()
        if e.type == EdgeType.USES and e.target.endswith("fastapi")
    ]
    assert fastapi_uses, "expected a USES edge -> tech:fastapi"
    edge = fastapi_uses[0]
    assert edge.evidence, "expected at least one Evidence id on the USES edge"
    ev = g.evidence[edge.evidence[0]]
    assert ev.evidence_type.value in ("dependency", "source_code")
    assert "fastapi" in ev.excerpt.lower() or ev.locator.endswith("requirements.txt")


def test_graph_json_export_matches_consumer_contract(
    fixture_repo: Path, tmp_path: Path
) -> None:
    g = _build_graph(fixture_repo)
    out = export_graph_json(g, tmp_path / "kg.json")
    data = json.loads(out.read_text())
    # GraphConnector requires nodes[].id, .type, .properties; edges[].from/.to/.type
    assert "nodes" in data and "edges" in data
    assert all({"id", "type", "properties"}.issubset(n) for n in data["nodes"])
    assert all({"from", "to", "type"}.issubset(e) for e in data["edges"])


def test_wiki_vault_export_creates_obsidian_pages(
    fixture_repo: Path, tmp_path: Path
) -> None:
    g = _build_graph(fixture_repo)
    vault = export_wiki_vault(g, tmp_path / "vault")
    # Must produce a repo page, at least one skill/tech page, and an index.
    assert (vault / "index.md").exists()
    assert (vault / "SCHEMA.md").exists()
    repos = list((vault / "repos").glob("*.md"))
    assert repos, "expected at least one repo page"
    # The repo page must contain wikilinks and frontmatter.
    repo_md = repos[0].read_text()
    assert repo_md.startswith("---"), "missing YAML frontmatter"
    assert "type: 'repo'" in repo_md
    assert "[[" in repo_md and "]]" in repo_md, "expected wikilinks"
    # And at least one skills/<tech>.md should exist (FastAPI / Neo4j / Uvicorn)
    skills = list((vault / "skills").glob("*.md"))
    assert skills, "expected technology pages under /skills"


def test_recompute_confidence_aggregates_evidence(fixture_repo: Path) -> None:
    g = _build_graph(fixture_repo)
    # All technology nodes must have a confidence in (0, 1].
    techs = [n for n in g.nodes.values() if n.type == NodeType.TECHNOLOGY]
    assert techs, "expected technology nodes"
    for t in techs:
        assert 0.0 < t.confidence <= 1.0
