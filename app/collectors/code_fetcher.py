"""Code fetcher - links Vercel projects to GitHub repos for deep code evidence."""
import re
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from app.collectors.github_collector import GitHubCollector


class CodeFetcher:
    """
    Fetches actual source code for Vercel projects by linking them to GitHub repos.
    
    Vercel projects often have a linked Git repository. This class:
    1. Extracts repo information from Vercel project metadata
    2. Uses GitHubCollector to fetch deep code evidence
    3. Returns linked code evidence for skill analysis
    """

    def __init__(self, github_collector: Optional[GitHubCollector] = None):
        """Initialize with optional GitHubCollector instance."""
        self.github_collector = github_collector or GitHubCollector()

    def extract_repo_info_from_vercel_project(self, project: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        """
        Extract owner and repo name from Vercel project metadata.
        
        Returns:
            Tuple of (owner, repo_name) or None if not found
        """
        link = project.get("link", {})
        if isinstance(link, dict):
            # Try repo field first
            repo_url = link.get("repo", "")
            if repo_url:
                return self._parse_repo_url(repo_url)
            
            # Try repoUrl field
            repo_url = link.get("repoUrl", "")
            if repo_url:
                return self._parse_repo_url(repo_url)
        
        # Try to extract from project name or other metadata
        return None

    def _parse_repo_url(self, repo_url: str) -> Optional[Tuple[str, str]]:
        """
        Parse GitHub repo URL into (owner, repo) tuple.
        
        Examples:
            - https://github.com/owner/repo -> ("owner", "repo")
            - owner/repo -> ("owner", "repo")
        """
        if not repo_url:
            return None
        
        # Pattern for full GitHub URL
        match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', repo_url)
        if match:
            return (match.group(1), match.group(2))
        
        # Pattern for owner/repo shorthand
        match = re.match(r'([^/]+)/([^/]+)$', repo_url)
        if match:
            return (match.group(1), match.group(2))
        
        return None

    def fetch_code_for_vercel_project(
        self,
        project: Dict[str, Any],
        max_files: int = 50,
        max_bytes: int = 50000
    ) -> Dict[str, Any]:
        """
        Fetch deep code evidence for a Vercel project.
        
        Args:
            project: Vercel project metadata dict
            max_files: Maximum files to fetch
            max_bytes: Maximum bytes per file
            
        Returns:
            Dict with project metadata linked to code evidence
        """
        project_name = project.get("name", "")
        project_id = project.get("id", "")
        
        result = {
            "project_name": project_name,
            "project_id": project_id,
            "has_code_evidence": False,
            "code_evidence": None,
            "linked_repo": None,
            "error": None,
        }
        
        # Try to extract repo info
        repo_info = self.extract_repo_info_from_vercel_project(project)
        if not repo_info:
            result["error"] = "No linked GitHub repository found"
            return result
        
        owner, repo_name = repo_info
        result["linked_repo"] = f"{owner}/{repo_name}"
        
        # Fetch code evidence via GitHub collector
        try:
            print(f" 🔗 Linking Vercel project '{project_name}' to GitHub repo '{owner}/{repo_name}'...")
            
            # Get repo metadata
            repo_data = self._fetch_repo_metadata(owner, repo_name)
            if not repo_data:
                result["error"] = f"Could not fetch repo metadata for {owner}/{repo_name}"
                return result
            
            # Get file tree
            tree = self.github_collector.get_repo_tree(owner, repo_name)
            if not tree:
                result["error"] = f"Could not fetch file tree for {owner}/{repo_name}"
                return result
            
            # Get dependency files
            dep_files = self.github_collector.get_dependency_files(owner, repo_name)
            
            # Detect and fetch key source files
            key_file_paths = self.github_collector.detect_key_source_files(tree, max_files)
            key_file_contents = self.github_collector.get_key_source_contents(
                owner, repo_name, key_file_paths
            )
            
            # Get README
            readme = self.github_collector.get_readme(owner, repo_name)
            
            # Get language breakdown
            languages = self.github_collector.get_repo_languages(owner, repo_name)
            
            result["has_code_evidence"] = True
            result["code_evidence"] = {
                "repo_name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "owner": owner,
                "url": repo_data.get("html_url", ""),
                "description": repo_data.get("description", ""),
                "languages": languages,
                "total_bytes": sum(languages.values()),
                "file_count": len(tree),
                "dependency_files": dep_files,
                "key_source_files": key_file_contents,
                "readme": readme[:3000],
                "topics": repo_data.get("topics", []),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
            }
            
        except Exception as e:
            result["error"] = str(e)
        
        return result

    def _fetch_repo_metadata(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch basic repo metadata from GitHub API."""
        r = self.github_collector.client.get(
            f"{self.github_collector.client.headers.get('Accept', '').split(',')[0].strip() if 'Accept' in self.github_collector.client.headers else ''}https://api.github.com/repos/{owner}/{repo}"
        )
        # Simpler approach - just use the client directly
        r = self.github_collector.client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if r.status_code == 200:
            return r.json()
        return None

    def fetch_code_for_multiple_projects(
        self,
        projects: List[Dict[str, Any]],
        max_projects: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch code evidence for multiple Vercel projects.
        
        Args:
            projects: List of Vercel project metadata dicts
            max_projects: Maximum projects to process (0 = all)
            
        Returns:
            List of code evidence results
        """
        results = []
        projects_to_process = projects[:max_projects] if max_projects > 0 else projects
        
        print(f"🔗 Fetching code evidence for {len(projects_to_process)} Vercel projects...")
        
        for i, project in enumerate(projects_to_process):
            print(f" [{i+1}/{len(projects_to_process)}]", end="")
            try:
                result = self.fetch_code_for_vercel_project(project)
                results.append(result)
                if result["has_code_evidence"]:
                    print(f" ✓", end="")
                else:
                    print(f" ⚠", end="")
            except Exception as e:
                print(f" ✗", end="")
                results.append({
                    "project_name": project.get("name", ""),
                    "project_id": project.get("id", ""),
                    "has_code_evidence": False,
                    "error": str(e),
                })
        
        print(f"\n✅ Code fetching complete")
        return results
