"""Vercel data normalizer - converts raw Vercel collector output to normalized format."""
import hashlib
from datetime import datetime
from typing import Dict, Any, List

from app.models.schemas import ProjectSnapshot, DeploymentSnapshot


class VercelNormalizer:
    """
    Normalizes raw Vercel collector data into structured formats for graph building.
    
    Converts raw JSON from VercelCollector into:
    - ProjectSnapshot objects
    - DeploymentSnapshot objects
    - Normalized build/deployment metadata
    """

    def __init__(self):
        pass

    def normalize_project(self, project_data: Dict[str, Any]) -> ProjectSnapshot:
        """
        Normalize a Vercel project's data.
        
        Args:
            project_data: Raw dict from VercelCollector.analyze_project_deep()
            
        Returns:
            ProjectSnapshot with normalized data
        """
        # Extract git repo info
        git_repo = project_data.get("git_repo", "")
        
        return ProjectSnapshot(
            project_name=project_data.get("project_name", ""),
            project_id=project_data.get("project_id", ""),
            framework=project_data.get("framework", ""),
            build_settings=project_data.get("build_settings", {}),
            git_repo=git_repo,
            env_var_keys=project_data.get("env_var_keys", []),
            deployments=project_data.get("deployments", []),
            domains=project_data.get("domains", []),
            created_at=project_data.get("created_at", ""),
            updated_at=project_data.get("updated_at", ""),
            source_system="vercel",
        )

    def normalize_deployments(
        self,
        project_name: str,
        deployments_data: List[Dict[str, Any]]
    ) -> List[DeploymentSnapshot]:
        """
        Normalize deployment data for a project.
        
        Args:
            project_name: Name of the parent project
            deployments_data: List of deployment dicts
            
        Returns:
            List of DeploymentSnapshot objects
        """
        snapshots = []
        
        for dep in deployments_data:
            snapshot = DeploymentSnapshot(
                deployment_id=dep.get("id", ""),
                project_name=project_name,
                repo_name="",  # Would need to extract from git_repo
                url=dep.get("url", ""),
                state=dep.get("state", ""),
                branch=dep.get("branch", ""),
                created_at=dep.get("created_at", ""),
                ready_at=dep.get("ready_at", ""),
                source_system="vercel",
            )
            snapshots.append(snapshot)
        
        return snapshots

    def extract_framework_info(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract framework and build information from project.
        
        Args:
            project_data: Raw project data
            
        Returns:
            Dict with framework details
        """
        framework = project_data.get("framework", "")
        build_settings = project_data.get("build_settings", {})
        
        return {
            "framework": framework,
            "build_command": build_settings.get("buildCommand", ""),
            "output_directory": build_settings.get("outputDirectory", ""),
            "install_command": build_settings.get("installCommand", ""),
            "dev_command": project_data.get("dev_command", ""),
            "has_custom_config": bool(
                build_settings.get("buildCommand") or 
                build_settings.get("outputDirectory")
            ),
        }

    def normalize_collection_results(
        self,
        collection_result: Dict[str, Any]
    ) -> List[ProjectSnapshot]:
        """
        Normalize entire Vercel collection results.
        
        Args:
            collection_result: Raw result from VercelCollector.collect_all()
            
        Returns:
            List of ProjectSnapshot objects
        """
        snapshots = []
        
        deep_analyses = collection_result.get("deep_analyses", [])
        for project_data in deep_analyses:
            try:
                snapshot = self.normalize_project(project_data)
                snapshots.append(snapshot)
            except Exception as e:
                print(f"⚠️ Error normalizing {project_data.get('project_name', 'unknown')}: {e}")
        
        return snapshots
