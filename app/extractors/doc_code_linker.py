"""Doc-Code Linker - Links README sections to actual source files.

Parses README content into sections (by ## headings), then attempts to
match each section to relevant source files by keyword matching. Creates
DOCUMENTED_BY relationships in the knowledge graph connecting File nodes
to Narrative nodes (README sections).

This enables queries like: "Show me the code that implements the auth system
described in the README" and powers evidence-backed RAG responses.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ReadmeSection:
    """A parsed section from a README file."""
    heading: str
    level: int  # 1 for #, 2 for ##, etc.
    content: str
    keywords: Set[str] = field(default_factory=set)


@dataclass
class DocLink:
    """A link from a README section to a source file."""
    section_heading: str
    file_path: str
    match_type: str  # "exact", "keyword", "fuzzy_path"
    confidence: float


@dataclass
class DocCodeMap:
    """Complete documentation-to-code mapping for a project."""
    sections: List[ReadmeSection] = field(default_factory=list)
    links: List[DocLink] = field(default_factory=list)
    project_id: str = ""


class DocCodeLinker:
    """Links README documentation sections to actual source code files.

    Usage:
        linker = DocCodeLinker()
        doc_map = linker.analyze(readme_content, repo_path)
        # Then create Narrative nodes for each section and DOCUMENTED_BY
        # relationships to matched File nodes.
    """

    # ── README Parsing ──────────────────────────────────────────────────

    HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    @classmethod
    def parse_readme(cls, content: str) -> List[ReadmeSection]:
        """Parse a README into sections by heading level."""
        if not content:
            return []

        sections: List[ReadmeSection] = []
        matches = list(cls.HEADING_RE.finditer(content))

        for i, match in enumerate(matches):
            level = len(match.group(1))
            heading = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end].strip()

            # Extract keywords from heading + content
            keywords = cls._extract_keywords(heading, section_content)

            sections.append(ReadmeSection(
                heading=heading,
                level=level,
                content=section_content,
                keywords=keywords,
            ))

        return sections

    @staticmethod
    def _extract_keywords(heading: str, content: str) -> Set[str]:
        """Extract relevant keywords from a section."""
        keywords: Set[str] = set()

        # Split heading into words, collect significant ones
        heading_words = re.findall(r'\b[a-zA-Z_][\w\.-]*\b', heading.lower())
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "from", "by", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "shall", "you", "your",
            "this", "that", "these", "those", "it", "its", "how", "what", "which",
            "who", "whom", "where", "when", "why", "not", "no", "nor", "so",
            "if", "then", "than", "too", "very", "just", "also", "only", "all",
            "both", "each", "every", "other", "some", "such", "about", "over",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "up", "down", "out", "off", "here", "there",
        }

        for word in heading_words:
            if word not in stopwords and len(word) > 2:
                keywords.add(word)

        # Extract important terms from content (first 500 chars)
        content_words = re.findall(r'\b[a-zA-Z_][\w\.-]*\b', content[:500].lower())
        word_freq: Dict[str, int] = {}
        for word in content_words:
            if word not in stopwords and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Add top frequent content words
        for word, freq in sorted(word_freq.items(), key=lambda x: -x[1])[:10]:
            if freq >= 2:
                keywords.add(word)

        return keywords

    # ── File Matching ───────────────────────────────────────────────────

    @classmethod
    def match_section_to_files(cls, section: ReadmeSection,
                                repo_path: str) -> List[DocLink]:
        """Match a README section to relevant source files in the repo.

        Matching strategies (in priority order):
        1. Exact path mention: if a file path appears verbatim in the heading/content
        2. File name keyword match: section keywords match file names
        3. Directory keyword match: section keywords match directory names
        """
        links: List[DocLink] = []
        repo = Path(repo_path)

        # Strategy 1: Exact path mentions
        exact_matches = cls._find_exact_paths(section, repo)
        for file_path in exact_matches:
            links.append(DocLink(
                section_heading=section.heading,
                file_path=file_path,
                match_type="exact",
                confidence=1.0,
            ))

        if not links:
            # Strategy 2 & 3: Keyword matching
            keyword_links = cls._find_keyword_matches(section, repo)
            links.extend(keyword_links)

        return links

    @classmethod
    def _find_exact_paths(cls, section: ReadmeSection, repo: Path) -> List[str]:
        """Find file paths explicitly mentioned in the README section."""
        found: List[str] = []
        text = f"{section.heading} {section.content}"

        # Match patterns like "src/app.py", "./utils/helper.ts", "app/main.py"
        path_pattern = re.compile(r'(?:[\'\"]|`|\s)(\.?/?(?:[\w.-]+/)*[\w.-]+\.\w{1,5})(?:[\'\"]|`|\s|$)', re.I)

        for match in path_pattern.finditer(text):
            candidate = match.group(1).strip("'\"`").lstrip("./")
            full_path = repo / candidate
            if full_path.exists() and full_path.is_file():
                found.append(str(full_path))

        return found

    @classmethod
    def _find_keyword_matches(cls, section: ReadmeSection, repo: Path) -> List[DocLink]:
        """Find files that match section keywords in their names."""
        links: List[DocLink] = []
        source_exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
                       ".rb", ".java", ".cpp", ".h", ".yaml", ".yml", ".json",
                       ".toml", ".md", ".css", ".html"}

        for file_path in repo.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in source_exts:
                continue
            if "node_modules" in str(file_path).split("/"):
                continue
            if "__pycache__" in str(file_path).split("/"):
                continue

            file_name_lower = file_path.name.lower()
            dir_name_lower = file_path.parent.name.lower() if file_path.parent != repo else ""

            score = 0
            matched_keywords: List[str] = []

            # Check file name match
            for keyword in section.keywords:
                # Exact word match in file name
                if re.search(rf'\b{re.escape(keyword)}\b', file_name_lower.replace("-", " ").replace("_", " ")):
                    score += 3
                    matched_keywords.append(keyword)
                # Partial match
                elif keyword in file_name_lower:
                    score += 1
                    matched_keywords.append(keyword)
                # Match in directory name
                elif dir_name_lower and keyword in dir_name_lower:
                    score += 2
                    matched_keywords.append(keyword)

            if score >= 3:
                links.append(DocLink(
                    section_heading=section.heading,
                    file_path=str(file_path),
                    match_type="keyword",
                    confidence=min(1.0, score / 10.0),
                ))

        # Sort by confidence, keep top 5
        links.sort(key=lambda x: -x.confidence)
        return links[:5]

    # ── Main Analysis ───────────────────────────────────────────────────

    @classmethod
    def analyze(cls, readme_content: str, repo_path: str,
                project_id: str = "") -> DocCodeMap:
        """Analyze a README and link sections to source code files.

        Args:
            readme_content: The README text content
            repo_path: Path to the cloned repository root
            project_id: Optional project identifier

        Returns:
            DocCodeMap with parsed sections and file links
        """
        result = DocCodeMap(project_id=project_id)

        # Parse sections
        result.sections = cls.parse_readme(readme_content)

        # Match each section to files
        for section in result.sections:
            try:
                section_links = cls.match_section_to_files(section, repo_path)
                result.links.extend(section_links)
            except Exception as e:
                logger.debug(f"Doc-code linking failed for section '{section.heading}': {e}")

        return result


def narrative_id_from_section(project_id: str, heading: str, index: int) -> str:
    """Generate a Narrative node ID for a README section."""
    safe_heading = re.sub(r'[^a-zA-Z0-9_-]', '_', heading.lower())[:50]
    return f"doc:{project_id}:{index}:{safe_heading}"
