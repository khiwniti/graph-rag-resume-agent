"""Deep code analysis, skill extraction, and knowledge graph enrichment.

GitNexus/Graphify-style extraction layer:
- SkillExtractor: Surface-level skills from imports, config files
- DependencyParser: Package dependencies from manifest files
- SourceAnalyzer: Code statistics and technology detection
- CodeStructureExtractor: Functions, classes, modules as graph nodes with relationships
- CrossFileLinker: File-level import/dependency maps
- ArchitectureDetector: MVC, REST, microservice, monorepo pattern detection
- DeploymentAnalyzer: Deep Vercel/Cloudflare config, env vars, routes, domains
- DocCodeLinker: README section → source file linking
- NarrativeBuilder: LLM-powered career story generation per project
"""
from .skill_extractor import SkillExtractor, SkillEvidence
from .dependency_parser import DependencyParser
from .source_analyzer import SourceAnalyzer
from .narrative_builder import NarrativeBuilder, ProjectNarrative
from .code_structure import CodeStructureExtractor, CodeStructure, CodeEntity, CodeRelationship, entity_id
from .cross_file_linker import CrossFileLinker, CrossFileMap, FileImport, file_id
from .architecture_detector import ArchitectureDetector, ArchitectureAnalysis, ArchitecturePattern
from .deployment_analyzer import DeploymentAnalyzer, DeploymentAnalysis, DeploymentRoute, DeploymentConfig, DeploymentDomain, config_id, route_id
from .doc_code_linker import DocCodeLinker, DocCodeMap, ReadmeSection, DocLink, narrative_id_from_section

__all__ = [
    "SkillExtractor", "SkillEvidence",
    "DependencyParser",
    "SourceAnalyzer",
    "NarrativeBuilder", "ProjectNarrative",
    "CodeStructureExtractor", "CodeStructure", "CodeEntity", "CodeRelationship", "entity_id",
    "CrossFileLinker", "CrossFileMap", "FileImport", "file_id",
    "ArchitectureDetector", "ArchitectureAnalysis", "ArchitecturePattern",
    "DeploymentAnalyzer", "DeploymentAnalysis", "DeploymentRoute", "DeploymentConfig", "DeploymentDomain",
    "config_id", "route_id",
    "DocCodeLinker", "DocCodeMap", "ReadmeSection", "DocLink", "narrative_id_from_section",
]
