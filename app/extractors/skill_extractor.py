"""Skill extraction from source code with confidence scoring."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


class EvidenceType(Enum):
    """Type of evidence for a skill."""
    SOURCE_CODE = "source_code"  # Direct usage in code
    DEPENDENCY = "dependency"  # Package dependency
    CONFIG = "config"  # Configuration file
    DEPLOYMENT = "deployment"  # Deployment configuration
    CONVERSATION = "conversation"  # Mentioned in conversation


# Confidence weights by evidence type
EVIDENCE_WEIGHTS = {
    EvidenceType.SOURCE_CODE: 1.0,
    EvidenceType.DEPENDENCY: 0.7,
    EvidenceType.CONFIG: 0.6,
    EvidenceType.DEPLOYMENT: 0.5,
    EvidenceType.CONVERSATION: 0.3,
}


@dataclass
class SkillEvidence:
    """Evidence for a skill extraction."""
    evidence_type: EvidenceType
    source_path: str
    evidence_text: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "evidence_type": self.evidence_type.value,
            "source_path": self.source_path,
            "evidence_text": self.evidence_text,
            "confidence": self.confidence,
        }


@dataclass
class ExtractedSkill:
    """Represents an extracted skill with metadata."""
    name: str
    category: str
    confidence: float = 1.0
    evidence: List[SkillEvidence] = field(default_factory=list)
    projects: Set[str] = field(default_factory=set)

    def add_evidence(self, evidence: SkillEvidence) -> None:
        """Add evidence and update confidence."""
        self.evidence.append(evidence)
        # Recalculate confidence as weighted average
        if self.evidence:
            total_weight = sum(e.confidence for e in self.evidence)
            self.confidence = min(1.0, total_weight / len(self.evidence))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "projects": list(self.projects),
        }


class SkillExtractor:
    """
    Extracts skills from source code, dependencies, and configurations.

    Skill Categories:
    - language: Programming languages (Python, JavaScript, etc.)
    - framework: Web frameworks (React, FastAPI, etc.)
    - library: Libraries and packages
    - tool: Development tools
    - cloud: Cloud platforms and services
    - database: Database technologies
    """

    # Language patterns
    LANGUAGE_PATTERNS = {
        "python": [
            r"def\s+\w+\s*\(",
            r"import\s+\w+",
            r"from\s+\w+\s+import",
            r"class\s+\w+\s*\(",
            r"async\s+def\s+\w+",
            r"await\s+\w+",
        ],
        "javascript": [
            r"const\s+\w+\s*=",
            r"function\s+\w+\s*\(",
            r"import\s+.*\s+from",
            r"export\s+default",
            r"module\.exports",
            r"require\(['\"]",
        ],
        "typescript": [
            r":\s*\w+\s*=>",
            r"interface\s+\w+",
            r"type\s+\w+\s*=",
            r"<\w+\s+extends",
        ],
        "rust": [
            r"fn\s+\w+\s*\(",
            r"let\s+mut\s+\w+",
            r"impl\s+\w+",
            r"struct\s+\w+",
        ],
        "go": [
            r"func\s+\w+\s*\(",
            r"var\s+\w+\s+",
            r"package\s+\w+",
        ],
    }

    # File extension to language mapping
    EXTENSION_LANGUAGE = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".go": "go",
        ".tsx": "typescript",
    }

    def __init__(self):
        self.skills: Dict[str, ExtractedSkill] = {}
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for efficiency."""
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            self._compiled_patterns[lang] = [
                re.compile(pattern, re.MULTILINE)
                for pattern in patterns
            ]

    def extract_from_file(self, file_path: str,
                          content: str) -> List[ExtractedSkill]:
        """
        Extract skills from a single file.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            List of extracted skills
        """
        skills = []
        path = Path(file_path)
        extension = path.suffix.lower()

        # Detect language from extension
        language = self.EXTENSION_LANGUAGE.get(extension)

        if language:
            # Extract language skill
            skills.extend(self._extract_language_skill(
                language, file_path, content))

            # Extract framework/library skills from imports
            skills.extend(self._extract_from_imports(
                content, file_path, language))

        # Extract from dependency files
        if path.name in ["package.json", "requirements.txt", "Cargo.toml",
                         "go.mod", "pyproject.toml"]:
            skills.extend(self._extract_from_dependencies(
                content, file_path))

        # Extract from config files
        if path.name in ["docker-compose.yml", "Dockerfile", ".gitlab-ci.yml",
                         "github-actions.yml", "vercel.json", "wrangler.toml"]:
            skills.extend(self._extract_from_config(
                content, file_path))

        return skills

    def _extract_language_skill(self, language: str, file_path: str,
                                 content: str) -> List[ExtractedSkill]:
        """Extract programming language skill."""
        skills = []

        # Check if content matches language patterns
        for pattern in self._compiled_patterns.get(language, []):
            if pattern.search(content):
                skill = self._get_or_create_skill(
                    language.capitalize(), "language")
                evidence = SkillEvidence(
                    evidence_type=EvidenceType.SOURCE_CODE,
                    source_path=file_path,
                    evidence_text=f"Detected {language} code pattern",
                    confidence=EVIDENCE_WEIGHTS[EvidenceType.SOURCE_CODE],
                )
                skill.add_evidence(evidence)
                skills.append(skill)
                break  # One evidence per language is enough

        return skills

    def _extract_from_imports(self, content: str, file_path: str,
                               language: str) -> List[ExtractedSkill]:
        """Extract skills from import statements."""
        skills = []

        # Python imports
        if language == "python":
            import_pattern = re.compile(
                r'^(?:import\s+(\w+)|from\s+(\w+)\s+import)',
                re.MULTILINE
            )
            for match in import_pattern.finditer(content):
                module = match.group(1) or match.group(2)
                if module:
                    skill = self._get_or_create_skill(module, "library")
                    evidence = SkillEvidence(
                        evidence_type=EvidenceType.SOURCE_CODE,
                        source_path=file_path,
                        evidence_text=f"Import: {module}",
                        confidence=EVIDENCE_WEIGHTS[EvidenceType.SOURCE_CODE],
                    )
                    skill.add_evidence(evidence)
                    skills.append(skill)

        # JavaScript/TypeScript imports
        elif language in ["javascript", "typescript"]:
            import_pattern = re.compile(
                r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                re.MULTILINE
            )
            for match in import_pattern.finditer(content):
                module = match.group(1).split('/')[0]
                if module and not module.startswith('.'):
                    skill = self._get_or_create_skill(module, "library")
                    evidence = SkillEvidence(
                        evidence_type=EvidenceType.SOURCE_CODE,
                        source_path=file_path,
                        evidence_text=f"Import: {module}",
                        confidence=EVIDENCE_WEIGHTS[EvidenceType.SOURCE_CODE],
                    )
                    skill.add_evidence(evidence)
                    skills.append(skill)

        return skills

    def _extract_from_dependencies(self, content: str,
                                    file_path: str) -> List[ExtractedSkill]:
        """Extract skills from dependency files."""
        skills = []
        path = Path(file_path)

        # requirements.txt
        if path.name == "requirements.txt":
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse package name (ignore version specifiers)
                    package = re.split(r'[=<>!~]', line)[0].strip()
                    if package:
                        skill = self._get_or_create_skill(package, "library")
                        evidence = SkillEvidence(
                            evidence_type=EvidenceType.DEPENDENCY,
                            source_path=file_path,
                            evidence_text=f"Dependency: {package}",
                            confidence=EVIDENCE_WEIGHTS[
                                EvidenceType.DEPENDENCY],
                        )
                        skill.add_evidence(evidence)
                        skills.append(skill)

        # package.json (simplified - just check for dependencies)
        elif path.name == "package.json":
            # Look for common frameworks
            framework_patterns = [
                (r'"react"', "React"),
                (r'"next"', "Next.js"),
                (r'"vue"', "Vue.js"),
                (r'"express"', "Express"),
                (r'"typescript"', "TypeScript"),
            ]
            for pattern, framework in framework_patterns:
                if re.search(pattern, content):
                    skill = self._get_or_create_skill(framework, "framework")
                    evidence = SkillEvidence(
                        evidence_type=EvidenceType.DEPENDENCY,
                        source_path=file_path,
                        evidence_text=f"Dependency: {framework}",
                        confidence=EVIDENCE_WEIGHTS[
                            EvidenceType.DEPENDENCY],
                    )
                    skill.add_evidence(evidence)
                    skills.append(skill)

        return skills

    def _extract_from_config(self, content: str,
                              file_path: str) -> List[ExtractedSkill]:
        """Extract skills from configuration files."""
        skills = []
        path = Path(file_path)

        # Docker
        if "docker" in path.name.lower():
            if "docker compose" in content.lower() or "FROM " in content:
                skill = self._get_or_create_skill("Docker", "tool")
                evidence = SkillEvidence(
                    evidence_type=EvidenceType.CONFIG,
                    source_path=file_path,
                    evidence_text="Docker configuration found",
                    confidence=EVIDENCE_WEIGHTS[EvidenceType.CONFIG],
                )
                skill.add_evidence(evidence)
                skills.append(skill)

        # Vercel
        if "vercel" in path.name.lower():
            skill = self._get_or_create_skill("Vercel", "cloud")
            evidence = SkillEvidence(
                evidence_type=EvidenceType.DEPLOYMENT,
                source_path=file_path,
                evidence_text="Vercel deployment config",
                confidence=EVIDENCE_WEIGHTS[EvidenceType.DEPLOYMENT],
            )
            skill.add_evidence(evidence)
            skills.append(skill)

        # Cloudflare
        if "wrangler" in path.name.lower() or "cloudflare" in path.name.lower():
            skill = self._get_or_create_skill("Cloudflare", "cloud")
            evidence = SkillEvidence(
                evidence_type=EvidenceType.DEPLOYMENT,
                source_path=file_path,
                evidence_text="Cloudflare configuration found",
                confidence=EVIDENCE_WEIGHTS[EvidenceType.DEPLOYMENT],
            )
            skill.add_evidence(evidence)
            skills.append(skill)

        return skills

    def _get_or_create_skill(self, name: str, category: str) -> ExtractedSkill:
        """Get existing skill or create new one."""
        key = f"{name}:{category}"
        if key not in self.skills:
            self.skills[key] = ExtractedSkill(name=name, category=category)
        return self.skills[key]

    def get_all_skills(self) -> List[ExtractedSkill]:
        """Return all extracted skills."""
        return list(self.skills.values())

    def get_skills_by_category(self) -> Dict[str, List[ExtractedSkill]]:
        """Group skills by category."""
        categorized: Dict[str, List[ExtractedSkill]] = {}
        for skill in self.skills.values():
            if skill.category not in categorized:
                categorized[skill.category] = []
            categorized[skill.category].append(skill)
        return categorized

    def clear(self) -> None:
        """Clear all extracted skills."""
        self.skills.clear()
