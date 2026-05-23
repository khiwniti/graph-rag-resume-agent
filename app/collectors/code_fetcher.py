"""Code Fetcher - handles fetching code from repositories"""
import os
import shutil
from pathlib import Path
from git import Repo
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CodeFetcher:
    """Fetches code from repository URLs"""
    
    def __init__(self, github_collector=None):
        self.github_collector = github_collector
        self.base_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "code"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def fetch_code(self, repo_url: str, target_dir: Path) -> bool:
        """Fetch code from a repository"""
        try:
            if not target_dir.exists():
                Repo.clone_from(repo_url, target_dir)
            return True
        except Exception as e:
            logger.error(f"Failed to fetch code from {repo_url}: {str(e)}")
            return False