"""Source code analyzer - detects patterns, frameworks, and architecture in source files."""
import re
from typing import Dict, Any, List, Set, Tuple
from collections import Counter


class SourceAnalyzer:
    """
    Analyzes source code files to detect:
    - Programming languages
    - Frameworks and libraries used
    - Architecture patterns
    - API patterns
    - Testing approaches
    - Infrastructure as code
    """

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": [r"^import\s+\w+", r"^from\s+\w+\s+import", r"def\s+\w+\s*\(", r"class\s+\w+"],
        "typescript": [r"import\s+.*\s+from\s+['\"]", r"export\s+(default|const|function|class)", r"interface\s+\w+", r"type\s+\w+\s*="],
        "javascript": [r"import\s+.*\s+from\s+['\"]", r"export\s+default", r"const\s+\w+\s*=", r"function\s+\w+\s*\("],
        "rust": [r"fn\s+\w+\s*\(", r"let\s+mut\s+\w+", r"impl\s+\w+", r"struct\s+\w+"],
        "go": [r"func\s+\w+\s*\(", r"package\s+\w+", r"import\s+\(", r"type\s+\w+\s+struct"],
        "sql": [r"SELECT\s+", r"INSERT\s+INTO", r"CREATE\s+TABLE", r"ALTER\s+TABLE"],
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "react": [r"import\s+React", r"from\s+['\"]react['\"]", r"<\w+\s+[^>]*>", r"useState|useEffect|useContext"],
        "nextjs": [r"next/head", r"next/link", r"getServerSideProps", r"getStaticProps"],
        "vue": [r"import\s+.*\s+from\s+['\"]vue['\"]", r"export\s+default\s+{", r"v-if|v-for"],
        "fastapi": [r"from\s+fastapi", r"@app\.router\.", r"def\s+\w+\s*\([^:]*:\s*Request"],
        "django": [r"from\s+django", r"django\.db", r"class\s+\w+\(models\.Model\)", r"admin\.site\.register"],
        "flask": [r"from\s+flask", r"Flask\(\)", r"@app\.route"],
        "express": [r"import\s+express", r"require\(['\"]express['\"]\)", r"app\.get\(|app\.post\("],
        "hono": [r"import\s+.*\s+from\s+['\"]hono", r"new\s+Hono", r"hono"],
    }

    # Architecture pattern detection
    ARCHITECTURE_PATTERNS = {
        "api_first": [r"@app\.router\.", r"@router\.", r"FastAPI\(\)", r"express"],
        "component_based": [r"export\s+default\s+function\s+\w+", r"function\s+\w+\s*\([^)]*\)\s*{", r"return\s+\("],
        "event_driven": [r"addEventListener", r"on\w+\s*=", r"emit\(", r"subscribe\("],
        "serverless": [r"export\s+const\s+handler", r"exports\.handler", r"async\s+handler"],
        "microservice": [r"health\s*\(", r"liveness\s*\(", r"readiness\s*\("],
    }

    def __init__(self):
        pass

    def detect_language(self, file_path: str, content: str) -> str:
        """
        Detect programming language of a file.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Detected language name
        """
        # First try by file extension
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".rs": "rust",
            ".go": "go",
            ".sql": "sql",
        }
        
        ext = "." + file_path.split(".")[-1] if "." in file_path else ""
        if ext in ext_map:
            return ext_map[ext]
        
        # Fallback to content analysis
        return self._detect_language_by_content(content)

    def _detect_language_by_content(self, content: str) -> str:
        """Detect language by analyzing content patterns."""
        scores = {}
        
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    score += 1
            if score > 0:
                scores[lang] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "unknown"

    def detect_frameworks(self, content: str, file_path: str = "") -> List[str]:
        """
        Detect frameworks used in the content.
        
        Args:
            content: File content
            file_path: Optional file path for context
            
        Returns:
            List of detected framework names
        """
        detected = []
        
        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected.append(framework)
                    break  # One match per framework is enough
        
        return list(set(detected))

    def detect_architecture_patterns(self, content: str) -> List[str]:
        """
        Detect architecture patterns in the content.
        
        Returns:
            List of detected pattern names
        """
        detected = []
        
        for pattern_name, patterns in self.ARCHITECTURE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected.append(pattern_name)
                    break
        
        return list(set(detected))

    def extract_imports(self, content: str, language: str = "python") -> List[str]:
        """
        Extract import statements from code.
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            List of imported modules/packages
        """
        imports = []
        
        if language == "python":
            # Python: import x, from x import y
            matches = re.findall(r"^(?:import|from)\s+([\w.]+)", content, re.MULTILINE)
            imports = [m.split(".")[0] for m in matches if m]
            
        elif language in ["typescript", "javascript"]:
            # JS/TS: import x from 'y', import 'y', require('y')
            matches = re.findall(r"from\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content)
            for match in matches:
                if match[0]:
                    imports.append(match[0])
                if match[1]:
                    imports.append(match[1])
        
        return list(set(imports))

    def analyze_file(
        self,
        file_path: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a single file.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Dict with analysis results
        """
        language = self.detect_language(file_path, content)
        frameworks = self.detect_frameworks(content, file_path)
        patterns = self.detect_architecture_patterns(content)
        imports = self.extract_imports(content, language)
        
        # Additional metrics
        line_count = len(content.split("\n"))
        char_count = len(content)
        
        # Detect if it's a test file
        is_test = any(x in file_path.lower() for x in ["test", "spec", "test_"])
        if language == "python" and is_test:
            patterns.append("testing")
        
        return {
            "file_path": file_path,
            "language": language,
            "frameworks": frameworks,
            "architecture_patterns": patterns,
            "imports": imports,
            "line_count": line_count,
            "character_count": char_count,
            "is_test": is_test,
        }

    def analyze_repository_files(
        self,
        file_contents: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analyze multiple files from a repository.
        
        Args:
            file_contents: Dict mapping file path to content
            
        Returns:
            Aggregated analysis results
        """
        all_languages = []
        all_frameworks = []
        all_patterns = []
        all_imports = []
        file_analyses = []
        
        for file_path, content in file_contents.items():
            analysis = self.analyze_file(file_path, content)
            file_analyses.append(analysis)
            
            all_languages.append(analysis["language"])
            all_frameworks.extend(analysis["frameworks"])
            all_patterns.extend(analysis["architecture_patterns"])
            all_imports.extend(analysis["imports"])
        
        # Aggregate results
        language_counts = Counter(all_languages)
        framework_counts = Counter(all_frameworks)
        pattern_counts = Counter(all_patterns)
        
        return {
            "primary_language": language_counts.most_common(1)[0][0] if language_counts else "unknown",
            "languages": dict(language_counts),
            "frameworks": list(set(all_frameworks)),
            "framework_counts": dict(framework_counts),
            "architecture_patterns": list(set(all_patterns)),
            "pattern_counts": dict(pattern_counts),
            "all_imports": list(set(all_imports)),
            "file_count": len(file_contents),
            "file_analyses": file_analyses,
        }
