"""Cloudflare Collector - handles fetching data from Cloudflare"""
import os
import json
import shutil
from git import Repo
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx
from datetime import datetime
import logging

from app.config import RAW_DIR, CLOUDFLARE_TOKEN, CLOUDFLARE_ACCOUNT_ID
from app.collectors.retry_utils import with_retry, CircuitBreaker, CircuitBreakerConfig, RETRY_CONFIG_API

logger = logging.getLogger(__name__)

class CloudflareCollector:
    """Collects data from Cloudflare (workers, zones, etc.)"""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers
        self.api_token = CLOUDFLARE_TOKEN or os.getenv("CLOUDFLARE_TOKEN", "")
        self.account_id = CLOUDFLARE_ACCOUNT_ID or os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.repo_dir = None
        # Circuit breaker for API resilience
        self._api_breaker = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
        ))

        if not self.api_token:
            logger.warning("CLOUDFLARE_TOKEN not set")
        if not self.account_id:
            logger.warning("CLOUDFLARE_ACCOUNT_ID not set")

        self.base_url = "https://api.cloudflare.com/client/v4"

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    @with_retry(RETRY_CONFIG_API)
    def fetch_workers(self) -> List[Dict[str, Any]]:
        """Fetch list of workers from Cloudflare API"""
        if not self.account_id:
            logger.warning("Cannot fetch workers: account_id not set")
            return []

        try:
            # Correct endpoint: /accounts/{account_id}/workers/scripts
            url = f"{self.base_url}/accounts/{self.account_id}/workers/scripts"
            with httpx.Client() as client:
                response = client.get(url, headers=self._auth_headers())

                if response.status_code == 400:
                    logger.error(f"Cloudflare API returned 400 - check account_id and token permissions")
                    return []

                response.raise_for_status()
                data = response.json()
                workers = data.get("result", [])
                logger.info(f"Fetched {len(workers)} workers from Cloudflare")
                return workers
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch workers from Cloudflare: {str(e)}")
            return []

    @with_retry(RETRY_CONFIG_API)
    def fetch_zones(self) -> List[Dict[str, Any]]:
        """Fetch list of zones from Cloudflare API"""
        if not self.api_token:
            logger.warning("Cannot fetch zones: API token not set")
            return []

        try:
            # Zones endpoint doesn't need account_id
            url = f"{self.base_url}/zones"
            with httpx.Client() as client:
                response = client.get(url, headers=self._auth_headers())
                response.raise_for_status()
                data = response.json()
                zones = data.get("result", [])
                logger.info(f"Fetched {len(zones)} zones from Cloudflare")
                return zones
        except Exception as e:
            logger.error(f"Failed to fetch zones from Cloudflare: {str(e)}")
            return []

    @with_retry(RETRY_CONFIG_API)
    def fetch_pages(self) -> List[Dict[str, Any]]:
        """Fetch list of Cloudflare Pages projects"""
        if not self.account_id:
            return []

        try:
            url = f"{self.base_url}/accounts/{self.account_id}/pages/projects"
            with httpx.Client() as client:
                response = client.get(url, headers=self._auth_headers())
                response.raise_for_status()
                data = response.json()
                pages = data.get("result", [])
                logger.info(f"Fetched {len(pages)} Pages projects from Cloudflare")
                return pages
        except Exception as e:
            logger.error(f"Failed to fetch Pages from Cloudflare: {str(e)}")
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
        """Main collection method - returns structured data"""
        results = {
            "workers_count": 0,
            "pages_count": 0,
            "zones_count": 0,
            "collected_workers": [],
            "collected_pages": [],
            "collected_zones": [],
            "errors": []
        }

        try:
            # Fetch workers
            workers = self.fetch_workers()
            results["workers_count"] = len(workers)
            for w in workers:
                results["collected_workers"].append({
                    "name": w.get("name", "Unnamed"),
                    "id": w.get("id", ""),
                    "created_on": w.get("created_on", ""),
                    "modified_on": w.get("modified_on", ""),
                })

            # Fetch zones
            zones = self.fetch_zones()
            results["zones_count"] = len(zones)
            for z in zones:
                results["collected_zones"].append({
                    "name": z.get("name", "Unnamed Zone"),
                    "id": z.get("id", ""),
                    "status": z.get("status", "active"),
                })

            # Fetch Pages
            pages = self.fetch_pages()
            results["pages_count"] = len(pages)
            for p in pages:
                results["collected_pages"].append({
                    "name": p.get("name", "Unnamed"),
                    "id": p.get("id", ""),
                })

        except Exception as e:
            results["errors"].append(f"Cloudflare collection failed: {str(e)}")
            logger.error(results["errors"][-1])

        return results
