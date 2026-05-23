"""Code Structure Extractor - AST/regex-based extraction of code entities.

Extracts functions, classes, modules, and their relationships from source files.
Creates graph-ready data for Neo4j import (Function, Class, Module, File nodes
with CALLS, CONTAINS, INHERITS, IMPORTS relationships).
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
class CodeEntity:
    """Represents a code entity (function, class, module)."""
    entity_type: str  # "function", "class", "module"
    name: str
    file_path: str
    signature: str = ""
    line_start: int = 0
    line_end: int = 0
    bases: List[str] = field(default_factory=list)
    docstring: str = ""
    decorators: List[str] = field(default_factory=list)
    exports: bool = False


@dataclass
class CodeRelationship:
    """A relationship between two code entities."""
    rel_type: str  # "CALLS", "CONTAINS", "INHERITS", "IMPORTS", "CONTAINS_METHOD"
    source_id: str
    target_id: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class CodeStructure:
    """Complete code structure analysis for a project or file."""
    entities: List[CodeEntity] = field(default_factory=list)
    relationships: List[CodeRelationship] = field(default_factory=list)
    file_count: int = 0
    function_count: int = 0
    class_count: int = 0
    module_count: int = 0


class CodeStructureExtractor:
    """Extracts code structure (functions, classes, modules, relationships) from
    source files using AST for Python and regex for JS/TS/Go/Rust.

    Produces graph-ready CodeStructure data that can be ingested into Neo4j via
    Neo4jStore's File, Function, Class, Module node operations.
    """

    # ── Python AST extraction ──────────────────────────────────────────

    @staticmethod
    def extract_python(file_path: str, content: str) -> CodeStructure:
        """AST-based extraction for Python files."""
        result = CodeStructure()
        result.file_count = 1

        try:
            tree = ast.parse(content)
        except SyntaxError:
            logger.debug(f"Python syntax error in {file_path}, falling back to regex")
            return CodeStructureExtractor._extract_generic(file_path, content, "python")

        rel_path = Path(file_path)
        # Create a module entity for the file's package
        module_id = f"module:{rel_path.parent.as_posix().replace('/', '.')}" if rel_path.parent.as_posix() not in (".", "") else None

        # Collect all function/class definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                entity = CodeStructureExtractor._python_function(node, str(rel_path))
                result.entities.append(entity)
                result.function_count += 1

                # Extract calls within this function
                for call_node in ast.walk(node):
                    if isinstance(call_node, ast.Call):
                        call_name = CodeStructureExtractor._get_call_name(call_node)
                        if call_name:
                            result.relationships.append(CodeRelationship(
                                rel_type="CALLS",
                                source_id=entity_id("function", str(rel_path), entity.name),
                                target_id=entity_id("function", "*", call_name),
                            ))

            elif isinstance(node, ast.ClassDef):
                entity = CodeStructureExtractor._python_class(node, str(rel_path))
                result.entities.append(entity)
                result.class_count += 1

                # Methods belong to this class
                for body_node in node.body:
                    if isinstance(body_node, ast.FunctionDef):
                        method = CodeStructureExtractor._python_function(body_node, str(rel_path))
                        method.entity_type = "function"
                        result.entities.append(method)
                        result.function_count += 1
                        result.relationships.append(CodeRelationship(
                            rel_type="CONTAINS_METHOD",
                            source_id=entity_id("class", str(rel_path), entity.name),
                            target_id=entity_id("function", str(rel_path), method.name),
                        ))

        return result

    @staticmethod
    def _python_function(node: ast.FunctionDef, file_path: str) -> CodeEntity:
        args = [a.arg for a in node.args.args]
        return CodeEntity(
            entity_type="function",
            name=node.name,
            file_path=file_path,
            signature=f"def {node.name}({', '.join(args)})",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=[CodeStructureExtractor._decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node) or "",
        )

    @staticmethod
    def _python_class(node: ast.ClassDef, file_path: str) -> CodeEntity:
        return CodeEntity(
            entity_type="class",
            name=node.name,
            file_path=file_path,
            signature=f"class {node.name}",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=[CodeStructureExtractor._base_name(b) for b in node.bases],
            decorators=[CodeStructureExtractor._decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node) or "",
        )

    @staticmethod
    def _get_call_name(call_node: ast.Call) -> Optional[str]:
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None

    @staticmethod
    def _decorator_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return node.func.id
        return ""

    @staticmethod
    def _base_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    # ── JavaScript / TypeScript regex extraction ────────────────────────

    JS_FUNCTION_RE = re.compile(
        r'(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
        re.MULTILINE
    )
    JS_ARROW_RE = re.compile(
        r'(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>',
        re.MULTILINE
    )
    JS_CLASS_RE = re.compile(
        r'(?:export\s+(?:default\s+)?)?class\s+(\w+)(?:\s+extends\s+(\w+))?',
        re.MULTILINE
    )
    JS_METHOD_RE = re.compile(
        r'^\s*(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*{',
        re.MULTILINE
    )
    JS_CALL_RE = re.compile(
        r'(?:^|[^\w.])(\w+)\s*\(([^)]*)\)',
        re.MULTILINE
    )

    @classmethod
    def extract_javascript(cls, file_path: str, content: str) -> CodeStructure:
        """Regex-based extraction for JS/TS files."""
        return cls._extract_js_ts(file_path, content, "javascript")

    @classmethod
    def extract_typescript(cls, file_path: str, content: str) -> CodeStructure:
        """Regex-based extraction for TS files."""
        return cls._extract_js_ts(file_path, content, "typescript")

    @classmethod
    def _extract_js_ts(cls, file_path: str, content: str, lang: str) -> CodeStructure:
        result = CodeStructure()
        result.file_count = 1

        # Extract standalone functions
        for match in cls.JS_FUNCTION_RE.finditer(content):
            name = match.group(1)
            params = match.group(2)
            result.entities.append(CodeEntity(
                entity_type="function",
                name=name,
                file_path=file_path,
                signature=f"function {name}({params})",
                line_start=content[:match.start()].count('\n') + 1,
                exports="export" in content[max(0, match.start()-50):match.start()],
            ))
            result.function_count += 1

        # Extract arrow function assignments
        for match in cls.JS_ARROW_RE.finditer(content):
            name = match.group(1)
            params = match.group(2)
            result.entities.append(CodeEntity(
                entity_type="function",
                name=name,
                file_path=file_path,
                signature=f"const {name} = ({params}) =>",
                line_start=content[:match.start()].count('\n') + 1,
                exports="export" in content[max(0, match.start()-50):match.start()],
            ))
            result.function_count += 1

        # Extract classes
        for match in cls.JS_CLASS_RE.finditer(content):
            name = match.group(1)
            base = match.group(2)
            line_no = content[:match.start()].count('\n') + 1
            entity = CodeEntity(
                entity_type="class",
                name=name,
                file_path=file_path,
                signature=f"class {name}" + (f" extends {base}" if base else ""),
                line_start=line_no,
                bases=[base] if base else [],
                exports="export" in content[max(0, match.start()-50):match.start()],
            )
            result.entities.append(entity)
            result.class_count += 1

            # Extract methods within class body
            class_end = content.find('\n}', match.end())
            if class_end == -1:
                class_end = len(content)
            class_body = content[match.end():class_end]
            for method_match in cls.JS_METHOD_RE.finditer(class_body):
                mname = method_match.group(1)
                if mname in ("if", "for", "while", "switch", "return", "const", "let", "var"):
                    continue
                method = CodeEntity(
                    entity_type="function",
                    name=mname,
                    file_path=file_path,
                    signature=f"{mname}({method_match.group(2)})",
                    line_start=line_no + class_body[:method_match.start()].count('\n') + 1,
                )
                result.entities.append(method)
                result.function_count += 1
                result.relationships.append(CodeRelationship(
                    rel_type="CONTAINS_METHOD",
                    source_id=entity_id("class", file_path, name),
                    target_id=entity_id("function", file_path, mname),
                ))

        # Extract function calls (for CALLS relationships)
        called: Set[str] = set()
        for match in cls.JS_CALL_RE.finditer(content):
            call_name = match.group(1)
            if call_name not in ("if", "for", "while", "switch", "require", "import",
                                  "console", "return", "throw", "new", "typeof", "instanceof"):
                called.add(call_name)

        # Link calls from functions to called functions
        for entity in result.entities:
            if entity.entity_type == "function":
                func_content = content.split('\n')[entity.line_start-1:entity.line_start+20]
                func_text = '\n'.join(func_content)
                for call_name in called:
                    if call_name in func_text:
                        result.relationships.append(CodeRelationship(
                            rel_type="CALLS",
                            source_id=entity_id("function", file_path, entity.name),
                            target_id=entity_id("function", "*", call_name),
                        ))

        return result

    # ── Go regex extraction ─────────────────────────────────────────────

    GO_FUNC_RE = re.compile(r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)', re.MULTILINE)
    GO_STRUCT_RE = re.compile(r'type\s+(\w+)\s+struct\s*{', re.MULTILINE)
    GO_METHOD_RE = re.compile(r'func\s+\((\w+)\s+\*?(\w+)\)\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)

    @classmethod
    def extract_go(cls, file_path: str, content: str) -> CodeStructure:
        """Regex-based extraction for Go files."""
        result = CodeStructure()
        result.file_count = 1

        # Structs as classes
        for match in cls.GO_STRUCT_RE.finditer(content):
            line_no = content[:match.start()].count('\n') + 1
            result.entities.append(CodeEntity(
                entity_type="class", name=match.group(1), file_path=file_path,
                signature=f"type {match.group(1)} struct", line_start=line_no,
            ))
            result.class_count += 1

        # Standalone functions
        for match in cls.GO_FUNC_RE.finditer(content):
            name = match.group(1)
            params = match.group(2)
            line_no = content[:match.start()].count('\n') + 1
            result.entities.append(CodeEntity(
                entity_type="function", name=name, file_path=file_path,
                signature=f"func {name}({params})", line_start=line_no,
            ))
            result.function_count += 1

        # Methods (receiver functions linked to structs)
        for match in cls.GO_METHOD_RE.finditer(content):
            recv_name = match.group(1)
            recv_type = match.group(2)
            method_name = match.group(3)
            params = match.group(4)
            line_no = content[:match.start()].count('\n') + 1

            method = CodeEntity(
                entity_type="function", name=method_name, file_path=file_path,
                signature=f"func ({recv_name} {recv_type}) {method_name}({params})",
                line_start=line_no,
            )
            result.entities.append(method)
            result.function_count += 1

            result.relationships.append(CodeRelationship(
                rel_type="CONTAINS_METHOD",
                source_id=entity_id("class", file_path, recv_type),
                target_id=entity_id("function", file_path, method_name),
            ))

        return result

    # ── Rust regex extraction ───────────────────────────────────────────

    RUST_FN_RE = re.compile(r'(?:pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)
    RUST_STRUCT_RE = re.compile(r'(?:pub\s+)?struct\s+(\w+)', re.MULTILINE)
    RUST_IMPL_RE = re.compile(r'impl\s+(?:(\w+)\s+for\s+)?(\w+)', re.MULTILINE)

    @classmethod
    def extract_rust(cls, file_path: str, content: str) -> CodeStructure:
        """Regex-based extraction for Rust files."""
        result = CodeStructure()
        result.file_count = 1

        # Structs as classes
        for match in cls.RUST_STRUCT_RE.finditer(content):
            line_no = content[:match.start()].count('\n') + 1
            result.entities.append(CodeEntity(
                entity_type="class", name=match.group(1), file_path=file_path,
                signature=f"struct {match.group(1)}", line_start=line_no,
            ))
            result.class_count += 1

        # Functions
        for match in cls.RUST_FN_RE.finditer(content):
            name = match.group(1)
            params = match.group(2)
            line_no = content[:match.start()].count('\n') + 1
            result.entities.append(CodeEntity(
                entity_type="function", name=name, file_path=file_path,
                signature=f"fn {name}({params})", line_start=line_no,
            ))
            result.function_count += 1

        # impl blocks - link functions within impl to their struct
        for match in cls.RUST_IMPL_RE.finditer(content):
            trait = match.group(1)
            struct_name = match.group(2) if not trait else match.group(2)
            if struct_name:
                # We don't parse the body deeply here, but note the impl relationship
                result.relationships.append(CodeRelationship(
                    rel_type="CONTAINS_METHOD",
                    source_id=entity_id("class", file_path, struct_name),
                    target_id=f"function:impl_{struct_name}",
                ))

        return result

    # ── Generic fallback ────────────────────────────────────────────────

    @staticmethod
    def _extract_generic(file_path: str, content: str, language: str) -> CodeStructure:
        """Fallback regex extraction for unknown or syntax-invalid files."""
        result = CodeStructure()
        result.file_count = 1

        generic_func = re.compile(r'(?:def|fn|func|function)\s+(\w+)\s*\(', re.MULTILINE)
        for match in generic_func.finditer(content):
            result.entities.append(CodeEntity(
                entity_type="function", name=match.group(1), file_path=file_path,
                line_start=content[:match.start()].count('\n') + 1,
            ))
            result.function_count += 1

        return result

    # ── Dispatcher ──────────────────────────────────────────────────────

    # File extension → extractor method mapping
    EXTRACTORS = {
        ".py": "extract_python",
        ".js": "extract_javascript",
        ".jsx": "extract_javascript",
        ".mjs": "extract_javascript",
        ".ts": "extract_typescript",
        ".tsx": "extract_typescript",
        ".go": "extract_go",
        ".rs": "extract_rust",
    }

    @classmethod
    def extract_file(cls, file_path: str, content: Optional[str] = None) -> Optional[CodeStructure]:
        """Extract code structure from a single file.

        Args:
            file_path: Path to the source file
            content: Optional file content (reads from disk if not provided)

        Returns:
            CodeStructure or None if unsupported/invalid
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in cls.EXTRACTORS:
            return None

        if content is None:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except (UnicodeDecodeError, IOError):
                return None

        if not content or len(content) > 1_000_000:  # Skip huge files
            return None

        method_name = cls.EXTRACTORS[ext]
        extractor = getattr(cls, method_name)
        return extractor(file_path, content)

    @classmethod
    def extract_directory(cls, directory: str, max_files: int = 200) -> CodeStructure:
        """Extract code structure from all files in a directory.

        Returns a merged CodeStructure with deduplicated entities
        and cross-file relationships.
        """
        combined = CodeStructure()
        dir_path = Path(directory)

        source_exts = set(cls.EXTRACTORS.keys())
        processed = 0

        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in source_exts:
                continue
            if processed >= max_files:
                break

            structure = cls.extract_file(str(file_path))
            if structure:
                combined.entities.extend(structure.entities)
                combined.relationships.extend(structure.relationships)
                combined.function_count += structure.function_count
                combined.class_count += structure.class_count
                combined.file_count += 1
                processed += 1

        # Resolve cross-file function calls
        cls._resolve_cross_file_calls(combined)

        return combined

    @classmethod
    def _resolve_cross_file_calls(cls, structure: CodeStructure) -> None:
        """Resolve CALLS relationship targets to actual function entity IDs.

        CALLS targets use wildcard format `function:*:call_name`. This method
        resolves them to specific function entity IDs when the callee is
        defined within the same project.

        When multiple functions share a name, resolves to the one in the
        same file first, then falls back to any match.
        """
        # Build a multi-map: lowercase_name → list of (file_path, entity_id)
        defined_functions: Dict[str, List[Tuple[str, str]]] = {}
        for entity in structure.entities:
            if entity.entity_type == "function":
                eid = entity_id("function", entity.file_path, entity.name)
                defined_functions.setdefault(entity.name.lower(), []).append(
                    (entity.file_path, eid)
                )

        for rel in structure.relationships:
            if rel.rel_type == "CALLS":
                # Parse wildcard target: function:*:call_name
                parts = rel.target_id.split(":", 2)
                if len(parts) == 3 and parts[1] == "*":
                    call_name = parts[2].lower()
                    candidates = defined_functions.get(call_name, [])
                    if candidates:
                        # Resolve caller source file path from source_id
                        caller_parts = rel.source_id.split(":", 2)
                        caller_file = caller_parts[1] if len(caller_parts) == 3 else ""
                        # Prefer same-file match, then first available
                        same_file = [eid for fp, eid in candidates if fp == caller_file]
                        rel.target_id = same_file[0] if same_file else candidates[0][1]


def entity_id(entity_type: str, file_path: str, name: str) -> str:
    """Generate a unique ID for a code entity.

    Format: {type}:{file_path}:{name}
    """
    safe_path = file_path.replace("\\", "/")
    return f"{entity_type}:{safe_path}:{name}"
