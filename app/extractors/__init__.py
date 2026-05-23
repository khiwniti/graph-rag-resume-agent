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
import logging
_log = logging.getLogger(__name__)

# ── Each import is wrapped so one failing module doesn't break the entire package.
#     This matters on Kaggle/Colab where dotenv or NVIDIA SDK may be unavailable.

_IMPORT_ERRORS = []

try:
    from .skill_extractor import SkillExtractor, SkillEvidence
except Exception as e:
    SkillExtractor = SkillEvidence = None  # type: ignore
    _IMPORT_ERRORS.append(f"skill_extractor: {e}")

try:
    from .dependency_parser import DependencyParser
except Exception as e:
    DependencyParser = None  # type: ignore
    _IMPORT_ERRORS.append(f"dependency_parser: {e}")

try:
    from .source_analyzer import SourceAnalyzer
except Exception as e:
    SourceAnalyzer = None  # type: ignore
    _IMPORT_ERRORS.append(f"source_analyzer: {e}")

try:
    from .narrative_builder import NarrativeBuilder, ProjectNarrative
except Exception as e:
    NarrativeBuilder = ProjectNarrative = None  # type: ignore
    _IMPORT_ERRORS.append(f"narrative_builder: {e}")

try:
    from .code_structure import CodeStructureExtractor, CodeStructure, CodeEntity, CodeRelationship, entity_id
except Exception as e:
    CodeStructureExtractor = CodeStructure = CodeEntity = CodeRelationship = entity_id = None  # type: ignore
    _IMPORT_ERRORS.append(f"code_structure: {e}")

try:
    from .cross_file_linker import CrossFileLinker, CrossFileMap, FileImport, file_id
except Exception as e:
    CrossFileLinker = CrossFileMap = FileImport = file_id = None  # type: ignore
    _IMPORT_ERRORS.append(f"cross_file_linker: {e}")

try:
    from .architecture_detector import ArchitectureDetector, ArchitectureAnalysis, ArchitecturePattern
except Exception as e:
    ArchitectureDetector = ArchitectureAnalysis = ArchitecturePattern = None  # type: ignore
    _IMPORT_ERRORS.append(f"architecture_detector: {e}")

try:
    from .deployment_analyzer import DeploymentAnalyzer, DeploymentAnalysis, DeploymentRoute, DeploymentConfig, DeploymentDomain, config_id, route_id
except Exception as e:
    DeploymentAnalyzer = DeploymentAnalysis = DeploymentRoute = DeploymentConfig = DeploymentDomain = config_id = route_id = None  # type: ignore
    _IMPORT_ERRORS.append(f"deployment_analyzer: {e}")

try:
    from .doc_code_linker import DocCodeLinker, DocCodeMap, ReadmeSection, DocLink, narrative_id_from_section
except Exception as e:
    DocCodeLinker = DocCodeMap = ReadmeSection = DocLink = narrative_id_from_section = None  # type: ignore
    _IMPORT_ERRORS.append(f"doc_code_linker: {e}")

if _IMPORT_ERRORS:
    _log.warning("Some extractors failed to load (non-fatal): %s", "; ".join(_IMPORT_ERRORS), exc_info=True)

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
