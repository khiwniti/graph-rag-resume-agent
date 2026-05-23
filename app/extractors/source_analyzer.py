"""Source code analyzer for skill extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class SourceAnalysis:
    """Result of analyzing a source file."""
    file_path: str
    language: str
    size_bytes: int
    line_count: int
    imports: List[str] = field(default_factory=list)
    function_count: int = 0
    class_count: int = 0
    technologies: Set[str] = field(default_factory=set)


class SourceAnalyzer:
    """
    Analyzes source code files to extract technical information.

    Extracts:
    - Programming language
    - Imports/dependencies
    - Code structure (functions, classes)
    - Technology usage patterns
    """

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": {
            "extensions": [".py"],
            "patterns": [
                r"^import\s+\w+",
                r"^from\s+\w+\s+import",
                r"^\s*def\s+\w+\s*\(",
                r"^\s*class\s+\w+",
                r"^\s*async\s+def",
            ]
        },
        "javascript": {
            "extensions": [".js", ".jsx", ".mjs"],
            "patterns": [
                r"import\s+.*\s+from",
                r"export\s+default",
                r"const\s+\w+\s*=\s*require",
                r"module\.exports",
            ]
        },
        "typescript": {
            "extensions": [".ts", ".tsx"],
            "patterns": [
                r"import\s+.*\s+from",
                r"interface\s+\w+",
                r"type\s+\w+\s*=",
                r":\s*\w+\s*=>",
            ]
        },
        "rust": {
            "extensions": [".rs"],
            "patterns": [
                r"fn\s+\w+\s*\(",
                r"impl\s+\w+",
                r"struct\s+\w+",
                r"use\s+\w+",
            ]
        },
        "go": {
            "extensions": [".go"],
            "patterns": [
                r"func\s+\w+\s*\(",
                r"package\s+\w+",
                r"import\s+\(",
            ]
        },
    }

    # Technology patterns in code
    TECH_PATTERNS = {
        "FastAPI": [r"from\s+fastapi\s+import", r"FastAPI\(\)"],
        "React": [r"import\s+React", r"from\s+['\"]react['\"]", r"<\w+\s+[^>]*>"],
        "Vue": [r"import\s+Vue", r"from\s+['\"]vue['\"]", r"createApp"],
        "Express": [r"import\s+express", r"require\(['\"]express['\"]", r"app\.get\("],
        "SQLAlchemy": [r"from\s+sqlalchemy", r"import\s+sqlalchemy"],
        "Pydantic": [r"from\s+pydantic", r"class\s+\w+\(BaseModel\)"],
        "Next.js": [r"from\s+['\"]next/", r"next/link", "getServerSideProps"],
    }

    def __init__(self):
        self.analyzed_files: Dict[str, SourceAnalysis] = {}
        self._compiled_lang_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns."""
        # Language patterns
        for lang, config in self.LANGUAGE_PATTERNS.items():
            self._compiled_lang_patterns[lang] = [
                re.compile(p, re.MULTILINE) for p in config["patterns"]
            ]

    def analyze_file(self, file_path: str, content: Optional[str] = None) -> Optional[SourceAnalysis]:
        """
        Analyze a source file.

        Args:
            file_path: Path to the file
            content: Optional file content (if not provided, reads from disk)

        Returns:
            SourceAnalysis result or None if file cannot be analyzed
        """
        path = Path(file_path)

        if not path.exists():
            return None

        if content is None:
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IOError):
                return None

        # Detect language
        language = self._detect_language(path, content)
        if not language:
            return None

        # Analyze content
        analysis = SourceAnalysis(
            file_path=str(path),
            language=language,
            size_bytes=path.stat().st_size,
            line_count=len(content.split('\n')),
        )

        # Extract imports
        analysis.imports = self._extract_imports(content, language)

        # Count functions and classes
        analysis.function_count = self._count_functions(content, language)
        analysis.class_count = self._count_classes(content, language)

        # Detect technologies
        analysis.technologies = self._detect_technologies(content)

        # Store result
        self.analyzed_files[str(path)] = analysis

        return analysis

    def _detect_language(self, path: Path, content: str) -> Optional[str]:
        """Detect programming language from file."""
        extension = path.suffix.lower()

        # Check by extension first
        for lang, config in self.LANGUAGE_PATTERNS.items():
            if extension in config["extensions"]:
                return lang

        # Check by content patterns
        for lang, patterns in self._compiled_lang_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    return lang

        return None

    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements."""
        imports = []

        if language == "python":
            # Python imports
            for match in re.finditer(r'^(?:import\s+(\w+)|from\s+(\w+)\s+import)',
                                     content, re.MULTILINE):
                module = match.group(1) or match.group(2)
                if module:
                    imports.append(module)

        elif language in ["javascript", "typescript"]:
            # ES6 imports
            for match in re.finditer(r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                                     content):
                module = match.group(1)
                if module and not module.startswith('.'):
                    imports.append(module.split('/')[0])

        elif language == "rust":
            # Rust use statements
            for match in re.finditer(r'^use\s+(\w+)', content, re.MULTILINE):
                imports.append(match.group(1))

        elif language == "go":
            # Go imports
            for match in re.finditer(r'"([^"]+)"', content):
                imports.append(match.group(1))

        return list(set(imports))  # Deduplicate

    def _count_functions(self, content: str, language: str) -> int:
        """Count function definitions."""
        count = 0

        if language == "python":
            count = len(re.findall(r'^\s*def\s+\w+\s*\(', content, re.MULTILINE))
        elif language in ["javascript", "typescript"]:
            count = len(re.findall(r'function\s+\w+\s*\(', content))
            count += len(re.findall(r'const\s+\w+\s*=\s*\([^)]*\)\s*=>', content))
        elif language == "rust":
            count = len(re.findall(r'fn\s+\w+\s*\(', content))
        elif language == "go":
            count = len(re.findall(r'func\s+\w+\s*\(', content))

        return count

    def _count_classes(self, content: str, language: str) -> int:
        """Count class definitions."""
        count = 0

        if language == "python":
            count = len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
        elif language in ["javascript", "typescript"]:
            count = len(re.findall(r'class\s+\w+', content))
        elif language == "rust":
            count = len(re.findall(r'struct\s+\w+', content))

        return count

    def _detect_technologies(self, content: str) -> Set[str]:
        """Detect technologies used in code."""
        techs = set()

        for tech, patterns in self.TECH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    techs.add(tech)
                    break  # One match per technology is enough

        return techs

    def get_languages_summary(self) -> Dict[str, int]:
        """Get count of files per language."""
        summary: Dict[str, int] = {}
        for analysis in self.analyzed_files.values():
            if analysis.language not in summary:
                summary[analysis.language] = 0
            summary[analysis.language] += 1
        return summary

    def get_all_technologies(self) -> Set[str]:
        """Get all detected technologies."""
        techs = set()
        for analysis in self.analyzed_files.values():
            techs.update(analysis.technologies)
        return techs

    def clear(self) -> None:
        """Clear analysis results."""
        self.analyzed_files.clear()
