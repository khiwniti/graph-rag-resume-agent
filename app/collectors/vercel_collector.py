"""Vercel Collector - fetches projects and deployments"""
import os
import shutil
from git import Repo
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx
import logging

from app.config import RAW_DIR, VERCEL_TOKEN
from app.collectors.retry_utils import with_retry, RETRY_CONFIG_API

logger = logging.getLogger(__name__)

class VercelCollector:
    """Collects data from Vercel projects"""

    def __init__(self):
        self.repo_dir = None
        self.vercel_token = VERCEL_TOKEN
        self.base_url = "https://api.vercel.com"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.vercel_token}",
            "Content-Type": "application/json"
        }

    @with_retry(RETRY_CONFIG_API)
    def get_projects_from_vercel(self) -> List[Dict[str, Any]]:
        """Fetch project data from Vercel API v1"""
        if not self.vercel_token:
            logger.warning("VERCEL_TOKEN not set")
            return []

        try:
            # Use v1 API endpoint
            url = f"{self.base_url}/v1/projects"
            response = httpx.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code == 404:
                logger.warning("Vercel API returned 404 - check token permissions")
                return []

            response.raise_for_status()
            data = response.json()
            
            # v1 API returns a list directly; other versions may wrap in {"projects": [...]}
            if isinstance(data, list):
                projects = data
            else:
                projects = data.get("projects", [])
            
            logger.info(f"Fetched {len(projects)} projects from Vercel")
            return projects
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Vercel API HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return []
        except Exception as e:
            logger.error(f"Vercel API request failed: {str(e)}")
            return []

    def clone_repo(self, repo_url, target_dir):
        """Clone a GitHub repository to the target directory."""
        try:
            Repo.clone_from(repo_url, target_dir)
            self.repo_dir = Path(target_dir)
            return True
        except Exception as e:
            logger.error(f"Clone failed: {str(e)}")
            return False

    def extract_resume_data(self, repo_path):
        """Extract resume data from files in the repository."""
        resume_data = []
        repo_path = Path(repo_path)

        for file_path in repo_path.rglob('*'):
            if file_path.suffix.lower() in ['.pdf', '.docx', '.txt']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        resume_data.append({
                            'file_path': str(file_path),
                            'content': content[:5000]
                        })
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
        return resume_data

    def cleanup_repo(self, repo_path):
        """Remove the cloned repository directory."""
        try:
            shutil.rmtree(repo_path)
            logger.info(f"Cleaned up {repo_path}")
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

    def collect_all(self) -> Dict[str, Any]:
        """Collect data from Vercel projects"""
        results = {
            "projects_collected": 0,
            "total_projects": 0,
            "collected_projects": [],
            "errors": []
        }

        try:
            projects = self.get_projects_from_vercel()
            results["total_projects"] = len(projects)

            for project in projects:
                project_data = {
                    "name": project.get("name", "Unnamed"),
                    "id": project.get("id", ""),
                    "framework": project.get("framework", None),
                    "git_repository": project.get("gitRepository", None),
                    "url": project.get("url", ""),
                }
                results["collected_projects"].append(project_data)
                results["projects_collected"] += 1

        except Exception as e:
            results["errors"].append(f"Vercel collection failed: {str(e)}")
            logger.error(results["errors"][-1])

        return results
