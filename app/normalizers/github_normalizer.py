"""GitHub data normalizer - converts raw GitHub collector output to normalized format."""
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.models.schemas import RepositorySnapshot, SourceFileEvidence


class GitHubNormalizer:
    """
    Normalizes raw GitHub collector data into structured formats for graph building.
    
    Converts raw JSON from GitHubCollector into:
    - RepositorySnapshot objects
    - SourceFileEvidence objects
    - Normalized dependency and config data
    """

    def __init__(self):
        pass

    def normalize_repository(self, repo_data: Dict[str, Any]) -> RepositorySnapshot:
        """
        Normalize a single repository's deep analysis data.
        
        Args:
            repo_data: Raw dict from GitHubCollector.analyze_repo_deep()
            
        Returns:
            RepositorySnapshot with normalized data
        """
        return RepositorySnapshot(
            repo_name=repo_data.get("repo_name", ""),
            full_name=repo_data.get("full_name", ""),
            owner=repo_data.get("owner", ""),
            url=repo_data.get("url", ""),
            description=repo_data.get("description", ""),
            is_private=repo_data.get("is_private", False),
            is_fork=repo_data.get("is_fork", False),
            default_branch=repo_data.get("default_branch", "main"),
            created_at=repo_data.get("created_at", ""),
            updated_at=repo_data.get("updated_at", ""),
            pushed_at=repo_data.get("pushed_at", ""),
            stars=repo_data.get("stars", 0),
            forks=repo_data.get("forks", 0),
            topics=repo_data.get("topics", []),
            languages=repo_data.get("languages_bytes", {}),
            file_count=repo_data.get("file_count", 0),
            file_paths=repo_data.get("file_paths", []),
            dependency_files=repo_data.get("dependency_files", {}),
            key_source_files=repo_data.get("key_source_files", {}),
            recent_commits=repo_data.get("recent_commits", []),
            source_system="github",
        )

    def extract_file_evidence(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        file_type: str = "source"
    ) -> SourceFileEvidence:
        """
        Create SourceFileEvidence from a file's content.
        
        Args:
            repo_name: Name of the repository
            file_path: Path to the file in repo
            content: File content
            file_type: Type of file (source, dependency, config, documentation)
            
        Returns:
            SourceFileEvidence object
        """
        # Generate hash for content
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Detect concepts in file (simple keyword matching)
        detected_concepts = self._detect_concepts(content, file_path)
        
        return SourceFileEvidence(
            file_path=file_path,
            repo_name=repo_name,
            project_name=repo_name,
            source_system="github",
            file_type=file_type,
            content_preview=content[:500],  # First 500 chars
            content_hash=content_hash,
            detected_concepts=detected_concepts,
            timestamp=datetime.utcnow().isoformat(),
        )

    def extract_all_file_evidence(
        self,
        repo_snapshot: RepositorySnapshot
    ) -> List[SourceFileEvidence]:
        """
        Extract SourceFileEvidence from all files in a repository.
        
        Args:
            repo_snapshot: Normalized repository data
            
        Returns:
            List of SourceFileEvidence objects
        """
        evidence_list = []
        
        # Extract from dependency files
        for file_name, content in repo_snapshot.dependency_files.items():
            file_type = "dependency" if any(
                x in file_name for x in ["package.json", "requirements", "pyproject"]
            ) else "config"
            
            evidence = self.extract_file_evidence(
                repo_snapshot.repo_name,
                file_name,
                content,
                file_type=file_type,
            )
            evidence_list.append(evidence)
        
        # Extract from key source files
        for file_path, content in repo_snapshot.key_source_files.items():
            evidence = self.extract_file_evidence(
                repo_snapshot.repo_name,
                file_path,
                content,
                file_type="source",
            )
            evidence_list.append(evidence)
        
        return evidence_list

    def _detect_concepts(self, content: str, file_path: str = "") -> List[str]:
        """Detect technical concepts in file content."""
        concepts = []
        content_lower = content.lower()
        
        # Language detection
        if "import " in content_lower and "from " in content_lower:
            concepts.append("python_imports")
        if "require(" in content or "import " in content:
            concepts.append("javascript_imports")
        
        # Framework detection
        if "react" in content_lower or "jsx" in file_path.lower():
            concepts.append("react")
        if "fastapi" in content_lower:
            concepts.append("fastapi")
        if "next" in content_lower and ("config" in file_path.lower() or "next.config" in file_path):
            concepts.append("nextjs")
        
        # Pattern detection
        if "class " in content and "def " in content:
            concepts.append("oop")
        if "async " in content or "await " in content:
            concepts.append("async_await")
        if "def test_" in content or "describe(" in content or "it(" in content:
            concepts.append("testing")
        
        return list(set(concepts))

    def normalize_collection_results(
        self,
        collection_result: Dict[str, Any]
    ) -> List[RepositorySnapshot]:
        """
        Normalize entire GitHub collection results.
        
        Args:
            collection_result: Raw result from GitHubCollector.collect_all()
            
        Returns:
            List of RepositorySnapshot objects
        """
        snapshots = []
        
        deep_analyses = collection_result.get("deep_analyses", [])
        for repo_data in deep_analyses:
            try:
                snapshot = self.normalize_repository(repo_data)
                snapshots.append(snapshot)
            except Exception as e:
                print(f"⚠️ Error normalizing {repo_data.get('repo_name', 'unknown')}: {e}")
        
        return snapshots
