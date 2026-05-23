"""Cross-File Linker - maps imports and dependencies between files within a project.

Creates IMPORTS relationships between File nodes in the knowledge graph,
enabling graph traversal to understand code dependencies and architecture.
"""

from __future__ import annotations

import ast
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FileImport:
    """A single import from one file to another."""
    source_file: str
    imported_module: str  # e.g., "os", "./utils", "react"
    is_relative: bool = False
    resolved_file: Optional[str] = None  # Absolute path if resolved
    import_type: str = "module"  # "module", "file", "package"


@dataclass
class CrossFileMap:
    """Complete cross-file dependency map for a project."""
    imports: List[FileImport] = field(default_factory=list)
    exports: Dict[str, List[str]] = field(default_factory=dict)  # file → [exported_names]
    file_graph: Dict[str, Set[str]] = field(default_factory=dict)  # file → {imported_files}


class CrossFileLinker:
    """Analyzes import/dependency statements to build a cross-file dependency graph.

    Supports:
    - Python: import X, from X import Y, from .module import X
    - JavaScript/TypeScript: import X from './module', require('./module')
    - Go: import "package/path"
    - Rust: use crate::module, use super::
    """

    # ── Python imports ──────────────────────────────────────────────────

    @staticmethod
    def extract_python_imports(file_path: str, content: str) -> List[FileImport]:
        """Extract all imports from a Python file."""
        imports: List[FileImport] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return CrossFileLinker._extract_python_imports_regex(file_path, content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(FileImport(
                        source_file=file_path,
                        imported_module=alias.name,
                        is_relative=False,
                        import_type="module",
                    ))

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    level = node.level  # Number of dots for relative imports
                    is_rel = level > 0

                    imports.append(FileImport(
                        source_file=file_path,
                        imported_module=module_name,
                        is_relative=is_rel,
                        import_type="module",
                    ))

        return imports

    @staticmethod
    def _extract_python_imports_regex(file_path: str, content: str) -> List[FileImport]:
        """Regex fallback for Python imports."""
        imports: List[FileImport] = []
        for match in re.finditer(r'^(?:import\s+(\w+)|from\s+(\.+)?(\w+)\s+import)', content, re.MULTILINE):
            if match.group(1):  # import X
                imports.append(FileImport(
                    source_file=file_path,
                    imported_module=match.group(1),
                    is_relative=False,
                    import_type="module",
                ))
            elif match.group(3):  # from .X import Y
                is_rel = bool(match.group(2))
                imports.append(FileImport(
                    source_file=file_path,
                    imported_module=match.group(3),
                    is_relative=is_rel,
                    import_type="module",
                ))
        return imports

    # ── JavaScript/TypeScript imports ───────────────────────────────────

    @staticmethod
    def extract_javascript_imports(file_path: str, content: str) -> List[FileImport]:
        """Extract ES6 import and require statements from JS/TS files."""
        imports: List[FileImport] = []

        # ES6 imports: import X from './module'
        for match in re.finditer(r"import\s+(?:[\w*\s{},]*\s+from\s+)?['\"]([^'\"]+)['\"]", content):
            module_path = match.group(1)
            is_rel = module_path.startswith('.')
            imports.append(FileImport(
                source_file=file_path,
                imported_module=module_path,
                is_relative=is_rel,
                import_type="file" if is_rel else "package",
            ))

        # require() calls: const X = require('./module')
        for match in re.finditer(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
            module_path = match.group(1)
            is_rel = module_path.startswith('.')
            imports.append(FileImport(
                source_file=file_path,
                imported_module=module_path,
                is_relative=is_rel,
                import_type="file" if is_rel else "package",
            ))

        return imports

    # ── Go imports ──────────────────────────────────────────────────────

    @staticmethod
    def extract_go_imports(file_path: str, content: str) -> List[FileImport]:
        """Extract Go import statements."""
        imports: List[FileImport] = []

        # Single-line: import "package"
        for match in re.finditer(r'import\s+"([^"]+)"', content):
            imports.append(FileImport(
                source_file=file_path,
                imported_module=match.group(1),
                is_relative=False,
                import_type="package",
            ))

        # Multi-line: import ( ... )
        in_import_block = False
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('import ('):
                in_import_block = True
                continue
            if in_import_block and stripped == ')':
                in_import_block = False
                continue
            if in_import_block:
                m = re.match(r'"([^"]+)"', stripped)
                if m:
                    imports.append(FileImport(
                        source_file=file_path,
                        imported_module=m.group(1),
                        is_relative=False,
                        import_type="package",
                    ))

        return imports

    # ── Rust imports ────────────────────────────────────────────────────

    @staticmethod
    def extract_rust_imports(file_path: str, content: str) -> List[FileImport]:
        """Extract Rust use statements."""
        imports: List[FileImport] = []

        for match in re.finditer(r'use\s+(crate::|super::|self::)?([\w:]+)', content):
            path = match.group(2)
            is_rel = bool(match.group(1))
            imports.append(FileImport(
                source_file=file_path,
                imported_module=path,
                is_relative=is_rel,
                import_type="module",
            ))

        return imports

    # ── Resolution ──────────────────────────────────────────────────────

    @staticmethod
    def resolve_relative_import(import_path: str, source_dir: str, ext: str) -> Optional[str]:
        """Resolve a relative import path to an absolute file path.

        Handles:
        - Python: from .module import X → ./module.py
        - JS/TS: import X from './module' → ./module.js|.ts|.tsx
        """
        if not import_path:
            return None

        base = Path(source_dir)
        resolved = base / import_path

        # Try with extension
        if ext in (".py",):
            candidate = resolved.with_suffix(".py")
            if candidate.exists():
                return str(candidate)

        if ext in (".js", ".jsx", ".mjs", ".ts", ".tsx"):
            for try_ext in [ext, ".js", ".ts", ".tsx", ".jsx"]:
                candidate = Path(str(resolved) + try_ext)
                if candidate.exists():
                    return str(candidate)
                # Try index file
                idx_candidate = resolved / f"index{try_ext}"
                if idx_candidate.exists():
                    return str(idx_candidate)

        return None

    # ── Dispatcher ──────────────────────────────────────────────────────

    IMPORT_EXTRACTORS = {
        ".py": "extract_python_imports",
        ".js": "extract_javascript_imports",
        ".jsx": "extract_javascript_imports",
        ".mjs": "extract_javascript_imports",
        ".ts": "extract_javascript_imports",
        ".tsx": "extract_javascript_imports",
        ".go": "extract_go_imports",
        ".rs": "extract_rust_imports",
    }

    @classmethod
    def extract_imports(cls, file_path: str, content: Optional[str] = None) -> List[FileImport]:
        """Extract all imports from a source file."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in cls.IMPORT_EXTRACTORS:
            return []

        if content is None:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except (UnicodeDecodeError, IOError):
                return []

        if not content:
            return []

        method_name = cls.IMPORT_EXTRACTORS[ext]
        extractor = getattr(cls, method_name)
        return extractor(file_path, content)

    @classmethod
    def build_dependency_map(cls, directory: str, max_files: int = 200) -> CrossFileMap:
        """Build a complete cross-file dependency map for a project directory.

        Returns a CrossFileMap with resolved file imports suitable for
        creating IMPORTS relationships in Neo4j.
        """
        result = CrossFileMap()
        dir_path = Path(directory)
        processed = 0

        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in cls.IMPORT_EXTRACTORS:
                continue
            if processed >= max_files:
                break

            imports = cls.extract_imports(str(file_path))
            result.imports.extend(imports)

            # Build file_graph adjacency
            source = str(file_path)
            if source not in result.file_graph:
                result.file_graph[source] = set()

            for imp in imports:
                if imp.is_relative:
                    resolved = cls.resolve_relative_import(
                        imp.imported_module, str(file_path.parent), ext
                    )
                    if resolved:
                        imp.resolved_file = resolved
                        result.file_graph[source].add(resolved)
                else:
                    # External package import
                    result.file_graph[source].add(f"package:{imp.imported_module}")

            processed += 1

        return result


def file_id(file_path: str, project_id: str) -> str:
    """Generate a Neo4j File node ID."""
    safe = file_path.replace("\\", "/")
    return f"file:{project_id}:{safe}"
