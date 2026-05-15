"""Deep GitHub codebase collector - extracts code, dependencies, architecture patterns."""
import json
import base64
import time
import re
from pathlib import Path
from typing import Optional

import httpx

from app.config import GITHUB_TOKEN, GITHUB_API, RAW_DIR


class GitHubCollector:
    """Collects deep codebase data from GitHub: repos, code, deps, patterns."""

    def __init__(self):
        self.headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.client = httpx.Client(headers=self.headers, timeout=30.0)
        self.cache_dir = RAW_DIR / "github"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── User Profile ──────────────────────────────────────────────

    def get_user_profile(self) -> dict:
        r = self.client.get(f"{GITHUB_API}/user")
        r.raise_for_status()
        return r.json()

    # ── Repository Listing (all pages) ────────────────────────────

    def get_all_repos(self) -> list[dict]:
        repos = []
        page = 1
        while True:
            r = self.client.get(
                f"{GITHUB_API}/user/repos",
                params={"per_page": 100, "sort": "updated", "page": page},
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            repos.extend(batch)
            page += 1
            time.sleep(0.3)
        return repos

    # ── Language Bytes per Repo ───────────────────────────────────

    def get_repo_languages(self, owner: str, repo: str) -> dict:
        r = self.client.get(f"{GITHUB_API}/repos/{owner}/{repo}/languages")
        if r.status_code == 200:
            return r.json()
        return {}

    # ── File Tree ─────────────────────────────────────────────────

    def get_repo_tree(self, owner: str, repo: str, branch: str = "main") -> list[dict]:
        """Get full file tree via Git Trees API (recursive)."""
        r = self.client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )
        if r.status_code == 200:
            return r.json().get("tree", [])
        # fallback to master
        r = self.client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/master",
            params={"recursive": "1"},
        )
        if r.status_code == 200:
            return r.json().get("tree", [])
        return []

    # ── Read Single File Content ──────────────────────────────────

    def get_file_content(self, owner: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
        r = self.client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch},
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("encoding") == "base64" and data.get("content"):
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return None

    # ── README ────────────────────────────────────────────────────

    def get_readme(self, owner: str, repo: str) -> str:
        content = self.get_file_content(owner, repo, "README.md")
        if content:
            return content
        content = self.get_file_content(owner, repo, "readme.md")
        if content:
            return content
        return ""

    # ── Dependency Files ──────────────────────────────────────────

    DEPENDENCY_FILES = [
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "Pipfile",
        "Cargo.toml",
        "go.mod",
        "bun.lock",
        "package-lock.json",
        "yarn.lock",
        "pom.xml",
        "build.gradle",
        "Gemfile",
        "composer.json",
        "mix.exs",
        "deno.json",
        "deno.jsonc",
        "import_map.json",
    ]

    CONFIG_FILES = [
        "next.config.ts", "next.config.js", "next.config.mjs",
        "vite.config.ts", "vite.config.js",
        "tsconfig.json", "jsconfig.json",
        "tailwind.config.ts", "tailwind.config.js",
        "postcss.config.mjs", "postcss.config.js",
        "eslint.config.mjs", ".eslintrc.json",
        "prisma/schema.prisma",
        "docker-compose.yml", "Dockerfile",
        "vercel.json", "netlify.toml",
        "wrangler.toml", "wrangler.json",
        "caddy.json", "Caddyfile",
        "vitest.config.ts", "jest.config.ts",
        "playwright.config.ts",
        "drizzle.config.ts",
        ".env.example",
        "CLAUDE.md", "AGENTS.md",
    ]

    def get_dependency_files(self, owner: str, repo: str, branch: str = "main") -> dict:
        """Extract content of all dependency & config files."""
        results = {}
        all_files = self.DEPENDENCY_FILES + self.CONFIG_FILES
        for fname in all_files:
            content = self.get_file_content(owner, repo, fname, branch)
            if content:
                results[fname] = content
            time.sleep(0.05)
        return results

    # ── Key Source Files Detection ────────────────────────────────

    KEY_FILE_PATTERNS = [
        r"^src/app/.*\.tsx?$",          # Next.js App Router pages
        r"^src/pages/.*\.tsx?$",        # Next.js Pages Router
        r"^src/components/.*\.tsx?$",   # React components
        r"^src/lib/.*\.ts$",            # Utility libraries
        r"^src/server/.*\.ts$",         # Server code
        r"^src/api/.*\.ts$",            # API routes
        r"^app/.*\.py$",                # Python app
        r"^api/.*\.py$",                # Python API
        r"^src/.*\.py$",                # Python source
        r"^main\.py$",                  # Python entry
        r"^index\.ts$",                 # TS entry
        r"^index\.js$",                 # JS entry
        r"^server\.py$",                # Python server
        r"^server\.ts$",                # TS server
        r"^worker\.ts$",                # Cloudflare Worker
        r"^worker\.js$",                # CF Worker JS
    ]

    def detect_key_source_files(self, tree: list[dict], max_files: int = 15) -> list[str]:
        """Find key source files from the repo tree."""
        key_files = []
        for entry in tree:
            path = entry.get("path", "")
            if entry.get("type") != "blob":
                continue
            for pattern in self.KEY_FILE_PATTERNS:
                if re.match(pattern, path):
                    key_files.append(path)
                    break
            if len(key_files) >= max_files:
                break
        return key_files

    def get_key_source_contents(self, owner: str, repo: str, key_files: list[str], branch: str = "main") -> dict:
        """Read content of key source files (limited to first 500 lines each)."""
        results = {}
        for path in key_files[:15]:
            content = self.get_file_content(owner, repo, path, branch)
            if content:
                lines = content.split("\n")
                results[path] = "\n".join(lines[:500])
            time.sleep(0.05)
        return results

    # ── Commit Activity ───────────────────────────────────────────

    def get_repo_commits(self, owner: str, repo: str, per_page: int = 30) -> list[dict]:
        r = self.client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            params={"per_page": per_page},
        )
        if r.status_code == 200:
            return r.json()
        return []

    # ── Comprehensive Repo Analysis ───────────────────────────────

    def analyze_repo_deep(self, repo: dict) -> dict:
        """Perform deep analysis of a single repo: code, deps, patterns."""
        owner = repo["owner"]["login"]
        name = repo["name"]
        default_branch = repo.get("default_branch", "main")

        print(f"  🔍 Deep analyzing: {owner}/{name} ...")

        # Language breakdown
        languages = self.get_repo_languages(owner, name)

        # File tree
        tree = self.get_repo_tree(owner, name, default_branch)
        file_paths = [e["path"] for e in tree if e.get("type") == "blob"]

        # README
        readme = self.get_readme(owner, name)

        # Dependency & config files
        dep_files = self.get_dependency_files(owner, name, default_branch)

        # Key source files
        key_file_paths = self.detect_key_source_files(tree)
        key_file_contents = self.get_key_source_contents(owner, name, key_file_paths, default_branch)

        # Recent commits
        commits = self.get_repo_commits(owner, name, 10)

        analysis = {
            "repo_name": name,
            "full_name": repo["full_name"],
            "owner": owner,
            "description": repo.get("description", ""),
            "url": repo["html_url"],
            "language": repo.get("language"),
            "languages_bytes": languages,
            "total_bytes": sum(languages.values()),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "is_fork": repo.get("fork", False),
            "is_private": repo.get("private", False),
            "default_branch": default_branch,
            "created_at": repo.get("created_at", ""),
            "updated_at": repo.get("updated_at", ""),
            "pushed_at": repo.get("pushed_at", ""),
            "topics": repo.get("topics", []),
            "file_count": len(file_paths),
            "file_paths": file_paths[:200],  # cap for storage
            "directory_structure": self._extract_dirs(tree),
            "readme": readme[:3000],
            "dependency_files": dep_files,
            "key_source_files": key_file_contents,
            "recent_commits": [
                {
                    "sha": c.get("sha", "")[:8],
                    "message": (c.get("commit", {}).get("message", "")[:200]),
                    "date": (c.get("commit", {}).get("author", {}).get("date", "")),
                }
                for c in commits
            ],
        }

        time.sleep(0.5)
        return analysis

    def _extract_dirs(self, tree: list[dict]) -> list[str]:
        """Extract unique directory paths."""
        dirs = set()
        for entry in tree:
            path = entry.get("path", "")
            if "/" in path:
                parent = "/".join(path.split("/")[:-1])
                dirs.add(parent)
        return sorted(dirs)[:50]

    # ── Full Collection Pipeline ──────────────────────────────────

    def collect_all(self, max_repos: int = 0) -> dict:
        """Run full collection: profile + all repos with deep analysis."""
        print("👤 Fetching GitHub profile...")
        profile = self.get_user_profile()
        self._save_json("profile", profile)

        print("📂 Fetching repository list...")
        repos = self.get_all_repos()
        print(f"   Found {len(repos)} repositories")

        # Filter out forks for skill analysis (original work only)
        original_repos = [r for r in repos if not r.get("fork", False)]
        fork_repos = [r for r in repos if r.get("fork", False)]
        print(f"   Original: {len(original_repos)}, Forks: {len(fork_repos)}")

        repos_to_analyze = original_repos
        if max_repos > 0:
            repos_to_analyze = original_repos[:max_repos]

        print(f"🔧 Deep analyzing {len(repos_to_analyze)} repos...")
        deep_analyses = []
        for i, repo in enumerate(repos_to_analyze):
            print(f"  [{i+1}/{len(repos_to_analyze)}]", end="")
            try:
                analysis = self.analyze_repo_deep(repo)
                deep_analyses.append(analysis)
            except Exception as e:
                print(f"  ⚠️ Error analyzing {repo['name']}: {e}")

        # Save fork repo names (lightweight)
        fork_summary = [{"name": r["name"], "url": r["html_url"], "fork": True} for r in fork_repos]

        result = {
            "profile": profile,
            "total_repos": len(repos),
            "original_repos_count": len(original_repos),
            "fork_repos_count": len(fork_repos),
            "deep_analyses": deep_analyses,
            "fork_repos": fork_summary,
        }

        self._save_json("full_collection", result)
        print(f"\n✅ GitHub collection complete: {len(deep_analyses)} repos deeply analyzed")
        return result

    def _save_json(self, name: str, data: dict):
        path = self.cache_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)