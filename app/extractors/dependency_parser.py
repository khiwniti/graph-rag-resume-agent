"""Parse dependencies from various package manager files."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class Dependency:
    """Represents a parsed dependency."""
    name: str
    version: Optional[str] = None
    version_spec: Optional[str] = None  # e.g., "^", "~", ">="
    dev: bool = False  # Development dependency
    source: str = ""  # Source file path

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "version_spec": self.version_spec,
            "dev": self.dev,
            "source": self.source,
        }


class DependencyParser:
    """
    Parses dependencies from various package manager files.

    Supported formats:
    - package.json (npm/yarn/pnpm)
    - requirements.txt (pip)
    - pyproject.toml (poetry/pip)
    - Cargo.toml (Cargo/rust)
    - go.mod (Go modules)
    - Gemfile (Ruby bundler)
    """

    def __init__(self):
        self.dependencies: Dict[str, Dependency] = {}

    def parse_file(self, file_path: str) -> List[Dependency]:
        """
        Parse dependencies from a file.

        Args:
            file_path: Path to the dependency file

        Returns:
            List of parsed dependencies
        """
        path = Path(file_path)
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8")
        deps = []

        if path.name == "package.json":
            deps = self._parse_package_json(content, file_path)
        elif path.name == "requirements.txt":
            deps = self._parse_requirements_txt(content, file_path)
        elif path.name == "pyproject.toml":
            deps = self._parse_pyproject_toml(content, file_path)
        elif path.name == "Cargo.toml":
            deps = self._parse_cargo_toml(content, file_path)
        elif path.name == "go.mod":
            deps = self._parse_go_mod(content, file_path)
        elif path.name == "Gemfile":
            deps = self._parse_gemfile(content, file_path)

        # Store in dictionary
        for dep in deps:
            key = f"{dep.name}:{dep.source}"
            self.dependencies[key] = dep

        return deps

    def _parse_package_json(self, content: str,
                            file_path: str) -> List[Dependency]:
        """Parse package.json dependencies."""
        deps = []
        try:
            data = json.loads(content)

            # Regular dependencies
            for name, version in data.get("dependencies", {}).items():
                deps.append(Dependency(
                    name=name,
                    version=version,
                    version_spec=self._get_version_spec(version),
                    source=file_path,
                ))

            # Dev dependencies
            for name, version in data.get("devDependencies", {}).items():
                deps.append(Dependency(
                    name=name,
                    version=version,
                    version_spec=self._get_version_spec(version),
                    dev=True,
                    source=file_path,
                ))

        except json.JSONDecodeError:
            pass  # Invalid JSON, skip

        return deps

    def _parse_requirements_txt(self, content: str,
                                 file_path: str) -> List[Dependency]:
        """Parse requirements.txt dependencies."""
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Skip -r, -e, --extra-index-url, etc.
            if line.startswith('-'):
                continue

            # Parse package and version
            match = re.match(r'^([a-zA-Z0-9_-]+)(.*)$', line)
            if match:
                name = match.group(1)
                version_part = match.group(2).strip()
                version = None
                version_spec = None

                if version_part:
                    # Extract version specifier
                    spec_match = re.match(r'^([><=!~]+)(.*)$', version_part)
                    if spec_match:
                        version_spec = spec_match.group(1)
                        version = spec_match.group(2)
                    else:
                        version = version_part

                deps.append(Dependency(
                    name=name,
                    version=version,
                    version_spec=version_spec,
                    source=file_path,
                ))

        return deps

    def _parse_pyproject_toml(self, content: str,
                               file_path: str) -> List[Dependency]:
        """Parse pyproject.toml dependencies (simplified)."""
        deps = []
        # Look for dependencies in [tool.poetry.dependencies]
        in_deps = False
        for line in content.split('\n'):
            if '[tool.poetry.dependencies]' in line:
                in_deps = True
                continue
            if in_deps and line.startswith('['):
                in_deps = False
            if in_deps and '=' in line:
                match = re.match(r'^([a-zA-Z0-9_-]+)\s*=', line)
                if match:
                    name = match.group(1)
                    if name.lower() != 'python':  # Skip python version
                        deps.append(Dependency(
                            name=name,
                            source=file_path,
                        ))
        return deps

    def _parse_cargo_toml(self, content: str,
                          file_path: str) -> List[Dependency]:
        """Parse Cargo.toml dependencies (simplified)."""
        deps = []
        in_deps = False
        for line in content.split('\n'):
            if '[dependencies]' in line:
                in_deps = True
                continue
            if in_deps and line.startswith('['):
                in_deps = False
            if in_deps and '=' in line:
                match = re.match(r'^([a-zA-Z0-9_-]+)\s*=', line)
                if match:
                    name = match.group(1)
                    deps.append(Dependency(
                        name=name,
                        source=file_path,
                    ))
        return deps

    def _parse_go_mod(self, content: str,
                      file_path: str) -> List[Dependency]:
        """Parse go.mod dependencies."""
        deps = []
        in_require = False
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('require ('):
                in_require = True
                continue
            if in_require and line == ')':
                in_require = False
                continue
            if in_require or line.startswith('require '):
                # Parse: module/path v1.2.3
                match = re.match(r'^([^\s]+)\s+([^\s]+)', line)
                if match:
                    name = match.group(1)
                    version = match.group(2)
                    deps.append(Dependency(
                        name=name,
                        version=version,
                        source=file_path,
                    ))
        return deps

    def _parse_gemfile(self, content: str,
                       file_path: str) -> List[Dependency]:
        """Parse Gemfile dependencies."""
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            # Match: gem 'name', 'version' or gem "name"
            match = re.match(r"gem\s+['\"]([^\s'\"]+)['\"]", line)
            if match:
                name = match.group(1)
                deps.append(Dependency(
                    name=name,
                    source=file_path,
                ))
        return deps

    def _get_version_spec(self, version: str) -> Optional[str]:
        """Extract version specifier from version string."""
        if not version:
            return None
        match = re.match(r'^([><=~^]+)', version)
        return match.group(1) if match else None

    def get_all_dependencies(self) -> List[Dependency]:
        """Return all parsed dependencies."""
        return list(self.dependencies.values())

    def get_technologies(self) -> Set[str]:
        """Extract technology names from dependencies."""
        techs = set()
        for dep in self.dependencies.values():
            # Map common packages to technologies
            name = dep.name.lower()

            # Framework detection
            if any(x in name for x in ['react', 'vue', 'angular', 'svelte']):
                techs.add('frontend-framework')
            if any(x in name for x in ['express', 'fastapi', 'flask', 'django']):
                techs.add('backend-framework')
            if any(x in name for x in ['next', 'nuxt', 'gatsby']):
                techs.add('meta-framework')

        return techs

    def clear(self) -> None:
        """Clear all parsed dependencies."""
        self.dependencies.clear()
