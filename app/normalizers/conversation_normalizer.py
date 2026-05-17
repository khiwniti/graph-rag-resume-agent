"""Conversation data normalizer - converts raw conversation export to normalized format."""
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.models.schemas import ConversationArtifact


class ConversationNormalizer:
    """
    Normalizes raw conversation collector data into structured formats for graph building.
    
    Converts raw JSON from ConversationCollector into:
    - ConversationArtifact objects
    - Normalized technology mentions
    - Normalized repo references
    """

    def __init__(self):
        pass

    def normalize_artifact(
        self,
        artifact_data: Dict[str, Any]
    ) -> ConversationArtifact:
        """
        Normalize a single conversation artifact.
        
        Args:
            artifact_data: Raw dict from ConversationCollector
            
        Returns:
            ConversationArtifact object
        """
        return ConversationArtifact(
            artifact_id=artifact_data.get("artifact_id", ""),
            artifact_type=artifact_data.get("artifact_type", "unknown"),
            content=artifact_data.get("content", "")[:5000],  # Limit content
            timestamp=artifact_data.get("timestamp", ""),
            source_path=artifact_data.get("source_file", ""),
            related_repos=artifact_data.get("related_repos", []),
            related_technologies=artifact_data.get("related_technologies", []),
            confidence=artifact_data.get("confidence", 1.0),
        )

    def extract_technology_mentions(
        self,
        artifacts: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Extract and count technology mentions across artifacts.
        
        Args:
            artifacts: List of raw artifact dicts
            
        Returns:
            Dict mapping technology name to mention count
        """
        tech_counts = {}
        
        for artifact in artifacts:
            related_techs = artifact.get("related_technologies", [])
            for tech in related_techs:
                tech_lower = tech.lower()
                if tech_lower not in tech_counts:
                    tech_counts[tech_lower] = 0
                tech_counts[tech_lower] += 1
        
        return tech_counts

    def extract_repo_references(
        self,
        artifacts: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Extract repository references across artifacts.
        
        Args:
            artifacts: List of raw artifact dicts
            
        Returns:
            Dict mapping repo name to list of artifact IDs
        """
        repo_refs = {}
        
        for artifact in artifacts:
            related_repos = artifact.get("related_repos", [])
            artifact_id = artifact.get("artifact_id", "")
            
            for repo in related_repos:
                if repo not in repo_refs:
                    repo_refs[repo] = []
                if artifact_id and artifact_id not in repo_refs[repo]:
                    repo_refs[repo].append(artifact_id)
        
        return repo_refs

    def normalize_collection_results(
        self,
        collection_result: Dict[str, Any]
    ) -> List[ConversationArtifact]:
        """
        Normalize entire conversation collection results.
        
        Args:
            collection_result: Raw result from ConversationCollector.collect_all()
            
        Returns:
            List of ConversationArtifact objects
        """
        artifacts = []
        
        raw_artifacts = collection_result.get("artifacts", [])
        for artifact_data in raw_artifacts:
            try:
                artifact = self.normalize_artifact(artifact_data)
                artifacts.append(artifact)
            except Exception as e:
                print(f"⚠️ Error normalizing conversation artifact: {e}")
        
        return artifacts

    def group_artifacts_by_type(
        self,
        artifacts: List[ConversationArtifact]
    ) -> Dict[str, List[ConversationArtifact]]:
        """
        Group artifacts by their type.
        
        Args:
            artifacts: List of ConversationArtifact objects
            
        Returns:
            Dict mapping artifact type to list of artifacts
        """
        grouped = {}
        
        for artifact in artifacts:
            art_type = artifact.artifact_type
            if art_type not in grouped:
                grouped[art_type] = []
            grouped[art_type].append(artifact)
        
        return grouped

    def get_technology_timeline(
        self,
        artifacts: List[ConversationArtifact]
    ) -> Dict[str, List[str]]:
        """
        Create a timeline of technology mentions.
        
        Args:
            artifacts: List of ConversationArtifact objects
            
        Returns:
            Dict mapping timestamp to list of technologies mentioned
        """
        timeline = {}
        
        for artifact in artifacts:
            timestamp = artifact.timestamp[:13] if artifact.timestamp else "unknown"  # YYYY-MM-DDTH
            if timestamp not in timeline:
                timeline[timestamp] = []
            
            timeline[timestamp].extend(artifact.related_technologies)
        
        # Deduplicate
        for ts in timeline:
            timeline[ts] = list(set(timeline[ts]))
        
        return timeline
