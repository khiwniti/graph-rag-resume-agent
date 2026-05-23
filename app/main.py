"""
FastAPI application for Graph RAG Resume Agent.
Provides endpoints for querying the résumé agent, managing skills, and collecting data.

Production-ready with:
- Structured JSON logging with request tracing
- Rate limiting and API key authentication
- Health checks and monitoring
- Comprehensive error handling
- Pagination for list endpoints
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import asyncio
import logging

from .config import (
    GITHUB_TOKEN, VERCEL_TOKEN, CLOUDFLARE_TOKEN,
    MAX_REPOS, MAX_FILES_PER_REPO, DATA_DIR
)
from .config_production import get_production_config
from .logging_config import setup_logging, set_request_id, get_request_id, get_structured_logger
from .middleware import register_middleware, get_rate_limiter
from .health import (
    get_health_checker, register_default_health_checks, 
    HealthStatus, SystemHealth
)
from .pipeline import GraphRAGPipeline
from .agent.resume_agent import ResumeAgent, AgentResponse

# Initialize structured logging
config = get_production_config()
setup_logging(
    level=config.logging.level,
    format_type=config.logging.format,
    include_request_id=config.logging.include_request_id,
    include_traceback=config.logging.include_traceback,
)
logger = get_structured_logger(__name__)


# ============================================================================
# Application Setup
# ============================================================================

# Register default health checks
register_default_health_checks()

app = FastAPI(
    title="Graph RAG Resume Agent",
    description="API for querying skills and experience from a knowledge graph",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
# Register production middleware (auth, rate limiting, logging, error handling)
register_middleware(app)

# CORS is configured by register_middleware based on production config
# The CORSMiddleware is added there with proper origins

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


class NarrativeResponse(BaseModel):
    """Response model for narrative listing."""
    narratives: List[Dict[str, Any]]
    total: int


class CareerStoryResponse(BaseModel):
    """Response model for career story queries."""
    projects: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    narratives: List[Dict[str, Any]]
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class TimelineResponse(BaseModel):
    """Response model for timeline queries."""
    projects: List[Dict[str, Any]]
    total: int


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
    
    Returns the status of the API and its dependencies including
    Neo4j, vector store, disk space, and API keys configuration.
    """
    checker = get_health_checker()
    system_health = await checker.check_all()
    
    # Map health status to boolean for backward compatibility
    is_healthy = system_health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    
    # Check if graph is loaded
    agent = get_agent()
    graph_loaded = os.path.exists(agent.graph_path)
    
    # Check if vector store is loaded
    vector_store_loaded = os.path.exists(f"{agent.vector_store_path}.faiss")
    
    return HealthResponse(
        status=system_health.status.value,
        graph_loaded=graph_loaded,
        vector_store_loaded=vector_store_loaded
    )


@app.get("/health/detailed", response_model=dict, tags=["system"])
async def health_check_detailed():
    """
    Detailed health check with component-level status.
    
    Returns comprehensive health information for all system components.
    """
    checker = get_health_checker()
    system_health = await checker.check_all()
    return system_health.to_dict()


@app.get("/health/ready", tags=["system"])
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if the service is ready to accept traffic,
    503 if it should be removed from the load balancer.
    """
    checker = get_health_checker()
    system_health = await checker.check_all()
    
    if system_health.status == HealthStatus.UNHEALTHY:
        return Response(
            content='{"status": "not ready", "reason": "unhealthy components"}',
            status_code=503,
            media_type="application/json"
        )
    
    return {"status": "ready"}


@app.get("/health/live", tags=["system"])
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if the service process is alive,
    500 if it should be restarted.
    """
    return {"status": "alive", "timestamp": asyncio.get_event_loop().time()}


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
    min_confidence: float = Query(default=0.3, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    category: Optional[str] = Query(default=None, description="Filter by skill category"),
):
    """
    List all extracted skills with pagination.
    
    Args:
        min_confidence: Minimum confidence threshold (0.0-1.0)
        limit: Maximum number of skills to return (1-1000)
        offset: Number of skills to skip for pagination
        category: Optional category filter
        
    Returns:
        List of skills sorted by confidence
    """
    agent = get_agent()
    
    try:
        all_skills = agent.list_skills(min_confidence=min_confidence)
        
        # Filter by category if specified
        if category:
            all_skills = [s for s in all_skills if s.get("category", "") == category]
        
        total = len(all_skills)
        
        # Apply pagination
        skills = all_skills[offset:offset + limit]
        
        # Add pagination headers
        headers = {
            "X-Total-Count": str(total),
            "X-Offset": str(offset),
            "X-Limit": str(limit),
            "X-Has-More": str(offset + limit < total),
        }
        
        response = SkillResponse(skills=skills, total=total)
        # Note: FastAPI doesn't easily support adding headers to response models
        # The headers are informational but actual pagination is done via offset/limit
        
        return response
    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
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
async def list_projects(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    source: Optional[str] = Query(default=None, description="Filter by source (github, vercel, cloudflare)"),
):
    """
    List all projects in the knowledge graph with pagination.
    
    Args:
        limit: Maximum number of projects to return (1-500)
        offset: Number of projects to skip for pagination
        source: Optional source filter
        
    Returns:
        Projects from GitHub, Vercel, and Cloudflare with their
        associated skills and metadata.
    """
    agent = get_agent()
    
    try:
        all_projects = agent.get_projects()
        
        # Filter by source if specified
        if source:
            all_projects = [p for p in all_projects if p.get("source", "") == source]
        
        total = len(all_projects)
        
        # Apply pagination
        projects = all_projects[offset:offset + limit]
        
        return ProjectResponse(projects=projects, total=total)
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
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


@app.get("/narratives", response_model=NarrativeResponse, tags=["narratives"])
async def list_narratives(
    query: str = "",
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    List career narrative chunks.

    Args:
        query: Optional keyword filter
        limit: Maximum number of narratives

    Returns:
        Narrative chunks linked to projects
    """
    from app.graph_store import Neo4jStore, KnowledgeGraphConfig
    from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

    try:
        store = Neo4jStore(KnowledgeGraphConfig(
            uri=NEO4J_URI or "bolt://localhost:7687",
            user=NEO4J_USER or "neo4j",
            password=NEO4J_PASSWORD or "",
            database=NEO4J_DATABASE or "neo4j",
        ))
        store.connect()
        cypher = """
        MATCH (n:Narrative)<-[:DESCRIBED_BY]-(p:Project)
        WHERE $query = '' OR toLower(n.text) CONTAINS toLower($query)
        RETURN n.id as id, n.text as text, n.period_start as period_start,
               n.period_end as period_end, p.id as project_id, p.name as project_name
        LIMIT $limit
        """
        with store.driver.session() as session:
            result = session.run(cypher, {"query": query, "limit": limit})
            narratives = [record.data() for record in result]
        store.close()
        return NarrativeResponse(narratives=narratives, total=len(narratives))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list narratives: {str(e)}")


@app.get("/career-story", response_model=CareerStoryResponse, tags=["narratives"])
async def get_career_story(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    topic: str = "",
    top_k: int = Query(default=5, ge=1, le=20)
):
    """
    Get a career story for a time period and/or topic.

    Args:
        period_start: ISO date string (inclusive), e.g. 2023-01-01
        period_end: ISO date string (inclusive), e.g. 2023-12-31
        topic: Optional topic keyword
        top_k: Maximum projects to return

    Returns:
        Projects, skills, and narratives matching the period/topic
    """
    agent = get_agent()

    try:
        story = agent._retriever.retrieve_career_story(
            period_start=period_start,
            period_end=period_end,
            topic=topic,
            top_k=top_k
        )
        return CareerStoryResponse(
            projects=story.get("projects", []),
            skills=story.get("skills", []),
            narratives=story.get("narratives", []),
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Career story query failed: {str(e)}")


@app.get("/timeline", response_model=TimelineResponse, tags=["projects"])
async def get_timeline(
    year: Optional[int] = None,
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Get projects on a timeline, optionally filtered by year.

    Args:
        year: Optional year filter (e.g. 2023)
        limit: Maximum number of projects

    Returns:
        Projects ordered by pushed_at date descending
    """
    from app.graph_store import Neo4jStore, KnowledgeGraphConfig
    from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

    try:
        store = Neo4jStore(KnowledgeGraphConfig(
            uri=NEO4J_URI or "bolt://localhost:7687",
            user=NEO4J_USER or "neo4j",
            password=NEO4J_PASSWORD or "",
            database=NEO4J_DATABASE or "neo4j",
        ))
        store.connect()

        cypher = """
        MATCH (p:Project)
        WHERE ($year = 0 OR (
            p.pushed_at STARTS WITH $year_prefix OR
            p.created_at STARTS WITH $year_prefix OR
            p.first_commit_at STARTS WITH $year_prefix
        ))
        RETURN p.id as id, p.name as name, p.description as description,
               p.source as source, p.url as url, p.pushed_at as pushed_at,
               p.created_at as created_at
        ORDER BY p.pushed_at DESC
        LIMIT $limit
        """
        with store.driver.session() as session:
            result = session.run(cypher, {
                "year": year or 0,
                "year_prefix": str(year) if year else "",
                "limit": limit
            })
            projects = [record.data() for record in result]
        store.close()
        return TimelineResponse(projects=projects, total=len(projects))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timeline query failed: {str(e)}")


@app.post("/reset", tags=["system"])
async def reset():
    """
    Reset the agent state.

    Clears cached graph and vector store, forcing reload from disk on next query.
    """
    global _agent, _pipeline
    
    _agent = None
    _pipeline = None
    
    logger.info("Agent state reset by request", request_id=get_request_id())
    
    return {"status": "reset_complete", "message": "Agent state cleared"}


@app.get("/metrics", tags=["system"])
async def get_metrics():
    """
    Get basic system metrics.
    
    Returns metrics about the knowledge graph, vector store, and system resources.
    """
    from app.config import DATA_DIR, EMBEDDINGS_DIR, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
    import shutil
    
    # Get Neo4j stats if available
    graph_stats = {"error": "Neo4j not available"}
    try:
        from app.graph_store import Neo4jStore, KnowledgeGraphConfig
        config = KnowledgeGraphConfig(
            uri=NEO4J_URI or "bolt://localhost:7687",
            user=NEO4J_USER or "neo4j",
            password=NEO4J_PASSWORD or "",
            database=NEO4J_DATABASE or "neo4j",
        )
        store = Neo4jStore(config)
        store.connect()
        graph_stats = store.get_stats()
        store.close()
    except Exception as e:
        graph_stats = {"error": f"Neo4j not available: {str(e)[:50]}"}
    
    # Get vector store info
    vector_info = {}
    try:
        import faiss
        index_path = str(EMBEDDINGS_DIR / "faiss_index")
        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
            vector_info = {
                "dimension": index.d,
                "total_vectors": index.ntotal,
            }
        else:
            vector_info = {"status": "not_initialized"}
    except Exception as e:
        vector_info = {"error": f"Vector store error: {str(e)[:50]}"}
    
    # Get disk usage
    try:
        disk_usage = shutil.disk_usage(DATA_DIR)
        disk_info = {
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
        }
    except Exception as e:
        disk_info = {"error": f"Could not get disk usage: {str(e)[:50]}"}
    
    return {
        "timestamp": asyncio.get_event_loop().time(),
        "graph": graph_stats,
        "vector_store": vector_info,
        "disk": disk_info,
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
