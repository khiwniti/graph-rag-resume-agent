"""Deep Vercel collector - extracts projects, frameworks, deployments, build configs."""
import json
import time
from pathlib import Path
from typing import Optional

import httpx

from app.config import VERCEL_TOKEN, VERCEL_API, RAW_DIR


class VercelCollector:
    """Collects deep data from Vercel: projects, deployments, configs, domains."""

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {VERCEL_TOKEN}",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(headers=self.headers, timeout=30.0)
        self.cache_dir = RAW_DIR / "vercel"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── User/Team Info ────────────────────────────────────────────

    def get_user(self) -> dict:
        r = self.client.get(f"{VERCEL_API}/v2/user")
        r.raise_for_status()
        return r.json()

    def get_teams(self) -> list[dict]:
        r = self.client.get(f"{VERCEL_API}/v2/teams")
        if r.status_code == 200:
            return r.json().get("teams", [])
        return []

    # ── Projects ──────────────────────────────────────────────────

    def get_all_projects(self, team_id: Optional[str] = None) -> list[dict]:
        projects = []
        base = f"{VERCEL_API}/v9/projects"
        if team_id:
            base += f"?teamId={team_id}"
        page = 1
        while True:
            r = self.client.get(base, params={"limit": 100, "page": page})
            if r.status_code != 200:
                break
            data = r.json()
            batch = data.get("projects", [])
            projects.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            time.sleep(0.3)
        return projects

    # ── Deployments ───────────────────────────────────────────────

    def get_project_deployments(self, project_id: str, limit: int = 10) -> list[dict]:
        r = self.client.get(
            f"{VERCEL_API}/v13/deployments",
            params={"projectId": project_id, "limit": limit},
        )
        if r.status_code == 200:
            return r.json().get("deployments", [])
        return []

    # ── Domains ───────────────────────────────────────────────────

    def get_project_domains(self, project_id: str) -> list[dict]:
        r = self.client.get(f"{VERCEL_API}/v9/projects/{project_id}/domains")
        if r.status_code == 200:
            return r.json().get("domains", [])
        return []

    # ── Environment Variables (names only, no values) ─────────────

    def get_project_env_vars(self, project_id: str) -> list[str]:
        r = self.client.get(
            f"{VERCEL_API}/v9/projects/{project_id}/env?decrypt=false"
        )
        if r.status_code == 200:
            data = r.json()
            return [e.get("key", "") for e in data.get("envs", [])]
        return []

    # ── Deep Project Analysis ─────────────────────────────────────

    def analyze_project_deep(self, project: dict) -> dict:
        """Deep analysis of a Vercel project."""
        pid = project.get("id", "")
        name = project.get("name", "")

        print(f"  🔍 Analyzing Vercel project: {name} ...")

        # Deployments
        deployments = self.get_project_deployments(pid, 5)

        # Domains
        domains = self.get_project_domains(pid)

        # Env var keys
        env_keys = self.get_project_env_vars(pid)

        # Extract framework info
        framework = project.get("framework", "")
        build_settings = project.get("buildSettings", {}) or {}
        dev_command = project.get("devCommand", "")
        install_command = project.get("installCommand", "")
        build_command = project.get("buildCommand", "")
        output_directory = project.get("outputDirectory", "")
        root_directory = project.get("rootDirectory", "")

        # Extract git repo link
        link = project.get("link", {})
        git_repo = ""
        if isinstance(link, dict):
            git_repo = link.get("repo", "")
            if not git_repo:
                repo_url = link.get("repoUrl", "")
                git_repo = repo_url

        # Deployment summary
        deployment_summaries = []
        for dep in deployments[:5]:
            deployment_summaries.append({
                "id": dep.get("uid", ""),
                "url": dep.get("url", ""),
                "state": dep.get("state", ""),
                "created_at": dep.get("created", ""),
                "branch": dep.get("target", ""),
                "ready_at": dep.get("ready", ""),
            })

        # Domain summary
        domain_summaries = []
        for d in domains:
            domain_summaries.append({
                "name": d.get("name", ""),
                "verified": d.get("verified", False),
            })

        analysis = {
            "project_name": name,
            "project_id": pid,
            "framework": framework,
            "build_settings": build_settings,
            "dev_command": dev_command,
            "install_command": install_command,
            "build_command": build_command,
            "output_directory": output_directory,
            "root_directory": root_directory,
            "git_repo": git_repo,
            "env_var_keys": env_keys,
            "deployments": deployment_summaries,
            "domains": domain_summaries,
            "created_at": project.get("createdAt", ""),
            "updated_at": project.get("updatedAt", ""),
            "latest_deployments": project.get("targets", {}),
        }

        time.sleep(0.3)
        return analysis

    # ── Full Collection Pipeline ──────────────────────────────────

    def collect_all(self) -> dict:
        """Run full Vercel collection."""
        print("👤 Fetching Vercel user info...")
        user = self.get_user()
        self._save_json("user", user)

        print("👥 Fetching teams...")
        teams = self.get_teams()

        print("📂 Fetching projects...")
        projects = self.get_all_projects()
        print(f"   Found {len(projects)} projects")

        print(f"🔧 Deep analyzing {len(projects)} projects...")
        deep_analyses = []
        for i, proj in enumerate(projects):
            print(f"  [{i+1}/{len(projects)}]", end="")
            try:
                analysis = self.analyze_project_deep(proj)
                deep_analyses.append(analysis)
            except Exception as e:
                print(f"  ⚠️ Error: {e}")

        result = {
            "user": user,
            "teams": teams,
            "total_projects": len(projects),
            "deep_analyses": deep_analyses,
        }

        self._save_json("full_collection", result)
        print(f"\n✅ Vercel collection complete: {len(deep_analyses)} projects analyzed")
        return result

    def _save_json(self, name: str, data: dict):
        path = self.cache_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)