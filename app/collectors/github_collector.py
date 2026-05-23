"""GitHub Collector - fetches repositories and analyzes code"""
import os
import shutil
import base64
import tempfile
from git import Repo
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx
import logging

from app.config import RAW_DIR, GITHUB_TOKEN
from app.collectors.retry_utils import with_retry, CircuitBreaker, CircuitBreakerConfig, RETRY_CONFIG_API

logger = logging.getLogger(__name__)

class GitHubCollector:
    """Collects data from GitHub repositories using the API"""

    def __init__(self, max_repos=0):
        self.repo_dir = None
        self.max_repos = max_repos
        self.github_token = GITHUB_TOKEN
        self.base_url = "https://api.github.com"
        # Circuit breaker for API resilience
        self._api_breaker = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
        ))

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    @with_retry(RETRY_CONFIG_API)
    def get_authenticated_user(self) -> str:
        """Get the authenticated GitHub username"""
        if not self.github_token:
            return ""

        try:
            response = httpx.get(
                f"{self.base_url}/user",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("login", "")
        except Exception as e:
            logger.error(f"Failed to get authenticated user: {e}")
            return ""

    @with_retry(RETRY_CONFIG_API)
    def get_user_repos(self, username: str = None) -> List[Dict[str, Any]]:
        """Fetch repositories for the authenticated user"""
        if not self.github_token:
            logger.warning("GITHUB_TOKEN not set, cannot fetch repos")
            return []

        try:
            # Fetch authenticated user's repos
            url = f"{self.base_url}/user/repos"
            params = {
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "type": "owner"
            }

            all_repos = []
            page = 1

            while True:
                params["page"] = page
                response = httpx.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                repos = response.json()

                if not repos:
                    break

                all_repos.extend(repos)
                page += 1

                # Respect max_repos limit
                if self.max_repos > 0 and len(all_repos) >= self.max_repos:
                    all_repos = all_repos[:self.max_repos]
                    break

            logger.info(f"Fetched {len(all_repos)} repositories from GitHub")
            return all_repos

        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch repos from GitHub: {e}")
            return []

    @with_retry(RETRY_CONFIG_API)
    def get_repo_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Fetch languages used in a repository"""
        try:
            response = httpx.get(
                f"{self.base_url}/repos/{owner}/{repo}/languages",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch languages for {owner}/{repo}: {e}")
            return {}

    def get_repo_contents(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """Fetch contents of a repository directory"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            response = httpx.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch contents for {owner}/{repo}/{path}: {e}")
            return []

    @with_retry(RETRY_CONFIG_API)
    def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Fetch content of a specific file"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            response = httpx.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            content_b64 = data.get("content", "")
            if content_b64:
                return base64.b64decode(content_b64).decode("utf-8", errors="ignore")
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch file {owner}/{repo}/{path}: {e}")
            return None

    def get_repo_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetch README content for a repository"""
        for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
            content = self.get_file_content(owner, repo, readme_name)
            if content:
                return content
        return None

    def clone_repo(self, repo_url: str, target_dir: str) -> bool:
        """Clone a GitHub repository to the target directory."""
        try:
            # Use authenticated URL if token is available
            if self.github_token and "github.com" in repo_url:
                auth_url = repo_url.replace(
                    "https://github.com",
                    f"https://{self.github_token}@github.com"
                )
            else:
                auth_url = repo_url

            Repo.clone_from(auth_url, target_dir, depth=1)
            self.repo_dir = Path(target_dir)
            return True
        except Exception as e:
            logger.error(f"Clone failed: {str(e)}")
            return False

    def cleanup_repo(self, repo_path: str) -> None:
        """Remove the cloned repository directory."""
        try:
            shutil.rmtree(repo_path)
            logger.info(f"Cleaned up {repo_path}")
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

    def extract_skills_from_repo(self, repo_path: str) -> List[Dict[str, Any]]:
        """Extract skills from repository files"""
        from app.extractors import SkillExtractor

        extractor = SkillExtractor()
        all_skills = []
        repo_path = Path(repo_path)

        # Analyze key files
        key_files = [
            "package.json", "requirements.txt", "pyproject.toml",
            "Cargo.toml", "go.mod", "Gemfile", "pom.xml",
            "Dockerfile", "docker-compose.yml", ".env.example",
            "tsconfig.json", "next.config.js", "vercel.json"
        ]

        for file_path in repo_path.rglob('*'):
            if not file_path.is_file():
                continue

            # Check if it's a key config file
            if file_path.name in key_files:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    skills = extractor.extract_from_file(str(file_path), content)
                    # Serialize skill evidence properly for Neo4j storage
                    all_skills.extend([{"name": s.name, "category": s.category, "confidence": s.confidence, "evidence": [e.to_dict() for e in s.evidence]} for s in skills])
                except Exception:
                    pass

            # Analyze source code files (limited)
            suffix = file_path.suffix.lower()
            if suffix in ['.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.rb']:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if len(content) < 500000:  # Skip huge files
                        skills = extractor.extract_from_file(str(file_path), content)
                        # Serialize skill evidence properly for Neo4j storage
                        all_skills.extend([{"name": s.name, "category": s.category, "confidence": s.confidence, "evidence": [e.to_dict() for e in s.evidence]} for s in skills])
                except Exception:
                    pass

        return all_skills

    def get_repo_dates(self, repo_path: str) -> Dict[str, Optional[str]]:
        """Extract first and last commit dates from a cloned repository."""
        from git import Git
        try:
            g = Git(repo_path)
            first = g.log("--reverse", "--format=%cI", "-1")
            last = g.log("--format=%cI", "-1")
            return {
                "first_commit_at": first if first else None,
                "last_commit_at": last if last else None,
            }
        except Exception as e:
            logger.debug(f"Failed to extract commit dates from {repo_path}: {e}")
            return {"first_commit_at": None, "last_commit_at": None}

    def collect_streaming(self, max_repos: int = None, include_forks: bool = False):
        """Stream repos one at a time: clone → extract → yield → caller cleans up.

        Memory-efficient: only one cloned repo exists at a time.
        Yields (repo_data, analysis) tuples. Caller must cleanup after each yield.
        """
        effective_max_repos = max_repos if max_repos is not None else self.max_repos

        username = self.get_authenticated_user()
        if not username:
            logger.error("Could not authenticate with GitHub")
            return

        logger.info(f"Authenticated as GitHub user: {username}")

        repos = self.get_user_repos(username)
        logger.info(f"Fetched {len(repos)} repositories total")

        if not include_forks:
            repos = [r for r in repos if not r.get("fork", False)]

        if effective_max_repos > 0:
            repos = repos[:effective_max_repos]

        yield_count = 0
        for repo in repos:
            repo_name = repo.get("name", "unknown")
            full_name = repo.get("full_name", f"{username}/{repo_name}")
            owner, name = full_name.split("/") if "/" in full_name else (username, repo_name)

            repo_data = {
                "name": repo_name,
                "full_name": full_name,
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url", ""),
                "is_private": repo.get("private", False),
                "fork": repo.get("fork", False),
                "created_at": repo.get("created_at", ""),
                "pushed_at": repo.get("pushed_at", ""),
                "updated_at": repo.get("updated_at", ""),
            }

            # Fetch languages and README (lightweight API calls)
            repo_data["languages"] = self.get_repo_languages(owner, name)
            readme = self.get_repo_readme(owner, name)
            repo_data["readme"] = readme[:2000] if readme else ""

            # Clone and extract skills
            clone_url = repo.get("clone_url", "")
            target_dir = os.path.join(RAW_DIR, repo_name)

            analysis = {"repo": repo_name, "repo_path": None, "status": "clone_failed"}

            if self.clone_repo(clone_url, target_dir):
                try:
                    skills = self.extract_skills_from_repo(target_dir)
                    repo_data["extracted_skills"] = skills
                    dates = self.get_repo_dates(target_dir)
                    repo_data.update(dates)
                    analysis = {
                        "repo": repo_name,
                        "repo_path": target_dir,
                        "status": "success",
                    }
                except Exception as e:
                    logger.error(f"Skill extraction failed for {repo_name}: {e}")
                    analysis["repo_path"] = target_dir
                    analysis["status"] = "extraction_failed"

            yield repo_data, analysis
            yield_count += 1

        logger.info(f"Streaming complete: yielded {yield_count} repos")

    def collect_all(self, max_repos: int = None, include_forks: bool = False) -> Dict[str, Any]:
        """Collect data from all accessible GitHub repositories.

        Cleanup of cloned repositories is the caller's responsibility
        to ensure data is safely persisted before deletion.
        """
        effective_max_repos = max_repos if max_repos is not None else self.max_repos

        results = {
            "repos_collected": 0,
            "original_repos_count": 0,
            "deep_analyses": [],
            "collected_repos": [],
            "errors": []
        }

        # Get authenticated user
        username = self.get_authenticated_user()
        if not username:
            results["errors"].append("Could not authenticate with GitHub")
            return results

        logger.info(f"Authenticated as GitHub user: {username}")

        # Fetch user repos
        repos = self.get_user_repos(username)
        results["original_repos_count"] = len(repos)

        if not include_forks:
            repos = [r for r in repos if not r.get("fork", False)]

        if effective_max_repos > 0:
            repos = repos[:effective_max_repos]

        for repo in repos:
            repo_name = repo.get("name", "unknown")
            full_name = repo.get("full_name", f"{username}/{repo_name}")
            owner, name = full_name.split("/") if "/" in full_name else (username, repo_name)

            repo_data = {
                "name": repo_name,
                "full_name": full_name,
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url", ""),
                "is_private": repo.get("private", False),
                "fork": repo.get("fork", False),
                "created_at": repo.get("created_at", ""),
                "pushed_at": repo.get("pushed_at", ""),
                "updated_at": repo.get("updated_at", ""),
            }

            # Fetch languages
            languages = self.get_repo_languages(owner, name)
            repo_data["languages"] = languages

            # Fetch README
            readme = self.get_repo_readme(owner, name)
            repo_data["readme"] = readme[:2000] if readme else ""

            # Clone and extract skills
            clone_url = repo.get("clone_url", "")
            target_dir = os.path.join(RAW_DIR, repo_name)

            if self.clone_repo(clone_url, target_dir):
                try:
                    skills = self.extract_skills_from_repo(target_dir)
                    repo_data["extracted_skills"] = skills

                    # Extract commit dates for timeline
                    dates = self.get_repo_dates(target_dir)
                    repo_data.update(dates)

                    results["deep_analyses"].append({
                        "repo": repo_name,
                        "files_processed": len(skills),
                        "status": "success",
                        "skills": skills,
                        "repo_path": target_dir,
                    })
                except Exception as e:
                    results["deep_analyses"].append({
                        "repo": repo_name,
                        "error": str(e),
                        "status": "failed",
                        "repo_path": target_dir,
                    })
                    results["errors"].append(str(e))
                    # Leave clone on disk for retry/debug
            else:
                # Still collect repo metadata even if clone fails
                results["deep_analyses"].append({
                    "repo": repo_name,
                    "status": "clone_failed"
                })

            results["collected_repos"].append(repo_data)
            results["repos_collected"] += 1

        return results
