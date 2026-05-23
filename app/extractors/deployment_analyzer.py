"""Deployment Analyzer - deep analysis of Vercel and Cloudflare deployments.

Extracts:
- Environment variables (as Config nodes)
- Route/endpoint definitions (as Route nodes)
- Domain names (as Domain nodes)
- Build configuration (as Config nodes)
- Framework detection from deployment config
- Git repository links for cross-source correlation

Produces graph-ready data for Neo4j (Config, Route, Domain nodes).
"""

from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

logger = logging.getLogger(__name__)


@dataclass
class DeploymentRoute:
    """A route/endpoint defined in deployment configuration."""
    method: str = "GET"  # HTTP method
    path: str = "/"  # Route path pattern
    source: str = ""  # Source URL pattern
    destination: str = ""  # Destination (function, static, etc.)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class DeploymentConfig:
    """A configuration entry extracted from deployment configs."""
    key: str
    value: str = ""
    config_type: str = "env_var"  # env_var, build_setting, route_rule
    source: str = ""  # Which file/config it came from
    is_secret: bool = False


@dataclass
class DeploymentDomain:
    """A domain name associated with a deployment."""
    name: str
    verified: bool = False
    is_primary: bool = False


@dataclass
class DeploymentAnalysis:
    """Complete deployment analysis for a project."""
    platform: str = ""  # "vercel", "cloudflare", etc.
    routes: List[DeploymentRoute] = field(default_factory=list)
    configs: List[DeploymentConfig] = field(default_factory=list)
    domains: List[DeploymentDomain] = field(default_factory=list)
    framework: str = ""
    build_command: str = ""
    output_dir: str = ""
    node_version: str = ""
    linked_github_repo: Optional[str] = None


class DeploymentAnalyzer:
    """Analyzes deployment configurations for deep graph ingestion."""

    # ── Vercel Analysis ─────────────────────────────────────────────────

    @staticmethod
    def analyze_vercel_project(project_data: Dict[str, Any]) -> DeploymentAnalysis:
        """Deep-analyze a single Vercel project's data.

        Extracts framework, env vars, domains, and routes from the
        Vercel API response data.
        """
        result = DeploymentAnalysis(platform="vercel")

        # Framework detection
        framework = project_data.get("framework")
        if framework:
            result.framework = framework
            result.configs.append(DeploymentConfig(
                key="framework", value=framework,
                config_type="build_setting", source="vercel_api",
            ))

        # Build settings
        for field, config_type in [
            ("buildCommand", "build_command"),
            ("outputDirectory", "output_dir"),
            ("installCommand", "install_command"),
            ("devCommand", "dev_command"),
            ("nodeVersion", "node_version"),
        ]:
            val = project_data.get(field)
            if val:
                setattr(result, config_type.replace("_command", "_command"), val)
                result.configs.append(DeploymentConfig(
                    key=field, value=str(val),
                    config_type="build_setting", source="vercel_api",
                ))

        # Environment variables (if available from API)
        env_vars = project_data.get("env", []) or project_data.get("environmentVariables", [])
        if isinstance(env_vars, dict):
            env_vars = [{"key": k, "value": v} for k, v in env_vars.items()]
        for env_entry in env_vars:
            if isinstance(env_entry, dict):
                result.configs.append(DeploymentConfig(
                    key=env_entry.get("key", env_entry.get("name", "")),
                    value="***" if env_entry.get("type") == "secret" else env_entry.get("value", ""),
                    config_type="env_var",
                    source="vercel_api",
                    is_secret=env_entry.get("type") == "secret",
                ))

        # Domains
        domains_data = project_data.get("domains", []) or project_data.get("alias", [])
        if isinstance(domains_data, list):
            for d in domains_data:
                if isinstance(d, dict):
                    result.domains.append(DeploymentDomain(
                        name=d.get("name", d.get("domain", "")),
                        verified=d.get("verified", False),
                    ))

        # Routes (from vercel.json if available)
        routes_data = project_data.get("routes", [])
        if routes_data:
            for route in routes_data:
                if isinstance(route, dict):
                    result.routes.append(DeploymentRoute(
                        source=route.get("src", route.get("source", "")),
                        destination=route.get("dest", route.get("destination", "")),
                        headers=route.get("headers", {}),
                    ))

        # Git repository link
        git_repo = project_data.get("gitRepository", project_data.get("link", {}))
        if isinstance(git_repo, dict):
            repo_name = git_repo.get("repo", git_repo.get("fullName", ""))
            if repo_name:
                result.linked_github_repo = f"github:{repo_name.split('/')[-1]}" if "/" in repo_name else repo_name

        return result

    # ── vercel.json File Analysis ───────────────────────────────────────

    @staticmethod
    def analyze_vercel_json(file_path: str, content: Optional[str] = None) -> Optional[DeploymentAnalysis]:
        """Parse a vercel.json configuration file."""
        if content is None:
            path = Path(file_path)
            if not path.exists():
                return None
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return None

        result = DeploymentAnalysis(platform="vercel")

        try:
            config = json.loads(content)
        except json.JSONDecodeError:
            return None

        # Routes
        for route in config.get("routes", []):
            if isinstance(route, dict):
                result.routes.append(DeploymentRoute(
                    source=route.get("src", route.get("source", "/")),
                    destination=route.get("dest", route.get("destination", "")),
                    headers=route.get("headers", {}),
                ))

        # Build config
        build = config.get("build", {}) or config.get("builds", [{}])[0] if config.get("builds") else {}
        for key, val in build.items():
            result.configs.append(DeploymentConfig(
                key=f"build.{key}", value=str(val),
                config_type="build_setting", source=file_path,
            ))

        # Environment
        for key, val in config.get("env", {}).items():
            result.configs.append(DeploymentConfig(
                key=key, value=str(val),
                config_type="env_var", source=file_path,
            ))

        # Functions (serverless)
        functions = config.get("functions", {})
        for pattern, func_config in functions.items():
            result.configs.append(DeploymentConfig(
                key=f"function:{pattern}", value=json.dumps(func_config),
                config_type="build_setting", source=file_path,
            ))

        return result

    # ── Cloudflare Worker Analysis ──────────────────────────────────────

    @staticmethod
    def analyze_cloudflare_worker(worker_data: Dict[str, Any]) -> DeploymentAnalysis:
        """Deep-analyze a Cloudflare Worker's data."""
        result = DeploymentAnalysis(platform="cloudflare")

        # Worker metadata
        for field in ["name", "compatibility_date", "compatibility_flags"]:
            val = worker_data.get(field)
            if val:
                result.configs.append(DeploymentConfig(
                    key=f"worker.{field}", value=str(val),
                    config_type="build_setting", source="cloudflare_api",
                ))

        # Bindings (KV, D1, R2, queues, etc.)
        bindings = worker_data.get("bindings", [])
        for binding in bindings:
            if isinstance(binding, dict):
                btype = binding.get("type", "unknown")
                bname = binding.get("name", "")
                result.configs.append(DeploymentConfig(
                    key=f"binding:{bname}", value=btype,
                    config_type="build_setting", source="cloudflare_api",
                ))

        # Environment variables
        env_vars = worker_data.get("env_vars", {}) or worker_data.get("text_blobs", {})
        if isinstance(env_vars, dict):
            for key, val in env_vars.items():
                result.configs.append(DeploymentConfig(
                    key=key, value=str(val)[:100],
                    config_type="env_var", source="cloudflare_api",
                ))

        # Routes
        routes = worker_data.get("routes", [])
        for route in routes:
            if isinstance(route, dict):
                result.routes.append(DeploymentRoute(
                    path=route.get("pattern", route.get("route", "/*")),
                    source="cloudflare_worker",
                ))
            elif isinstance(route, str):
                result.routes.append(DeploymentRoute(path=route))

        return result

    # ── wrangler.toml File Analysis ─────────────────────────────────────

    @staticmethod
    def analyze_wrangler_toml(file_path: str, content: Optional[str] = None) -> Optional[DeploymentAnalysis]:
        """Parse a wrangler.toml configuration file."""
        if content is None:
            path = Path(file_path)
            if not path.exists():
                return None
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return None

        result = DeploymentAnalysis(platform="cloudflare")

        # Simple TOML parsing (no external dependency)
        current_section = "root"
        for line in content.split("\n"):
            line = line.strip()

            # Section header
            section_match = re.match(r'^\[([^\]]+)\]', line)
            if section_match:
                current_section = section_match.group(1)
                continue

            # Key-value pair
            kv_match = re.match(r'^(\w[\w_-]*)\s*=\s*(.+)$', line)
            if kv_match:
                key = kv_match.group(1)
                value = kv_match.group(2).strip().strip('"').strip("'")

                if key in ("name", "compatibility_date", "main", "account_id"):
                    result.configs.append(DeploymentConfig(
                        key=f"wrangler.{key}", value=value,
                        config_type="build_setting", source=file_path,
                    ))

                # KV namespace bindings
                if "kv" in current_section.lower() or key == "binding":
                    result.configs.append(DeploymentConfig(
                        key=f"kv_binding:{key}", value=value,
                        config_type="build_setting", source=file_path,
                    ))

                # Environment variables
                if current_section.startswith("env") or "vars" in current_section:
                    result.configs.append(DeploymentConfig(
                        key=key, value=value,
                        config_type="env_var", source=file_path,
                    ))

            # Route definition
            route_match = re.match(r'\{.*pattern\s*=\s*"([^"]+)".*\}', line)
            if route_match:
                result.routes.append(DeploymentRoute(
                    path=route_match.group(1),
                    source="wrangler_toml",
                ))

        return result

    # ── Cloudflare Pages Analysis ────────────────────────────────────────

    @staticmethod
    def analyze_cloudflare_page(page_data: Dict[str, Any]) -> DeploymentAnalysis:
        """Deep-analyze a Cloudflare Pages project."""
        result = DeploymentAnalysis(platform="cloudflare_pages")

        # Build config
        build_config = page_data.get("build_config", {}) or page_data.get("deployment_configs", {}).get("production", {})
        if build_config:
            for key in ["build_command", "destination_dir", "root_dir", "build_caching"]:
                val = build_config.get(key)
                if val is not None:
                    result.configs.append(DeploymentConfig(
                        key=key, value=str(val),
                        config_type="build_setting", source="cloudflare_api",
                    ))

        # Domains
        domains = page_data.get("domains", []) or page_data.get("canonical_deployment", {}).get("url", "")
        if isinstance(domains, list):
            for d in domains:
                if isinstance(d, str):
                    result.domains.append(DeploymentDomain(name=d))
                elif isinstance(d, dict):
                    result.domains.append(DeploymentDomain(name=d.get("name", "")))
        elif isinstance(domains, str) and domains:
            result.domains.append(DeploymentDomain(name=domains))

        # Environment variables
        env_vars = page_data.get("env_vars", {}) or page_data.get("deployment_configs", {}).get("production", {}).get("env_vars", {})
        if isinstance(env_vars, dict):
            for key, val in env_vars.items():
                result.configs.append(DeploymentConfig(
                    key=key, value=str(val.get("value", val)) if isinstance(val, dict) else str(val),
                    config_type="env_var", source="cloudflare_api",
                    is_secret=isinstance(val, dict) and val.get("type") == "secret",
                ))

        # Git repository link
        git_repo = page_data.get("source", {}).get("config", {})
        repo_name = git_repo.get("repo_name", git_repo.get("full_name", ""))
        if repo_name:
            result.linked_github_repo = f"github:{repo_name.split('/')[-1]}" if "/" in repo_name else repo_name

        return result

    # ── Cloudflare Zone Analysis ─────────────────────────────────────────

    @staticmethod
    def analyze_cloudflare_zone(zone_data: Dict[str, Any]) -> DeploymentAnalysis:
        """Deep-analyze a Cloudflare Zone."""
        result = DeploymentAnalysis(platform="cloudflare")

        # The zone name is itself a domain
        zone_name = zone_data.get("name", "")
        if zone_name:
            result.domains.append(DeploymentDomain(
                name=zone_name,
                verified=True,
                is_primary=True,
            ))

        # Zone settings
        for field in ["status", "plan", "type"]:
            val = zone_data.get(field)
            if val:
                result.configs.append(DeploymentConfig(
                    key=f"zone.{field}", value=str(val),
                    config_type="build_setting", source="cloudflare_api",
                ))

        return result


def config_id(project_id: str, key: str) -> str:
    """Generate a Neo4j Config node ID."""
    return f"config:{project_id}:{key}"


def route_id(project_id: str, method: str, path: str) -> str:
    """Generate a Neo4j Route node ID."""
    return f"route:{project_id}:{method}:{path}"
