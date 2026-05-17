"""Dependency parser - extracts technologies from dependency files."""
import json
import re
from typing import Dict, Any, List, Optional, Set
from pathlib import Path


class DependencyParser:
    """
    Parses dependency files (package.json, requirements.txt, etc.) to extract technologies.
    
    Categorizes dependencies into:
    - Languages
    - Frameworks
    - Libraries
    - Databases
    - Testing tools
    - Build tools
    - Deployment targets
    """

    # Technology categorization maps
    FRAMEWORKS = {
        "react": "frontend",
        "next": "frontend",
        "next.js": "frontend",
        "vue": "frontend",
        "angular": "frontend",
        "svelte": "frontend",
        "django": "backend",
        "flask": "backend",
        "fastapi": "backend",
        "express": "backend",
        "nestjs": "backend",
        "rails": "backend",
        "laravel": "backend",
        "spring": "backend",
    }

    DATABASES = {
        "postgresql": "database",
        "postgres": "database",
        "mysql": "database",
        "sqlite": "database",
        "mongodb": "database",
        "mongo": "database",
        "redis": "cache",
        "elasticsearch": "search",
        "d1": "database",
        "turso": "database",
        "planetscale": "database",
    }

    TESTING = {
        "pytest": "testing",
        "jest": "testing",
        "vitest": "testing",
        "mocha": "testing",
        "chai": "testing",
        "testing-library": "testing",
        "playwright": "testing",
        "cypress": "testing",
        "selenium": "testing",
    }

    def __init__(self):
        pass

    def parse_package_json(self, content: str) -> Dict[str, Any]:
        """
        Parse package.json content.
        
        Returns:
            Dict with dependencies, devDependencies, and categorized tech
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON", "dependencies": [], "dev_dependencies": []}

        dependencies = data.get("dependencies", {})
        dev_dependencies = data.get("devDependencies", {})

        all_deps = []
        
        # Process regular dependencies
        for pkg, version in dependencies.items():
            all_deps.append({
                "name": pkg,
                "version": version,
                "is_dev": False,
                "category": self._categorize_package(pkg),
            })

        # Process dev dependencies
        for pkg, version in dev_dependencies.items():
            all_deps.append({
                "name": pkg,
                "version": version,
                "is_dev": True,
                "category": self._categorize_package(pkg),
            })

        # Extract framework info
        framework = self._detect_framework(data)

        return {
            "dependencies": all_deps,
            "framework": framework,
            "build_tool": self._detect_build_tool(data),
            "package_manager": self._detect_package_manager(data),
        }

    def parse_requirements_txt(self, content: str) -> Dict[str, Any]:
        """
        Parse requirements.txt content.
        
        Returns:
            Dict with dependencies and categorized tech
        """
        dependencies = []
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Parse package==version, package>=version, etc.
            match = re.match(r"^([a-zA-Z0-9_-]+)([>=<!=]+)?(.*)?$", line)
            if match:
                pkg_name = match.group(1)
                version = match.group(3) or ""
                
                dependencies.append({
                    "name": pkg_name,
                    "version": version,
                    "is_dev": False,
                    "category": self._categorize_package(pkg_name),
                })

        return {
            "dependencies": dependencies,
            "framework": self._detect_python_framework(dependencies),
            "package_manager": "pip",
        }

    def parse_pyproject_toml(self, content: str) -> Dict[str, Any]:
        """
        Parse pyproject.toml content (simplified, regex-based).
        
        Returns:
            Dict with dependencies and metadata
        """
        result = {
            "dependencies": [],
            "dev_dependencies": [],
            "build_tool": "poetry",
        }

        # Simple regex parsing for dependencies
        in_deps = False
        in_dev_deps = False

        for line in content.split("\n"):
            line = line.strip()
            
            if line == "[tool.poetry.dependencies]":
                in_deps = True
                in_dev_deps = False
                continue
            elif line == "[tool.poetry.group.dev.dependencies]":
                in_deps = False
                in_dev_deps = True
                continue
            elif line.startswith("["):
                in_deps = False
                in_dev_deps = False
                continue

            if in_deps or in_dev_deps:
                match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*["\']?([^"\']+)["\']?', line)
                if match:
                    pkg_name = match.group(1)
                    version = match.group(2)
                    
                    dep = {
                        "name": pkg_name,
                        "version": version,
                        "is_dev": in_dev_deps,
                        "category": self._categorize_package(pkg_name),
                    }
                    
                    if in_dev_deps:
                        result["dev_dependencies"].append(dep)
                    else:
                        result["dependencies"].append(dep)

        return result

    def _categorize_package(self, pkg_name: str) -> str:
        """Categorize a package name."""
        pkg_lower = pkg_name.lower()
        
        # Check frameworks
        for fw, category in self.FRAMEWORKS.items():
            if fw in pkg_lower:
                return category
        
        # Check databases
        for db, category in self.DATABASES.items():
            if db in pkg_lower:
                return "database"
        
        # Check testing
        for test, category in self.TESTING.items():
            if test in pkg_lower:
                return "testing"
        
        # Heuristics
        if any(x in pkg_lower for x in ["ui", "component", "react", "vue", "angular"]):
            return "frontend"
        
        if any(x in pkg_lower for x in ["server", "api", "db", "sql"]):
            return "backend"
        
        return "library"

    def _detect_framework(self, package_data: Dict[str, Any]) -> Optional[str]:
        """Detect main framework from package.json."""
        deps = package_data.get("dependencies", {})
        dev_deps = package_data.get("devDependencies", {})
        all_pkgs = set(list(deps.keys()) + list(dev_deps.keys()))
        
        # Check for common frameworks
        if any("next" in p for p in all_pkgs):
            return "Next.js"
        if any("react" in p for p in all_pkgs):
            return "React"
        if any("vue" in p for p in all_pkgs):
            return "Vue"
        if any("angular" in p for p in all_pkgs):
            return "Angular"
        if any("svelte" in p for p in all_pkgs):
            return "Svelte"
        
        return None

    def _detect_build_tool(self, package_data: Dict[str, Any]) -> Optional[str]:
        """Detect build tool from package.json scripts."""
        scripts = package_data.get("scripts", {})
        scripts_str = json.dumps(scripts)
        
        if "vite" in scripts_str:
            return "Vite"
        if "webpack" in scripts_str:
            return "Webpack"
        if "rollup" in scripts_str:
            return "Rollup"
        if "esbuild" in scripts_str:
            return "esbuild"
        if "tsc" in scripts_str or "typescript" in scripts_str:
            return "TypeScript"
        
        return None

    def _detect_package_manager(self, package_data: Dict[str, Any]) -> str:
        """Detect package manager from lockfile presence or config."""
        # This would ideally check for lockfile presence
        # For now, default to npm
        return "npm"

    def _detect_python_framework(self, dependencies: List[Dict]) -> Optional[str]:
        """Detect Python framework from dependencies."""
        for dep in dependencies:
            name = dep["name"].lower()
            if "django" in name:
                return "Django"
            if "flask" in name:
                return "Flask"
            if "fastapi" in name:
                return "FastAPI"
            if "tornado" in name:
                return "Tornado"
        
        return None

    def parse_all_dependency_files(
        self,
        dependency_files: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Parse all dependency files and merge results.
        
        Args:
            dependency_files: Dict mapping filename to content
            
        Returns:
            Merged dependency information
        """
        all_dependencies = []
        frameworks = []
        build_tools = []
        
        for file_name, content in dependency_files.items():
            if file_name == "package.json":
                result = self.parse_package_json(content)
                all_dependencies.extend(result.get("dependencies", []))
                if result.get("framework"):
                    frameworks.append(result["framework"])
                if result.get("build_tool"):
                    build_tools.append(result["build_tool"])
                    
            elif file_name in ["requirements.txt", "requirements.txt"]:
                result = self.parse_requirements_txt(content)
                all_dependencies.extend(result.get("dependencies", []))
                if result.get("framework"):
                    frameworks.append(result["framework"])
                    
            elif file_name == "pyproject.toml":
                result = self.parse_pyproject_toml(content)
                all_dependencies.extend(result.get("dependencies", []))
                all_dependencies.extend(result.get("dev_dependencies", []))
        
        # Deduplicate dependencies by name
        seen = set()
        unique_deps = []
        for dep in all_dependencies:
            if dep["name"] not in seen:
                seen.add(dep["name"])
                unique_deps.append(dep)
        
        return {
            "all_dependencies": unique_deps,
            "frameworks": list(set(frameworks)),
            "build_tools": list(set(build_tools)),
            "total_count": len(unique_deps),
        }
