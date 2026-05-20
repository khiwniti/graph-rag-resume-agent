#!/usr/bin/env python3
"""
MCP Server for Graph RAG Resume Agent

Exposes the knowledge graph and RAG retrieval as MCP tools
for AI agent orchestration in the MCP UI.

Usage:
    python -m app.mcp_server

Or deploy to MCP UI:
    npm run dev (in resume-mcp-ui directory)
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.query import GraphQuerier
from app.rag.retriever import Retriever
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore

try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️  mcp-use not installed. Install with: pip install mcp-use")

# Initialize FastMCP server
mcp = FastMCP(
    name="Graph RAG Resume Agent",
    instructions="Knowledge graph and RAG retrieval for AI-powered resume agent"
)

# Global instances
_graph_querier: Optional[GraphQuerier] = None
_retriever: Optional[Retriever] = None


def get_graph_querier() -> GraphQuerier:
    """Lazy-load the graph querier."""
    global _graph_querier
    if _graph_querier is None:
        _graph_querier = GraphQuerier()
    return _graph_querier


def get_retriever() -> Retriever:
    """Lazy-load the RAG retriever."""
    global _retriever
    if _retriever is None:
        embedder = Embedder()
        vector_store = VectorStore()
        _retriever = Retriever(embedder, vector_store)
    return _retriever


@mcp.tool()
def query_knowledge_graph(
    node_type: str = "all",
    query: Optional[str] = None
) -> dict:
    """
    Query the knowledge graph for nodes and edges.

    Args:
        node_type: Type of nodes to retrieve (person, skill, project, company, domain, tech, all)
        query: Optional text search query

    Returns:
        Dictionary with nodes, edges, and total count
    """
    querier = get_graph_querier()

    try:
        if node_type == "all":
            nodes = querier._cache.get("nodes", []) if querier._cache else []
        else:
            nodes = querier.get_nodes_by_type(node_type)

        # Filter by query if provided
        if query:
            query_lower = query.lower()
            nodes = [
                n for n in nodes
                if query_lower in n.get("label", "").lower()
                or query_lower in n.get("id", "").lower()
            ]

        # Get edges for filtered nodes
        node_ids = {n.get("id") for n in nodes}
        all_edges = querier._cache.get("edges", []) if querier._cache else []
        edges = [e for e in all_edges if e.get("from") in node_ids and e.get("to") in node_ids]

        return {
            "nodes": nodes,
            "edges": edges,
            "total": len(nodes)
        }
    except Exception as e:
        return {"error": str(e), "nodes": [], "edges": [], "total": 0}


@mcp.tool()
def get_skill_evidence(skill_name: str) -> dict:
    """
    Get evidence-backed details for a specific skill.

    Args:
        skill_name: Name of the skill to query

    Returns:
        Skill details with confidence score and evidence links
    """
    querier = get_graph_querier()

    try:
        skill = querier.get_skill(skill_name)
        if skill:
            return {
                "skill": skill.get("name"),
                "confidence": skill.get("confidence", 0),
                "category": skill.get("category", "general"),
                "evidence_count": skill.get("mention_count", 0),
                "evidence": skill.get("evidence", [])
            }
        return {"error": f"Skill not found: {skill_name}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_projects(
    domain: Optional[str] = None,
    min_confidence: float = 0.0
) -> dict:
    """
    List all projects with optional filtering.

    Args:
        domain: Optional domain filter (e.g., "geospatial", "analytics")
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        List of projects with metadata
    """
    querier = get_graph_querier()

    try:
        projects = querier.get_projects()

        # Filter by domain
        if domain:
            domain_lower = domain.lower()
            projects = [
                p for p in projects
                if domain_lower in str(p.get("domain", [])).lower()
                or domain_lower in p.get("name", "").lower()
            ]

        # Filter by confidence
        projects = [
            p for p in projects
            if p.get("confidence", 0) >= min_confidence
        ]

        return {
            "projects": projects,
            "total": len(projects)
        }
    except Exception as e:
        return {"error": str(e), "projects": [], "total": 0}


@mcp.tool()
def search_skills(
    query: str,
    top_k: int = 10,
    min_confidence: float = 0.0
) -> dict:
    """
    Search skills using RAG retrieval.

    Args:
        query: Search query
        top_k: Number of results to return
        min_confidence: Minimum confidence threshold

    Returns:
        Ranked list of skills with relevance scores
    """
    try:
        retriever = get_retriever()
        results = retriever.search(query, top_k=top_k)

        # Filter by confidence
        filtered = [
            r for r in results
            if r.get("confidence", 0) >= min_confidence
        ]

        return {
            "skills": filtered,
            "total": len(filtered),
            "query": query
        }
    except Exception as e:
        return {"error": str(e), "skills": [], "total": 0}


@mcp.tool()
def get_person_info() -> dict:
    """
    Get person node information from the knowledge graph.

    Returns:
        Person details including name, role, and contact info
    """
    querier = get_graph_querier()

    try:
        person_nodes = querier.get_nodes_by_type("person")
        if person_nodes:
            return person_nodes[0]
        return {"error": "No person node found"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_company_info(company_name: Optional[str] = None) -> dict:
    """
    Get company information from the knowledge graph.

    Args:
        company_name: Optional company name filter

    Returns:
        Company details or list of all companies
    """
    querier = get_graph_querier()

    try:
        if company_name:
            companies = querier.get_nodes_by_type("company")
            company = next(
                (c for c in companies if company_name.lower() in c.get("label", "").lower()),
                None
            )
            return company if company else {"error": f"Company not found: {company_name}"}
        else:
            return {"companies": querier.get_nodes_by_type("company")}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_health() -> dict:
    """
    Get system health status.

    Returns:
        Health check with component statuses
    """
    graph_path = Path("data/graph/knowledge_graph.json")
    vector_path = Path("data/embeddings/faiss_index.faiss")

    return {
        "status": "healthy" if graph_path.exists() else "degraded",
        "graph_loaded": graph_path.exists(),
        "vector_store_loaded": vector_path.exists(),
        "mcp_server": "running"
    }


# CLI entry point
if __name__ == "__main__":
    if not MCP_AVAILABLE:
        print("❌ mcp-use not installed. Install with: pip install mcp-use")
        sys.exit(1)

    print("🚀 Starting Graph RAG MCP Server...")
    print(f"   Graph path: data/graph/knowledge_graph.json")
    print(f"   Vector path: data/embeddings/faiss_index.faiss")
    print("")
    print("   Tools available:")
    print("   - query_knowledge_graph")
    print("   - get_skill_evidence")
    print("   - list_projects")
    print("   - search_skills")
    print("   - get_person_info")
    print("   - get_company_info")
    print("   - get_health")
    print("")

    # Run the MCP server
    mcp.run()
