"""Pydantic models for the Graph RAG Resume Agent."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# Person Profile
# =============================================================================
class PersonProfile(BaseModel):
    """User's profile information aggregated from all sources."""
    login: str = ""
    name: str = ""
    email: str = ""
    bio: str = ""
    company: str = ""
    location: str = ""
    blog: str = ""
    hireable: bool = False
    public_repos: int = 0
    total_private_repos: int = 0
    followers: int = 0
    following: int = 0
    created_at: str = ""
    github_url: str = ""
    vercel_username: str = ""
    cloudflare_account: str = ""


# =============================================================================
# Technology / Dependency Models
# =============================================================================
class DependencyInfo(BaseModel):
    """Information about a dependency or technology."""
    name: str
    version: str = ""
    is_dev: bool = False
    category: str = ""  # framework, ui, database, ai, testing, tooling, etc.


class CodebaseAnalysis(BaseModel):
    """Analysis of a codebase's technology stack."""
    repo_name: str = ""
    languages: dict = Field(default_factory=dict)
    language_bytes: dict = Field(default_factory=dict)
    total_bytes: int = 0
    dependencies: list = Field(default_factory=list)
    dev_dependencies: list = Field(default_factory=list)
    frameworks: list = Field(default_factory=list)
    databases: list = Field(default_factory=list)
    ai_tools: list = Field(default_factory=list)
    ui_libraries: list = Field(default_factory=list)
    testing_tools: list = Field(default_factory=list)
    deployment_targets: list = Field(default_factory=list)
    architecture_patterns: list = Field(default_factory=list)
    file_structure: list = Field(default_factory=list)
    key_files: dict = Field(default_factory=dict)
    readme_content: str = ""
    description: str = ""


# =============================================================================
# Graph Node/Edge Models
# =============================================================================
class GraphNode(BaseModel):
    """A node in the knowledge graph."""
    id: str
    type: str  # person, project, skill, technology, organization, deployment, domain
    properties: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""
    source: str
    target: str
    type: str  # BUILT, USES, DEPLOYED_ON, CONTRIBUTED_TO, MEMBER_OF, etc.
    properties: dict = Field(default_factory=dict)


# =============================================================================
# Skill Evidence Models
# =============================================================================
class SkillEvidence(BaseModel):
    """Evidence for a skill derived from code, configs, or deployments."""
    skill_name: str
    category: str  # language, framework, tool, platform, pattern, database
    evidence_type: str  # dependency_usage, code_presence, deployment_config, file_structure
    source_repo: str = ""
    source_deployment: str = ""
    details: str = ""
    proficiency_indicator: str = ""  # expert, advanced, intermediate, beginner
    frequency: int = 1


# =============================================================================
# Query/Response Models
# =============================================================================
class QueryRequest(BaseModel):
    """Request to query the résumé agent."""
    question: str
    max_context_items: int = 10


class QueryResponse(BaseModel):
    """Response from the résumé agent."""
    answer: str
    graph_context: list = Field(default_factory=list)
    vector_context: list = Field(default_factory=list)
    skills_found: list = Field(default_factory=list)
    confidence: float = 0.0


# =============================================================================
# Evidence Models (NEW for evidence-driven approach)
# =============================================================================
class SourceFileEvidence(BaseModel):
    """Evidence from a source file."""
    file_path: str
    repo_name: str = ""
    project_name: str = ""
    source_system: str  # github, vercel, cloudflare, conversation
    file_type: str  # dependency, config, source, documentation
    content_preview: str = ""
    content_hash: str = ""
    detected_concepts: List[str] = Field(default_factory=list)
    timestamp: str = ""


class RepositorySnapshot(BaseModel):
    """Snapshot of a repository's state."""
    repo_name: str
    full_name: str
    owner: str
    url: str
    description: str = ""
    is_private: bool = False
    is_fork: bool = False
    default_branch: str = ""
    created_at: str = ""
    updated_at: str = ""
    pushed_at: str = ""
    stars: int = 0
    forks: int = 0
    topics: List[str] = Field(default_factory=list)
    languages: Dict[str, int] = Field(default_factory=dict)
    file_count: int = 0
    file_paths: List[str] = Field(default_factory=list)
    dependency_files: Dict[str, str] = Field(default_factory=dict)
    key_source_files: Dict[str, str] = Field(default_factory=dict)
    recent_commits: List[Dict[str, Any]] = Field(default_factory=list)
    source_system: str = "github"


class ProjectSnapshot(BaseModel):
    """Snapshot of a Vercel project."""
    project_name: str
    project_id: str
    framework: str = ""
    build_settings: Dict[str, Any] = Field(default_factory=dict)
    git_repo: str = ""
    env_var_keys: List[str] = Field(default_factory=list)
    deployments: List[Dict[str, Any]] = Field(default_factory=list)
    domains: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    source_system: str = "vercel"


class DeploymentSnapshot(BaseModel):
    """Snapshot of a deployment."""
    deployment_id: str
    project_name: str = ""
    repo_name: str = ""
    url: str = ""
    state: str = ""
    branch: str = ""
    created_at: str = ""
    ready_at: str = ""
    source_system: str  # vercel, cloudflare


class ConversationArtifact(BaseModel):
    """Evidence from conversation artifacts."""
    artifact_id: str
    artifact_type: str  # user_message, agent_action, file_creation, task
    content: str
    timestamp: str = ""
    source_path: str = ""
    related_repos: List[str] = Field(default_factory=list)
    related_technologies: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class CloudflareResource(BaseModel):
    """Cloudflare infrastructure resource."""
    resource_type: str  # worker, pages, kv, d1, r2, durable_object, queue, zone
    resource_id: str
    resource_name: str = ""
    bindings: List[Dict[str, Any]] = Field(default_factory=list)
    source_code_preview: str = ""
    detected_patterns: List[str] = Field(default_factory=list)
    created_at: str = ""
    modified_at: str = ""


class SkillEvidenceRanked(BaseModel):
    """Skill evidence with ranking and provenance."""
    skill_name: str
    category: str
    proficiency_indicator: str  # expert, advanced, intermediate, beginner
    confidence: float
    frequency: int
    evidence_sources: List[str] = Field(default_factory=list)  # repo names, project names
    evidence_types: List[str] = Field(default_factory=list)  # dependency, source, config, deployment
    first_seen: str = ""
    last_seen: str = ""


class GraphDocument(BaseModel):
    """Complete graph document for serialization."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
