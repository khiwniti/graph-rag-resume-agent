"""Data Cleaner - Normalizes and sanitizes data before Neo4j ingestion.

Handles:
- Skill name normalization (case, duplicates)
- Framework name standardization
- Empty/null value sanitization
- Evidence serialization (SkillEvidence dataclass → dict)
- Cross-source deduplication hints
- Language name normalization
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalization maps
# ---------------------------------------------------------------------------

# Skill name overrides: raw lowercased key → canonical display name
SKILL_NAME_MAP: Dict[str, str] = {
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "python": "Python",
    "rust": "Rust",
    "golang": "Go",
    "go": "Go",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "react.js": "React",
    "reactjs": "React",
    "vue.js": "Vue.js",
    "vuejs": "Vue",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "nuxt.js": "Nuxt.js",
    "nuxtjs": "Nuxt",
    "express.js": "Express",
    "expressjs": "Express",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "gcp": "Google Cloud",
    "azure": "Azure",
    "github actions": "GitHub Actions",
    "github-actions": "GitHub Actions",
    "cloudflare workers": "Cloudflare Workers",
    "cloudflare pages": "Cloudflare Pages",
    "vercel": "Vercel",
    "tailwindcss": "Tailwind CSS",
    "tailwind": "Tailwind CSS",
    "graphql": "GraphQL",
    "rest": "REST",
    "rest api": "REST API",
    "restapi": "REST API",
}

# Framework name normalization
FRAMEWORK_MAP: Dict[str, str] = {
    "nextjs": "Next.js",
    "next": "Next.js",
    "nuxtjs": "Nuxt.js",
    "nuxt": "Nuxt",
    "react": "React",
    "vue": "Vue.js",
    "svelte": "Svelte",
    "sveltekit": "SvelteKit",
    "gatsby": "Gatsby",
    "remix": "Remix",
    "astro": "Astro",
    "angular": "Angular",
    "create-react-app": "Create React App",
    "vite": "Vite",
    "blitzjs": "Blitz.js",
    "redwoodjs": "RedwoodJS",
    "sanity": "Sanity",
    "storyblok": "Storyblok",
    "hydrogen": "Hydrogen",
}

# Language name normalization (GitHub API returns them already capitalized,
# but some edge cases slip through)
LANGUAGE_MAP: Dict[str, str] = {
    "c++": "C++",
    "c#": "C#",
    "f#": "F#",
    "objective-c": "Objective-C",
    "objective-c++": "Objective-C++",
    "jupyter notebook": "Jupyter Notebook",
}

# Category normalization
CATEGORY_MAP: Dict[str, str] = {
    "language": "language",
    "languages": "language",
    "framework": "framework",
    "frameworks": "framework",
    "library": "library",
    "libraries": "library",
    "tool": "tool",
    "tools": "tool",
    "cloud": "cloud",
    "platform": "platform",
    "database": "database",
    "runtime": "runtime",
}


@dataclass
class CleanedSkill:
    """A cleaned, normalized skill ready for Neo4j ingestion."""
    name: str
    category: str
    confidence: float
    evidence_count: int = 0
    evidence_summary: str = ""


@dataclass
class CleanedProject:
    """A cleaned, normalized project ready for Neo4j ingestion."""
    project_id: str
    name: str
    source: str
    url: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    skills: List[CleanedSkill] = field(default_factory=list)
    linked_project_ids: List[str] = field(default_factory=list)


class DataCleaner:
    """Normalizes and sanitizes raw collector data before Neo4j ingestion.

    Usage:
        cleaner = DataCleaner()
        cleaned = cleaner.clean_github_repo(raw_repo_data, github_user)
        # then pass cleaned.project_id, cleaned.skills etc. to Neo4j store
    """

    # ── public helpers ──────────────────────────────────────────────────

    @staticmethod
    def normalize_skill_name(raw: str) -> str:
        """Convert a raw skill name to its canonical form.

        >>> DataCleaner.normalize_skill_name('typescript')
        'TypeScript'
        >>> DataCleaner.normalize_skill_name('React')
        'React'
        """
        if not raw or not isinstance(raw, str):
            return ""
        key = raw.strip().lower()
        # Direct lookup
        if key in SKILL_NAME_MAP:
            return SKILL_NAME_MAP[key]
        # If already title-case or mixed case, try to keep it but check map
        # Handle hyphenated / slashed names
        if "-" in key or "/" in key:
            # Try replacing separators and look up again
            for sep in ["-", "/", "_"]:
                alt = key.replace(sep, " ")
                if alt in SKILL_NAME_MAP:
                    return SKILL_NAME_MAP[alt]
        return raw.strip()

    @staticmethod
    def normalize_language_name(raw: str) -> str:
        """Normalize a programming language name."""
        if not raw:
            return ""
        key = raw.strip().lower()
        if key in LANGUAGE_MAP:
            return LANGUAGE_MAP[key]
        # Also check skill name map for tools/frameworks mislabeled as languages
        if key in SKILL_NAME_MAP:
            return SKILL_NAME_MAP[key]
        # Most languages are already capitalized by GitHub API
        # Just handle remaining edge cases
        return raw.strip()

    @staticmethod
    def normalize_framework(raw: str) -> str:
        """Normalize a framework name from Vercel or other sources."""
        if not raw:
            return ""
        key = raw.strip().lower()
        if key in FRAMEWORK_MAP:
            return FRAMEWORK_MAP[key]
        return raw.strip()

    @staticmethod
    def normalize_category(raw: str) -> str:
        """Normalize a skill category string."""
        if not raw:
            return "tool"
        key = raw.strip().lower()
        return CATEGORY_MAP.get(key, key)

    @staticmethod
    def sanitize_string(value: Any, default: str = "") -> str:
        """Ensure value is a clean string, replacing None/empty with default."""
        if value is None:
            return default
        if not isinstance(value, str):
            return str(value)
        stripped = value.strip()
        return stripped if stripped else default

    @staticmethod
    def sanitize_url(url: Any) -> str:
        """Ensure url is a clean, non-empty string. Returns "" for None/empty."""
        if url is None or url == "":
            return ""
        return str(url).strip()

    @staticmethod
    def serialize_evidence(evidence_list: Any) -> List[Dict[str, Any]]:
        """Convert SkillEvidence dataclass objects or raw dicts to safe dicts.

        Neo4j can only store primitive types; this ensures all evidence
        items are plain dicts with string/int/float values.
        """
        serialized: List[Dict[str, Any]] = []
        if not evidence_list or not isinstance(evidence_list, list):
            return serialized

        for e in evidence_list:
            try:
                if hasattr(e, "to_dict"):
                    d = e.to_dict()
                elif isinstance(e, dict):
                    d = dict(e)
                else:
                    continue

                # Ensure all values are Neo4j-safe primitives
                safe: Dict[str, Any] = {}
                for k, v in d.items():
                    if isinstance(v, (str, int, float, bool, type(None))):
                        safe[k] = v
                    elif isinstance(v, (list, tuple)):
                        safe[k] = [str(x) if not isinstance(x, (str, int, float, bool, type(None))) else x for x in v]
                    else:
                        safe[k] = str(v)
                serialized.append(safe)
            except Exception as exc:
                logger.debug(f"Skipping non-serializable evidence item: {exc}")

        return serialized

    @staticmethod
    def build_evidence_summary(serialized_evidence: List[Dict[str, Any]],
                                fallback: str = "") -> str:
        """Build a concise evidence summary text from serialized evidence."""
        texts: List[str] = []
        for ev in serialized_evidence:
            text = (
                ev.get("evidence_text", "")
                or ev.get("text", "")
                or ev.get("source_path", "")
                or ev.get("source", "")
            )
            if text:
                texts.append(str(text)[:200])
        if texts:
            return " | ".join(texts[:5])
        return fallback

    # ── source-specific cleaners ────────────────────────────────────────

    def clean_github_repo(self, repo_data: Dict[str, Any]) -> CleanedProject:
        """Clean and normalize a single GitHub repo's data.

        Returns a CleanedProject with normalized skills, languages, and metadata.
        """
        raw_name = repo_data.get("name", "unknown")
        project_id = f"github:{raw_name}"

        # Normalize display name: use description if available, else repo name
        description = self.sanitize_string(repo_data.get("description"))
        display_name = description if description else raw_name

        # Build clean properties (only primitive types)
        props: Dict[str, Any] = {}
        for field in ["stars", "forks_count", "watchers_count", "open_issues_count"]:
            val = repo_data.get(field)
            if isinstance(val, (int, float)):
                props[field] = val

        primary_lang = self.sanitize_string(repo_data.get("language"))
        if primary_lang:
            props["language"] = self.normalize_language_name(primary_lang)

        for field in ["created_at", "pushed_at", "updated_at",
                       "first_commit_at", "last_commit_at"]:
            val = self.sanitize_string(repo_data.get(field))
            if val:
                props[field] = val

        # Languages → skills
        languages = repo_data.get("languages", {})
        if not isinstance(languages, dict):
            languages = {}
        if primary_lang:
            # Ensure primary language is in languages dict (match on lowercase keys)
            normalized_keys = {k.strip().lower(): k for k in languages}
            if primary_lang.lower() not in normalized_keys:
                languages[primary_lang] = 0

        cleaned_skills: List[CleanedSkill] = []

        # Add language skills
        for lang, _bytes in languages.items():
            norm_lang = self.normalize_language_name(lang)
            if not norm_lang:
                continue
            cleaned_skills.append(CleanedSkill(
                name=norm_lang,
                category="language",
                confidence=0.85,
                evidence_count=1,
                evidence_summary=f"GitHub repo: {raw_name}",
            ))

        # ── Add extracted skills (from deep analysis) ──────────────
        raw_extracted = repo_data.get("extracted_skills", [])
        seen_skill_names: Dict[str, int] = {}  # canonical_name → index in cleaned_skills

        for skill in raw_extracted:
            # Handle both ExtractedSkill objects and pre-serialized dicts
            if hasattr(skill, "to_dict"):
                skill_data = skill.to_dict()
            elif isinstance(skill, dict):
                skill_data = skill
            else:
                continue

            raw_skill_name = self.sanitize_string(skill_data.get("name"))
            if not raw_skill_name:
                continue

            canonical_name = self.normalize_skill_name(raw_skill_name)
            category = self.normalize_category(skill_data.get("category", "tool"))
            confidence = float(skill_data.get("confidence", 0.5))

            # Serialize evidence
            evidence_raw = skill_data.get("evidence", [])
            serialized = self.serialize_evidence(evidence_raw)
            evidence_count = len(serialized)
            evidence_summary = self.build_evidence_summary(
                serialized, f"Extracted from {raw_name}"
            )

            # Deduplicate by normalized name – keep highest confidence
            key = canonical_name.lower()
            if key in seen_skill_names:
                existing_idx = seen_skill_names[key]
                if confidence > cleaned_skills[existing_idx].confidence:
                    cleaned_skills[existing_idx] = CleanedSkill(
                        name=canonical_name,
                        category=category,
                        confidence=confidence,
                        evidence_count=evidence_count,
                        evidence_summary=evidence_summary,
                    )
                continue
            seen_skill_names[key] = len(cleaned_skills)

            cleaned_skills.append(CleanedSkill(
                name=canonical_name,
                category=category,
                confidence=confidence,
                evidence_count=evidence_count,
                evidence_summary=evidence_summary,
            ))

        return CleanedProject(
            project_id=project_id,
            name=display_name,
            source="github",
            url=self.sanitize_url(repo_data.get("url")),
            description=description,
            properties=props,
            skills=cleaned_skills,
        )

    def clean_vercel_project(self, project_data: Dict[str, Any]) -> CleanedProject:
        """Clean and normalize a single Vercel project's data."""
        raw_name = project_data.get("name", "unnamed-vercel-project")
        project_id = f"vercel:{raw_name}"

        framework_raw = project_data.get("framework")
        framework = self.normalize_framework(framework_raw) if framework_raw else ""

        desc_parts = ["Vercel project"]
        if framework:
            desc_parts.append(f"using {framework}")
        description = " - ".join(desc_parts)

        props: Dict[str, Any] = {}
        for field in ["created_at", "updated_at"]:
            val = self.sanitize_string(project_data.get(field))
            if val:
                props[field] = val
        if framework:
            props["framework"] = framework

        cleaned_skills: List[CleanedSkill] = []
        if framework:
            cleaned_skills.append(CleanedSkill(
                name=framework,
                category="framework",
                confidence=0.80,
                evidence_count=1,
                evidence_summary=f"Vercel project: {raw_name}",
            ))

        # If Vercel project is linked to a GitHub repo, note the link
        git_repo = project_data.get("git_repository")
        linked: List[str] = []
        if isinstance(git_repo, dict):
            repo_name = git_repo.get("repo") or git_repo.get("full_name") or ""
            if repo_name and "/" in repo_name:
                # Extract just the repo name
                linked.append(f"github:{repo_name.split('/')[-1]}")

        return CleanedProject(
            project_id=project_id,
            name=raw_name,
            source="vercel",
            url=self.sanitize_url(project_data.get("url")),
            description=description,
            properties=props,
            skills=cleaned_skills,
            linked_project_ids=linked,
        )

    def clean_cloudflare_worker(self, worker_data: Dict[str, Any]) -> CleanedProject:
        """Clean and normalize a Cloudflare Worker."""
        raw_name = worker_data.get("name", "unnamed-worker")
        project_id = f"cloudflare:worker:{raw_name}"

        props: Dict[str, Any] = {}
        for field in ["created_on", "modified_on", "created_at"]:
            val = self.sanitize_string(worker_data.get(field))
            if val:
                props[field] = val

        cleaned_skills = [
            CleanedSkill(
                name="Cloudflare Workers",
                category="platform",
                confidence=0.80,
                evidence_count=1,
                evidence_summary=f"Cloudflare Worker: {raw_name}",
            )
        ]

        return CleanedProject(
            project_id=project_id,
            name=raw_name,
            source="cloudflare",
            description="Cloudflare Worker",
            properties=props,
            skills=cleaned_skills,
        )

    def clean_cloudflare_page(self, page_data: Dict[str, Any]) -> CleanedProject:
        """Clean and normalize a Cloudflare Pages project."""
        raw_name = page_data.get("name", "unnamed-page")
        project_id = f"cloudflare:pages:{raw_name}"

        props: Dict[str, Any] = {}
        for field in ["created_at", "created_on"]:
            val = self.sanitize_string(page_data.get(field))
            if val:
                props[field] = val

        cleaned_skills = [
            CleanedSkill(
                name="Cloudflare Pages",
                category="platform",
                confidence=0.75,
                evidence_count=1,
                evidence_summary=f"Cloudflare Pages: {raw_name}",
            )
        ]

        return CleanedProject(
            project_id=project_id,
            name=raw_name,
            source="cloudflare",
            description="Cloudflare Pages project",
            properties=props,
            skills=cleaned_skills,
        )

    def clean_cloudflare_zone(self, zone_data: Dict[str, Any]) -> CleanedProject:
        """Clean and normalize a Cloudflare Zone as a project."""
        raw_name = zone_data.get("name", "unnamed-zone")
        project_id = f"cloudflare:zone:{raw_name}"

        props: Dict[str, Any] = {
            "status": self.sanitize_string(zone_data.get("status"), "active"),
        }
        for field in ["created_on", "modified_on"]:
            val = self.sanitize_string(zone_data.get(field))
            if val:
                props[field] = val

        cleaned_skills = [
            CleanedSkill(
                name="Cloudflare DNS",
                category="platform",
                confidence=0.70,
                evidence_count=1,
                evidence_summary=f"Cloudflare Zone: {raw_name}",
            )
        ]

        return CleanedProject(
            project_id=project_id,
            name=raw_name,
            source="cloudflare",
            description=f"Cloudflare Zone: {raw_name}",
            properties=props,
            skills=cleaned_skills,
        )

