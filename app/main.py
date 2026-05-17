"""
FastAPI application for Graph RAG Resume Agent.
Provides endpoints for querying the résumé agent, managing skills, and collecting data.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import asyncio

from .config import (
    GITHUB_TOKEN, VERCEL_TOKEN, CLOUDFLARE_TOKEN,
    MAX_REPOS, MAX_FILES_PER_REPO, DATA_DIR
)
from .pipeline import GraphRAGPipeline
from .agent.resume_agent import ResumeAgent, AgentResponse


# ============================================================================
# Application Setup
# ============================================================================

app = FastAPI(
    title="Graph RAG Resume Agent",
    description="API for querying skills and experience from a knowledge graph",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
_pipeline: Optional[GraphRAGPipeline] = None
_agent: Optional[ResumeAgent] = None


def get_pipeline() -> GraphRAGPipeline:
    """Get or create the collection pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = GraphRAGPipeline()
    return _pipeline


def get_agent() -> ResumeAgent:
    """Get or create the résumé agent."""
    global _agent
    if _agent is None:
        _agent = ResumeAgent()
    return _agent


# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for querying the agent."""
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    """Response model for agent queries."""
    answer: str
    skills: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    sources: List[str]
    confidence: float


class CollectRequest(BaseModel):
    """Request model for data collection."""
    sources: Optional[List[str]] = None
    max_repos: Optional[int] = None
    max_files_per_repo: Optional[int] = None


class CollectResponse(BaseModel):
    """Response model for data collection."""
    status: str
    repositories: int
    files: int
    skills_extracted: int
    graph_nodes: int
    graph_edges: int


class SkillResponse(BaseModel):
    """Response model for skill listing."""
    skills: List[Dict[str, Any]]
    total: int


class ProjectResponse(BaseModel):
    """Response model for project listing."""
    projects: List[Dict[str, Any]]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    graph_loaded: bool
    vector_store_loaded: bool


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Graph RAG Resume Agent API",
        "version": "1.0.0",
        "description": "Query your skills and experience from a knowledge graph",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "collect": "/collect",
            "query": "/query",
            "skills": "/skills",
            "projects": "/projects",
            "skill_evidence": "/skills/{skill}/evidence"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the status of the API and its dependencies.
    """
    agent = get_agent()
    
    # Check if graph is loaded
    graph_loaded = os.path.exists(agent.graph_path)
    
    # Check if vector store is loaded
    vector_store_loaded = os.path.exists(f"{agent.vector_store_path}.faiss")
    
    return HealthResponse(
        status="healthy",
        graph_loaded=graph_loaded,
        vector_store_loaded=vector_store_loaded
    )


@app.post("/collect", response_model=CollectResponse, tags=["data"])
async def collect_data(request: CollectRequest = None):
    """
    Collect data from configured sources (GitHub, Vercel, Cloudflare).
    
    This triggers the full collection pipeline:
    1. Fetch data from sources
    2. Normalize and extract skills
    3. Build knowledge graph
    4. Create vector embeddings
    
    **Note:** This is an asynchronous operation. Use the status endpoint to check progress.
    """
    pipeline = get_pipeline()
    
    # Configure limits if provided
    if request:
        if request.max_repos:
            # Note: Config constants are module-level, can't be changed dynamically
            pass
        if request.max_files_per_repo:
            pass
    
    try:
        # Run collection
        result = await pipeline.run()
        
        return CollectResponse(
            status="completed",
            repositories=result.get("repositories", 0),
            files=result.get("files", 0),
            skills_extracted=result.get("skills", 0),
            graph_nodes=result.get("graph_nodes", 0),
            graph_edges=result.get("graph_edges", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["query"])
async def query_agent(request: QueryRequest):
    """
    Query the résumé agent with a question.
    
    Example questions:
    - "What are my Python skills?"
    - "Which projects use React?"
    - "What cloud technologies have I used?"
    - "Show me my backend development experience"
    
    The agent will search the knowledge graph and vector store to provide
    an evidence-based answer.
    """
    agent = get_agent()
    
    try:
        response = agent.query(
            question=request.question,
            top_k=request.top_k
        )
        
        return QueryResponse(
            answer=response.answer,
            skills=response.skills,
            evidence=response.evidence,
            sources=response.sources,
            confidence=response.confidence
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/skills", response_model=SkillResponse, tags=["skills"])
async def list_skills(
    min_confidence: float = Query(default=0.3, ge=0.0, le=1.0)
):
    """
    List all extracted skills.
    
    Args:
        min_confidence: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        List of skills sorted by confidence
    """
    agent = get_agent()
    
    try:
        skills = agent.list_skills(min_confidence=min_confidence)
        return SkillResponse(skills=skills, total=len(skills))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list skills: {str(e)}")


@app.get("/skills/{skill_name}/evidence", tags=["skills"])
async def get_skill_evidence(skill_name: str):
    """
    Get evidence for a specific skill.
    
    Returns all evidence items that support the presence of this skill,
    including source files, projects, and confidence scores.
    """
    agent = get_agent()
    
    try:
        evidence = agent.get_skill_evidence(skill_name)
        return {
            "skill": skill_name,
            "evidence": evidence,
            "count": len(evidence)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get evidence: {str(e)}")


@app.get("/projects", response_model=ProjectResponse, tags=["projects"])
async def list_projects():
    """
    List all projects in the knowledge graph.
    
    Returns projects from GitHub, Vercel, and Cloudflare with their
    associated skills and metadata.
    """
    agent = get_agent()
    
    try:
        projects = agent.get_projects()
        return ProjectResponse(projects=projects, total=len(projects))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@app.get("/skills/search", response_model=SkillResponse, tags=["skills"])
async def search_skills(q: str, limit: int = 10):
    """
    Search for skills by name.
    
    Args:
        q: Search query (substring match)
        limit: Maximum number of results
        
    Returns:
        Matching skills
    """
    agent = get_agent()
    
    try:
        all_skills = agent.list_skills(min_confidence=0.0)
        query_lower = q.lower()
        
        # Filter by substring match
        matching = [
            skill for skill in all_skills
            if query_lower in skill["skill"].lower()
        ][:limit]
        
        return SkillResponse(skills=matching, total=len(matching))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/reset", tags=["system"])
async def reset():
    """
    Reset the agent state.
    
    Clears cached graph and vector store, forcing reload from disk on next query.
    """
    global _agent, _pipeline
    
    _agent = None
    _pipeline = None
    
    return {"status": "reset_complete", "message": "Agent state cleared"}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
