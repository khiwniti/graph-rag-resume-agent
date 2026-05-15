"""Pydantic models for the Graph RAG Resume Agent."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PersonProfile(BaseModel):
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


class DependencyInfo(BaseModel):
    name: str
    version: str = ""
    is_dev: bool = False
    category: str = ""  # framework, ui, database, ai, testing, tooling, etc.


class CodebaseAnalysis(BaseModel):
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


class GraphNode(BaseModel):
    id: str
    type: str  # person, project, skill, technology, organization, deployment, domain
    properties: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # BUILT, USES, DEPLOYED_ON, CONTRIBUTED_TO, MEMBER_OF, etc.
    properties: dict = Field(default_factory=dict)


class SkillEvidence(BaseModel):
    skill_name: str
    category: str  # language, framework, tool, platform, pattern, database
    evidence_type: str  # dependency_usage, code_presence, deployment_config, file_structure
    source_repo: str = ""
    source_deployment: str = ""
    details: str = ""
    proficiency_indicator: str = ""  # expert, advanced, intermediate, beginner
    frequency: int = 1


class QueryRequest(BaseModel):
    question: str
    max_context_items: int = 10


class QueryResponse(BaseModel):
    answer: str
    graph_context: list = Field(default_factory=list)
    vector_context: list = Field(default_factory=list)
    skills_found: list = Field(default_factory=list)
    confidence: float = 0.0