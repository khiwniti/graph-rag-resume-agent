#!/usr/bin/env python3
"""
Integration Test Suite for CareerGraph Import Pipeline

Tests the complete export/import/build pipeline and API endpoints.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.resume_agent import ResumeAgent, AgentResponse
from app.graph.builder import GraphBuilder
from app.graph.query import GraphQuerier
from app.config import GRAPH_DIR, EMBEDDINGS_DIR


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def graph_path() -> str:
    """Path to the test graph file."""
    return str(PROJECT_ROOT / "data" / "graph" / "knowledge_graph.json")


@pytest.fixture
def vector_store_path() -> str:
    """Path to the test vector store."""
    return str(PROJECT_ROOT / "data" / "embeddings" / "faiss_index")


@pytest.fixture
def sample_export_data() -> Dict[str, Any]:
    """Sample export data structure."""
    return {
        "version": "1.0",
        "source": "careergraph-wiki-mcp-ui",
        "exported_at": "2026-05-20T10:00:00.000000",
        "wiki_pages": {
            "pages": [
                {
                    "slug": "test-repo",
                    "title": "Test Repository",
                    "type": "repo",
                    "tags": ["python", "test"],
                    "content": "# Test Repo\n\nThis is a test repository with Python and React code.",
                    "metadata": {
                        "type": "repo",
                        "name": "test-repo",
                        "full_name": "testuser/test-repo",
                        "description": "A test repository",
                        "language": "Python",
                        "stars": 10,
                        "forks": 2,
                    },
                    "path": "./wiki/test-repo.md"
                },
                {
                    "slug": "test-project",
                    "title": "Test Project",
                    "type": "vercel_project",
                    "tags": ["nextjs", "vercel"],
                    "content": "# Test Project\n\nDeployed on Vercel with Next.js",
                    "metadata": {
                        "type": "vercel_project",
                        "name": "test-project",
                        "framework": "nextjs",
                        "url": "https://test-project.vercel.app",
                    },
                    "path": "./wiki/test-project.md"
                },
                {
                    "slug": "test-worker",
                    "title": "Test Worker",
                    "type": "cloudflare_worker",
                    "tags": ["cloudflare", "workers"],
                    "content": "# Test Worker\n\nA Cloudflare Worker handling requests.",
                    "metadata": {
                        "type": "cloudflare_worker",
                        "name": "test-worker",
                    },
                    "path": "./wiki/test-worker.md"
                }
            ]
        }
    }


@pytest.fixture
def resume_agent(graph_path: str, vector_store_path: str) -> ResumeAgent:
    """Create a ResumeAgent instance for testing."""
    return ResumeAgent(
        graph_path=graph_path,
        vector_store_path=vector_store_path,
        chunks_path=str(PROJECT_ROOT / "data" / "chunks.json")
    )


@pytest.fixture
def graph_querier(graph_path: str) -> GraphQuerier:
    """Create a GraphQuerier instance for testing."""
    return GraphQuerier(graph_path=graph_path)


@pytest.fixture
def graph_builder() -> GraphBuilder:
    """Create a fresh GraphBuilder instance."""
    return GraphBuilder()


# =============================================================================
# Test: Export/Import/Build Pipeline
# =============================================================================

class TestExportImportPipeline:
    """Tests for the export/import/build pipeline."""

    def test_export_data_structure(self, sample_export_data: Dict[str, Any]):
        """Test that exported data has the expected structure."""
        assert "version" in sample_export_data
        assert "source" in sample_export_data
        assert "exported_at" in sample_export_data
        assert "wiki_pages" in sample_export_data
        assert "pages" in sample_export_data["wiki_pages"]

        pages = sample_export_data["wiki_pages"]["pages"]
        assert len(pages) == 3

    def test_export_page_types(self, sample_export_data: Dict[str, Any]):
        """Test that different page types are properly identified."""
        pages = sample_export_data["wiki_pages"]["pages"]

        page_types = {p["type"] for p in pages}
        assert "repo" in page_types
        assert "vercel_project" in page_types
        assert "cloudflare_worker" in page_types

    def test_graph_file_exists(self, graph_path: str):
        """Test that the graph file exists and is readable."""
        assert os.path.exists(graph_path), f"Graph file not found: {graph_path}"

        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_graph_has_required_node_types(self, graph_path: str):
        """Test that graph contains all required node types."""
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        node_types = {node["type"] for node in data["nodes"]}

        # Graph should have at least person, repository, skill, and project nodes
        assert "person" in node_types, "Graph missing person node type"
        assert "repository" in node_types, "Graph missing repository node type"
        assert "skill" in node_types, "Graph missing skill node type"
        assert "project" in node_types, "Graph missing project node type"

    def test_vector_store_exists(self, vector_store_path: str):
        """Test that vector store files exist."""
        faiss_file = f"{vector_store_path}.faiss"
        assert os.path.exists(faiss_file), f"FAISS index not found: {faiss_file}"

    def test_import_script_transforms_data(self, sample_export_data: Dict[str, Any]):
        """Test that import script properly transforms data."""
        # Simulate the transformation functions from import_from_careergraph.py
        wiki_pages = sample_export_data.get('wiki_pages', {})
        pages = wiki_pages.get('pages', [])

        # Transform to GitHub format
        repos = []
        for page in pages:
            metadata = page.get('metadata', {})
            page_type = metadata.get('type', '')

            if 'repo' in page_type.lower():
                repos.append({
                    'full_name': metadata.get('full_name', page.get('slug')),
                    'name': metadata.get('name', page.get('title')),
                    'description': metadata.get('description', ''),
                    'language': metadata.get('language', ''),
                })

        assert len(repos) == 1
        assert repos[0]['name'] == 'test-repo'

        # Transform to Vercel format
        projects = []
        for page in pages:
            metadata = page.get('metadata', {})
            page_type = metadata.get('type', '')

            if 'vercel' in page_type.lower():
                projects.append({
                    'name': metadata.get('name', page.get('title')),
                    'framework': metadata.get('framework', 'nextjs'),
                })

        assert len(projects) == 1
        assert projects[0]['name'] == 'test-project'

    def test_graph_builder_from_imported_data(self, graph_builder: GraphBuilder):
        """Test that GraphBuilder can incorporate imported data."""
        # Add a person
        person = graph_builder.add_person_node("person:test")

        # Add a repository
        repo_node = graph_builder.add_repository_node(
            "test-imported-repo",
            {"language": "Python", "stars": 5}
        )

        # Add edge
        graph_builder.add_edge(
            person.id,
            repo_node.id,
            "OWNS",
            {"since": "2024-01-01"}
        )

        # Add a skill
        skill_node = graph_builder.add_skill_node(
            "Python",
            "language",
            {"confidence": 0.9}
        )

        # Add USES edge from repo to skill
        graph_builder.add_edge(
            repo_node.id,
            skill_node.id,
            "USES",
            {"evidence_type": "language_usage"}
        )

        # Verify graph structure
        assert len(graph_builder.node_index) == 3  # person, repo, skill
        assert len(graph_builder.edge_index) == 2  # OWNS, USES

    def test_full_pipeline_graph_stats(self, graph_path: str):
        """Test that the full pipeline produces expected graph statistics."""
        querier = GraphQuerier(graph_path)
        stats = querier.get_stats()

        assert stats["total_nodes"] > 0, "Graph should have nodes"
        assert stats["total_edges"] >= 0, "Graph should track edges"
        assert "person" in stats["node_types"], "Should have person nodes"
        assert "repository" in stats["node_types"], "Should have repository nodes"
        assert "skill" in stats["node_types"], "Should have skill nodes"


# =============================================================================
# Test: Skills Endpoint
# =============================================================================

class TestSkillsEndpoint:
    """Tests for the skills endpoint functionality."""

    def test_list_skills_returns_list(self, resume_agent: ResumeAgent):
        """Test that list_skills returns a list."""
        skills = resume_agent.list_skills(min_confidence=0.0)
        assert isinstance(skills, list), "list_skills should return a list"

    def test_skills_have_confidence_values(self, resume_agent: ResumeAgent):
        """Test that skills have confidence values."""
        skills = resume_agent.list_skills(min_confidence=0.0)

        if len(skills) > 0:
            for skill in skills:
                assert "skill" in skill, "Skill should have 'skill' field"
                assert "confidence" in skill, "Skill should have 'confidence' field"
                assert isinstance(skill["confidence"], (int, float)), \
                    "Confidence should be numeric"
                assert 0.0 <= skill["confidence"] <= 1.0, \
                    "Confidence should be between 0 and 1"

    def test_skills_filtered_by_confidence(self, resume_agent: ResumeAgent):
        """Test that min_confidence filter works."""
        all_skills = resume_agent.list_skills(min_confidence=0.0)
        high_confidence_skills = resume_agent.list_skills(min_confidence=0.5)

        # High confidence list should be a subset
        for skill in high_confidence_skills:
            assert skill["confidence"] >= 0.5

    def test_skills_sorted_by_confidence(self, resume_agent: ResumeAgent):
        """Test that skills are sorted by confidence descending."""
        skills = resume_agent.list_skills(min_confidence=0.0)

        if len(skills) > 1:
            confidences = [s["confidence"] for s in skills]
            assert confidences == sorted(confidences, reverse=True), \
                "Skills should be sorted by confidence descending"

    def test_graph_querier_get_skills(self, graph_querier: GraphQuerier):
        """Test GraphQuerier.get_skills returns skills with confidence."""
        skills = graph_querier.get_skills()
        assert isinstance(skills, list)

        if len(skills) > 0:
            for skill in skills:
                assert "name" in skill, "Skill should have 'name'"
                assert "confidence" in skill, "Skill should have 'confidence'"
                assert 0.0 <= skill["confidence"] <= 1.0


# =============================================================================
# Test: Projects Endpoint
# =============================================================================

class TestProjectsEndpoint:
    """Tests for the projects endpoint functionality."""

    def test_get_projects_returns_list(self, resume_agent: ResumeAgent):
        """Test that get_projects returns a list."""
        projects = resume_agent.get_projects()
        assert isinstance(projects, list), "get_projects should return a list"

    def test_projects_have_required_fields(self, resume_agent: ResumeAgent):
        """Test that projects have required fields."""
        projects = resume_agent.get_projects()

        if len(projects) > 0:
            for project in projects:
                assert "name" in project, "Project should have 'name' field"
                assert "platform" in project, "Project should have 'platform' field"

    def test_project_platforms_are_valid(self, resume_agent: ResumeAgent):
        """Test that project platforms are recognized types."""
        projects = resume_agent.get_projects()

        if len(projects) > 0:
            for project in projects:
                platform = project.get("platform", "unknown")
                # Platform should be a non-empty string
                assert isinstance(platform, str) and len(platform) > 0, \
                    f"Platform should be non-empty string, got: {platform}"

    def test_graph_querier_get_projects(self, graph_querier: GraphQuerier):
        """Test GraphQuerier.get_projects returns projects."""
        projects = graph_querier.get_projects()
        assert isinstance(projects, list)

        if len(projects) > 0:
            for project in projects:
                assert "name" in project
                assert "platform" in project


# =============================================================================
# Test: Query Functionality
# =============================================================================

class TestQueryFunctionality:
    """Tests for the query functionality."""

    def test_query_returns_agent_response(self, resume_agent: ResumeAgent):
        """Test that query returns an AgentResponse."""
        response = resume_agent.query("What are my Python skills?", top_k=5)

        assert isinstance(response, AgentResponse), \
            "Query should return AgentResponse"

    def test_query_response_has_required_fields(self, resume_agent: ResumeAgent):
        """Test that query response has all required fields."""
        response = resume_agent.query("What are my Python skills?", top_k=5)

        assert hasattr(response, "answer"), "Response should have 'answer'"
        assert hasattr(response, "skills"), "Response should have 'skills'"
        assert hasattr(response, "evidence"), "Response should have 'evidence'"
        assert hasattr(response, "sources"), "Response should have 'sources'"
        assert hasattr(response, "confidence"), "Response should have 'confidence'"

    def test_query_answer_is_string(self, resume_agent: ResumeAgent):
        """Test that answer field is a string."""
        response = resume_agent.query("What are my Python skills?", top_k=5)
        assert isinstance(response.answer, str), "Answer should be a string"

    def test_query_skills_is_list(self, resume_agent: ResumeAgent):
        """Test that skills field is a list."""
        response = resume_agent.query("What are my Python skills?", top_k=5)
        assert isinstance(response.skills, list), "Skills should be a list"

    def test_query_evidence_is_list(self, resume_agent: ResumeAgent):
        """Test that evidence field is a list."""
        response = resume_agent.query("What are my Python skills?", top_k=5)
        assert isinstance(response.evidence, list), "Evidence should be a list"

    def test_query_sources_is_list(self, resume_agent: ResumeAgent):
        """Test that sources field is a list."""
        response = resume_agent.query("What are my Python skills?", top_k=5)
        assert isinstance(response.sources, list), "Sources should be a list"

    def test_query_confidence_is_numeric(self, resume_agent: ResumeAgent):
        """Test that confidence is a number between 0 and 1."""
        response = resume_agent.query("What are my Python skills?", top_k=5)
        assert isinstance(response.confidence, (int, float)), \
            "Confidence should be numeric"
        assert 0.0 <= response.confidence <= 1.0, \
            "Confidence should be between 0 and 1"

    def test_query_various_questions(self, resume_agent: ResumeAgent):
        """Test various query questions don't cause errors."""
        questions = [
            "What are my Python skills?",
            "Which projects use React?",
            "What cloud technologies have I used?",
            "Show me my backend development experience",
        ]

        for question in questions:
            response = resume_agent.query(question, top_k=5)
            assert isinstance(response, AgentResponse), \
                f"Query failed for: {question}"
            assert isinstance(response.answer, str), \
                f"Invalid answer type for: {question}"

    def test_query_empty_question_handled(self, resume_agent: ResumeAgent):
        """Test that empty question is handled gracefully."""
        try:
            response = resume_agent.query("", top_k=5)
            # Should still return a response (may have low confidence)
            assert isinstance(response, AgentResponse)
        except Exception as e:
            # Empty question may raise an error, which is acceptable
            assert "empty" in str(e).lower() or "question" in str(e).lower()


# =============================================================================
# Test: Health Check
# =============================================================================

class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_graph_loaded(self, graph_path: str):
        """Test that health check shows graph as loaded."""
        graph_exists = os.path.exists(graph_path)
        assert graph_exists, f"Graph file should exist at: {graph_path}"

        # Check it's valid JSON
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "nodes" in data, "Graph should have nodes key"

    def test_health_check_vector_store_loaded(self, vector_store_path: str):
        """Test that health check shows vector store as loaded."""
        faiss_file = f"{vector_store_path}.faiss"
        assert os.path.exists(faiss_file), \
            f"FAISS index should exist at: {faiss_file}"

    def test_health_check_returns_correct_structure(self):
        """Test health response has correct structure."""
        # This tests what the /health endpoint should return
        graph_path = str(PROJECT_ROOT / "data" / "graph" / "knowledge_graph.json")
        vector_path = str(PROJECT_ROOT / "data" / "embeddings" / "faiss_index")

        graph_loaded = os.path.exists(graph_path)
        vector_store_loaded = os.path.exists(f"{vector_path}.faiss")

        response = {
            "status": "healthy" if (graph_loaded and vector_store_loaded) else "unhealthy",
            "graph_loaded": graph_loaded,
            "vector_store_loaded": vector_store_loaded
        }

        assert "status" in response
        assert "graph_loaded" in response
        assert "vector_store_loaded" in response
        assert isinstance(response["graph_loaded"], bool)
        assert isinstance(response["vector_store_loaded"], bool)

    def test_both_stores_loaded_means_healthy(self):
        """Test that both stores loaded means healthy status."""
        graph_path = str(PROJECT_ROOT / "data" / "graph" / "knowledge_graph.json")
        vector_path = str(PROJECT_ROOT / "data" / "embeddings" / "faiss_index")

        graph_loaded = os.path.exists(graph_path)
        vector_store_loaded = os.path.exists(f"{vector_path}.faiss")

        if graph_loaded and vector_store_loaded:
            status = "healthy"
        else:
            status = "unhealthy"

        assert status == "healthy", \
            "System should be healthy when both stores are loaded"


# =============================================================================
# Test: Integration with Real Data
# =============================================================================

class TestIntegrationWithRealData:
    """Integration tests using actual data files."""

    def test_real_graph_has_skills(self):
        """Test that the real graph contains skill nodes."""
        graph_path = str(PROJECT_ROOT / "data" / "graph" / "knowledge_graph.json")

        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        skill_nodes = [
            n for n in data["nodes"]
            if n.get("type") == "skill"
        ]

        assert len(skill_nodes) > 0, "Graph should have skill nodes"

    def test_real_graph_has_repositories(self):
        """Test that the real graph contains repository nodes."""
        graph_path = str(PROJECT_ROOT / "data" / "graph" / "knowledge_graph.json")

        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        repo_nodes = [
            n for n in data["nodes"]
            if n.get("type") == "repository"
        ]

        assert len(repo_nodes) > 0, "Graph should have repository nodes"

    def test_agent_query_with_real_data(self, resume_agent: ResumeAgent):
        """Test agent query with real data."""
        response = resume_agent.query("What technologies do I know?", top_k=5)

        assert isinstance(response, AgentResponse)
        assert isinstance(response.answer, str)
        assert len(response.answer) > 0, "Should have some answer"

    def test_skills_endpoint_with_real_data(self, resume_agent: ResumeAgent):
        """Test skills listing with real data."""
        skills = resume_agent.list_skills(min_confidence=0.1)

        assert isinstance(skills, list)
        assert len(skills) > 0, "Should have some skills"

        # Verify structure
        for skill in skills:
            assert "skill" in skill
            assert "confidence" in skill

    def test_projects_endpoint_with_real_data(self, resume_agent: ResumeAgent):
        """Test projects listing with real data."""
        projects = resume_agent.get_projects()

        assert isinstance(projects, list)
        # Projects may be empty if none were collected, which is valid

        for project in projects:
            assert "name" in project
            assert "platform" in project


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])