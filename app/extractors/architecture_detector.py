"""Architecture Detector - identifies high-level architectural patterns.

Detects:
- MVC patterns (models/, views/, controllers/ directories)
- REST API patterns (route definitions, HTTP methods)
- Microservice patterns (multiple independent services, message queues)
- Monorepo patterns (multiple packages/apps in one repo)
- Event-driven patterns (pub/sub, event emitters)

Returns ArchitectureAnalysis with detected patterns and the evidence
that supports each detection.
"""

from __future__ import annotations

import re
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ArchitecturePattern:
    """A detected architectural pattern."""
    pattern_type: str  # "mvc", "rest", "microservice", "monorepo", "event_driven"
    confidence: float  # 0.0-1.0
    evidence: List[str] = field(default_factory=list)  # Files/paths that support this
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class ArchitectureAnalysis:
    """Complete architectural analysis of a project."""
    patterns: List[ArchitecturePattern] = field(default_factory=list)
    directory_structure: Dict[str, List[str]] = field(default_factory=dict)  # dir → files
    route_definitions: List[Dict[str, str]] = field(default_factory=list)  # {method, path, handler}
    services: List[str] = field(default_factory=list)  # Detected service names
    technologies: Set[str] = field(default_factory=set)


class ArchitectureDetector:
    """Detects architectural patterns from project structure and source code."""

    # ── MVC Detection ───────────────────────────────────────────────────

    MVC_DIR_PATTERNS = {
        "models": re.compile(r'(?:^|/)(?:models?|schemas?|entities?)(?:/|$)', re.I),
        "views": re.compile(r'(?:^|/)(?:views?|templates?|pages?|components?)(?:/|$)', re.I),
        "controllers": re.compile(r'(?:^|/)(?:controllers?|handlers?|routes?)(?:/|$)', re.I),
    }

    @classmethod
    def detect_mvc(cls, directory: str) -> Optional[ArchitecturePattern]:
        """Detect MVC pattern by scanning directory structure."""
        dir_path = Path(directory)
        evidence: List[str] = []
        found = {"models": False, "views": False, "controllers": False}

        # Walk first 3 levels
        for root, dirs, files in os.walk(directory):
            depth = root.replace(directory, "").count(os.sep)
            if depth > 3:
                continue

            rel_root = os.path.relpath(root, directory)
            for pattern_name, pattern in cls.MVC_DIR_PATTERNS.items():
                if pattern.search(rel_root) and not found[pattern_name]:
                    found[pattern_name] = True
                    evidence.append(f"Directory: {rel_root}")

        matched = sum(1 for v in found.values() if v)
        if matched >= 2:
            return ArchitecturePattern(
                pattern_type="mvc",
                confidence=0.4 + (matched * 0.2),
                evidence=evidence,
                details={"matched_components": str([k for k, v in found.items() if v])},
            )
        return None

    # ── REST API Detection ──────────────────────────────────────────────

    REST_ROUTE_PATTERNS = [
        # Python
        (re.compile(r'@(?:app|router|bp)\.(?:get|post|put|delete|patch)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]'), "python"),
        (re.compile(r'@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(\s*[\'\"]?([^\'\")]+)[\'\"]?'), "java"),
        # JS/TS
        (re.compile(r'(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]'), "express"),
        (re.compile(r'@(?:Get|Post|Put|Delete|Patch)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]'), "nestjs"),
        # Go
        (re.compile(r'\.(?:GET|POST|PUT|DELETE|PATCH)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]'), "go"),
        # Rust
        (re.compile(r'#\[(?:get|post|put|delete|patch)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]'), "rust"),
        # General URL pattern
        (re.compile(r'(?:route|path)\s*=\s*[\'\"](/[\w/{}_-]+)[\'\"]'), "config"),
    ]

    @classmethod
    def detect_rest(cls, directory: str) -> Optional[ArchitecturePattern]:
        """Detect REST API by scanning for route definitions."""
        dir_path = Path(directory)
        routes: List[Dict[str, str]] = []
        evidence: List[str] = []

        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in (".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java"):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) > 200_000:
                    continue
            except (UnicodeDecodeError, IOError):
                continue

            for pattern, framework in cls.REST_ROUTE_PATTERNS:
                for match in pattern.finditer(content):
                    routes.append({
                        "path": match.group(1),
                        "framework": framework,
                        "file": str(file_path),
                    })
                    evidence.append(f"{framework} route: {match.group(1)} in {file_path.name}")

        if routes:
            return ArchitecturePattern(
                pattern_type="rest",
                confidence=min(1.0, 0.3 + (len(routes) * 0.05)),
                evidence=evidence[:10],
                details={"route_count": str(len(routes))},
            )
        return None

    # ── Microservice Detection ──────────────────────────────────────────

    MICROSERVICE_INDICATORS = [
        re.compile(r'(?:docker-compose|docker-compose)\.ya?ml', re.I),
        re.compile(r'(?:service|worker|consumer|producer|publisher)', re.I),
        re.compile(r'(?:kafka|rabbitmq|redis.*queue|nats|pubsub)', re.I),
        re.compile(r'(?:gRPC|protobuf|\.proto)', re.I),
        re.compile(r'(?:kubernetes|k8s|helm|deployment)\.ya?ml', re.I),
    ]

    @classmethod
    def detect_microservice(cls, directory: str) -> Optional[ArchitecturePattern]:
        """Detect microservice architecture."""
        dir_path = Path(directory)
        evidence: List[str] = []
        services: List[str] = []

        # Check for docker-compose files
        for indicator in cls.MICROSERVICE_INDICATORS[:1]:
            for match_path in dir_path.rglob("*"):
                if match_path.is_file() and indicator.search(match_path.name):
                    evidence.append(f"Docker Compose: {match_path.name}")

                    # Read to find service names
                    try:
                        content = match_path.read_text(encoding="utf-8", errors="ignore")
                        for svc_match in re.finditer(r'^\s{2}(\w[\w-]*):', content, re.MULTILINE):
                            svc = svc_match.group(1)
                            if svc not in ("services", "version", "networks", "volumes", "x-"):
                                services.append(svc)
                    except Exception:
                        pass

        # Check for multiple service directories
        service_dirs = []
        for item in dir_path.iterdir():
            if item.is_dir() and any(
                (item / f).exists() for f in ["Dockerfile", "main.py", "main.go", "server.js", "index.ts"]
            ):
                service_dirs.append(item.name)
                services.append(item.name)

        if len(services) >= 2:
            evidence.append(f"Detected services: {', '.join(services)}")
            return ArchitecturePattern(
                pattern_type="microservice",
                confidence=0.5 + (min(len(services), 5) * 0.1),
                evidence=evidence,
                details={"service_count": str(len(services)), "services": ", ".join(services[:10])},
            )

        # Check for message queue / event bus indicators
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in (".py", ".js", ".ts", ".go", ".yaml", ".yml"):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for indicator in cls.MICROSERVICE_INDICATORS[2:]:
                if indicator.search(content):
                    evidence.append(f"Queue/bus pattern in {file_path.name}")
                    if evidence:
                        return ArchitecturePattern(
                            pattern_type="microservice",
                            confidence=0.4,
                            evidence=evidence,
                            details={},
                        )

        return None

    # ── Monorepo Detection ──────────────────────────────────────────────

    MONOREPO_INDICATORS = [
        (re.compile(r'"workspaces"'), "package.json"),
        (re.compile(r'(?:pnpm-workspace|nx\.json|turbo\.json|lerna\.json)'), "monorepo config"),
        (re.compile(r'(?:packages|apps|libs|modules)/'), "directory structure"),
    ]

    @classmethod
    def detect_monorepo(cls, directory: str) -> Optional[ArchitecturePattern]:
        """Detect monorepo pattern."""
        dir_path = Path(directory)
        evidence: List[str] = []

        # Check package.json for workspaces
        pkg_json = dir_path / "package.json"
        if pkg_json.exists():
            try:
                content = pkg_json.read_text(encoding="utf-8")
                if '"workspaces"' in content:
                    evidence.append("package.json workspaces config")
            except Exception:
                pass

        # Check for monorepo config files
        for config_file in ["pnpm-workspace.yaml", "nx.json", "turbo.json", "lerna.json"]:
            if (dir_path / config_file).exists():
                evidence.append(f"Found {config_file}")

        # Check for packages/apps directories
        for dir_name in ["packages", "apps", "libs", "modules"]:
            p = dir_path / dir_name
            if p.is_dir() and any(p.iterdir()):
                evidence.append(f"Directory: {dir_name}/")

        if len(evidence) >= 2:
            return ArchitecturePattern(
                pattern_type="monorepo",
                confidence=0.6 + (len(evidence) * 0.1),
                evidence=evidence,
                details={"indicators": ", ".join(evidence)},
            )
        return None

    # ── Event-Driven Detection ──────────────────────────────────────────

    EVENT_DRIVEN_PATTERNS = [
        re.compile(r'(?:EventEmitter|\.on\(|\.emit\(|\.publish\(|\.subscribe\()', re.I),
        re.compile(r'(?:addEventListener|dispatchEvent|CustomEvent)', re.I),
        re.compile(r'(?:@Event|@Subscribe|@EventHandler|@EventListener)', re.I),
        re.compile(r'(?:signal|dispatch|pubsub|message.*bus)', re.I),
    ]

    @classmethod
    def detect_event_driven(cls, directory: str) -> Optional[ArchitecturePattern]:
        """Detect event-driven architecture patterns."""
        dir_path = Path(directory)
        evidence: List[str] = []

        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in (".py", ".js", ".ts", ".tsx", ".go"):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) > 200_000:
                    continue
            except Exception:
                continue

            for pattern in cls.EVENT_DRIVEN_PATTERNS:
                count = len(pattern.findall(content))
                if count >= 2:  # Multiple occurrences in one file
                    evidence.append(f"{count}x event patterns in {file_path.name}")
                    break

        if evidence:
            return ArchitecturePattern(
                pattern_type="event_driven",
                confidence=0.3 + (len(evidence) * 0.1),
                evidence=evidence[:8],
                details={"files_with_events": str(len(evidence))},
            )
        return None

    # ── Main Analysis ───────────────────────────────────────────────────

    @classmethod
    def analyze(cls, directory: str) -> ArchitectureAnalysis:
        """Run all architecture detectors on a project directory.

        Returns an ArchitectureAnalysis with all detected patterns,
        route definitions, and detected services.
        """
        result = ArchitectureAnalysis()

        # Run all detectors
        detectors = [
            cls.detect_mvc,
            cls.detect_rest,
            cls.detect_microservice,
            cls.detect_monorepo,
            cls.detect_event_driven,
        ]

        for detector in detectors:
            try:
                pattern = detector(directory)
                if pattern:
                    result.patterns.append(pattern)
            except Exception as e:
                logger.debug(f"Architecture detector {detector.__name__} failed: {e}")

        # Extract route definitions (do once, not after each detector)
        dir_path = Path(directory)
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in (".py", ".js", ".ts", ".tsx", ".go"):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for pattern, framework in cls.REST_ROUTE_PATTERNS:
                for match in pattern.finditer(content):
                    method = "GET"
                    raw = match.group(0).lower()
                    for m in ["get", "post", "put", "delete", "patch"]:
                        if m in raw:
                            method = m.upper()
                            break
                    result.route_definitions.append({
                        "method": method,
                        "path": match.group(1),
                        "handler": f"{str(file_path)}:{match.start()}",
                        "framework": framework,
                    })

        # Populate technologies
        for pattern in result.patterns:
            if pattern.pattern_type == "rest":
                result.technologies.add("REST API")
            elif pattern.pattern_type == "microservice":
                result.technologies.add("Microservices")

        return result
