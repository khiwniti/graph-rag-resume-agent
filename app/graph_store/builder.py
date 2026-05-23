"""Build knowledge graph from collected data."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .neo4j_store import Neo4jStore, KnowledgeGraphConfig
from ..extractors.skill_extractor import SkillExtractor, ExtractedSkill
from ..extractors.dependency_parser import DependencyParser
from ..extractors.source_analyzer import SourceAnalyzer

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """
    Builds knowledge graph from collected data.

    Orchestrates:
    1. Skill extraction from source code
    2. Dependency parsing
    3. Source analysis
    4. Neo4j graph population
    """

    def __init__(self, neo4j_config: Optional[KnowledgeGraphConfig] = None):
        self.neo4j_config = neo4j_config or KnowledgeGraphConfig()
        self.skill_extractor = SkillExtractor()
        self.dependency_parser = DependencyParser()
        self.source_analyzer = SourceAnalyzer()
        self._store: Optional[Neo4jStore] = None

    @property
    def store(self) -> Neo4jStore:
        """Lazy-load Neo4j store."""
        if self._store is None:
            self._store = Neo4jStore(self.neo4j_config)
            self._store.connect()
        return self._store

    def initialize_schema(self) -> None:
        """Create indexes and constraints."""
        self.store.create_indexes()
        self.store.create_constraints()
        logger.info("Initialized Neo4j schema")

    def build_from_collection(self, collection_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Build knowledge graph from collection results.

        Args:
            collection_data: Data from collectors with structure:
                {
                    "projects": [...],
                    "files": [...],
                    "dependencies": [...],
                }

        Returns:
            Statistics about inserted nodes
        """
        stats = {
            "projects": 0,
            "skills": 0,
            "technologies": 0,
            "relationships": 0,
        }

        # Process projects
        for project in collection_data.get("projects", []):
            self._process_project(project)
            stats["projects"] += 1

        # Process files and extract skills
        for file_data in collection_data.get("files", []):
            skills = self._process_file(
                file_data["path"],
                file_data.get("content", "")
            )
            stats["skills"] += len(skills)

        # Process dependencies
        for dep_file in collection_data.get("dependency_files", []):
            deps = self.dependency_parser.parse_file(dep_file)
            for dep in deps:
                self._process_dependency(dep)
                stats["technologies"] += 1

        return stats

    def _process_project(self, project: Dict[str, Any]) -> None:
        """Process a single project entry."""
        project_id = project.get("id")
        if not project_id:
            return

        # Upsert project
        self.store.upsert_project(
            project_id=project_id,
            name=project.get("name", "Unknown"),
            source=project.get("source", "unknown"),
            url=project.get("url"),
            description=project.get("description"),
            properties=project.get("metadata", {}),
        )

        # Link to person (owner)
        if person_id := project.get("person_id"):
            self.store.link_person_to_project(person_id, project_id)

    def _process_file(self, file_path: str, content: str) -> List[ExtractedSkill]:
        """Process a single file for skill extraction."""
        # Analyze source
        analysis = self.source_analyzer.analyze_file(file_path, content)

        # Extract skills
        skills = self.skill_extractor.extract_from_file(file_path, content)

        return skills

    def _process_dependency(self, dependency: Any) -> None:
        """Process a dependency entry."""
        # Extract technology from dependency
        tech_name = dependency.name
        self.store.upsert_technology(tech_name)

        # Link to project if available
        if project_id := getattr(dependency, 'project_id', None):
            self.store.link_project_to_technology(
                project_id, tech_name, dependency.evidence_type or 'dependency'
            )

    def ingest_skill(self, name: str, category: str, confidence: float = 1.0,
                     evidence: Optional[Dict[str, Any]] = None) -> None:
        """
        Ingest a single skill into the graph.

        Args:
            name: Skill name
            category: Skill category
            confidence: Confidence score (0-1)
            evidence: Optional evidence metadata
        """
        # Upsert skill
        self.store.upsert_skill(name, category, confidence)

        # Add evidence if provided
        if evidence:
            # Store evidence as relationship property
            pass  # Handled by link methods

    def ingest_project_skill(self, project_id: str, skill_name: str,
                              skill_category: str, evidence: Optional[str] = None) -> None:
        """Link a skill to a project."""
        self.store.link_skill_to_project(
            skill_name=skill_name,
            skill_category=skill_category,
            project_id=project_id,
            evidence=evidence,
        )

    def ingest_person_skill(self, person_id: str, skill_name: str,
                             skill_category: str, confidence: float = 1.0,
                             evidence: Optional[str] = None) -> None:
        """Link a skill to a person."""
        self.store.link_person_to_skill(
            person_id=person_id,
            skill_name=skill_name,
            skill_category=skill_category,
            confidence=confidence,
            evidence=evidence,
        )

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        return self.store.get_stats()

    def close(self) -> None:
        """Close connections."""
        if self._store:
            self._store.close()
            self._store = None

    def __enter__(self) -> "KnowledgeGraphBuilder":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
