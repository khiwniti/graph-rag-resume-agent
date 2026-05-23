"""Neo4j knowledge graph store for resume RAG system."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

try:
    from neo4j import GraphDatabase, Driver
    from neo4j.exceptions import ServiceUnavailable, AuthError
    _NEO4J_AVAILABLE = True
except ImportError:
    GraphDatabase = None  # type: ignore
    Driver = None  # type: ignore
    ServiceUnavailable = Exception  # type: ignore
    AuthError = Exception  # type: ignore
    _NEO4J_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeGraphConfig:
    """Configuration for Neo4j connection."""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = ""
    database: str = "neo4j"


class Neo4jStore:
    """
    Neo4j-based knowledge graph store for resume RAG.

    Node Types:
    - Person: The individual (you)
    - Project: GitHub repos, Vercel projects, Cloudflare workers
    - Skill: Extracted skills with confidence scores
    - Technology: Technologies, frameworks, languages
    - Deployment: Vercel/Cloudflare deployments
    - Narrative: LLM-generated career story chunks per project

    Relationships:
    - (:Person)-[:OWNS]->(:Project)
    - (:Person)-[:HAS_SKILL]->(:Skill)
    - (:Project)-[:USES_TECHNOLOGY]->(:Technology)
    - (:Project)-[:DEPLOYED_ON]->(:Deployment)
    - (:Skill)<-[:REQUIRES_SKILL]-(:Project)
    - (:Project)-[:DESCRIBED_BY]->(:Narrative)
    - (:Narrative)-[:MENTIONS]->(:Skill|:Technology)
    """

    # Node labels
    PERSON = "Person"
    PROJECT = "Project"
    SKILL = "Skill"
    TECHNOLOGY = "Technology"
    DEPLOYMENT = "Deployment"
    NARRATIVE = "Narrative"

    # Relationship types
    OWNS = "OWNS"
    HAS_SKILL = "HAS_SKILL"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    DEPLOYED_ON = "DEPLOYED_ON"
    REQUIRES_SKILL = "REQUIRES_SKILL"
    RELATED_TO = "RELATED_TO"
    DESCRIBED_BY = "DESCRIBED_BY"
    MENTIONS = "MENTIONS"

    def __init__(self, config: Optional[KnowledgeGraphConfig] = None):
        """Initialize Neo4j store with configuration."""
        self.config = config or KnowledgeGraphConfig()
        self._driver: Optional[Driver] = None
        self._connected = False

    @property
    def driver(self) -> Driver:
        """Lazy-load the Neo4j driver."""
        if self._driver is None:
            self.connect()
        return self._driver

    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        if self._connected:
            return

        if not _NEO4J_AVAILABLE:
            raise ImportError(
                "neo4j package is not installed. "
                "Install it with: pip install neo4j>=5.0.0"
            )

        try:
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
                database=self.config.database
            )
            # Verify connection
            with self._driver.session() as session:
                session.run("MATCH (n) RETURN count(n) as count").single()
            self._connected = True
            logger.info(f"Connected to Neo4j at {self.config.uri}")
        except ServiceUnavailable as e:
            logger.error(f"Neo4j connection failed: {e}")
            raise
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Disconnected from Neo4j")

    def __enter__(self) -> "Neo4jStore":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # =========================================================================
    # Schema Management
    # =========================================================================

    def create_indexes(self) -> None:
        """Create necessary indexes for efficient querying."""
        indexes = [
            f"CREATE INDEX IF NOT EXISTS FOR (p:{self.PERSON}) ON (p.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (p:{self.PROJECT}) ON (p.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (p:{self.PROJECT}) ON (p.name)",
            f"CREATE INDEX IF NOT EXISTS FOR (p:{self.PROJECT}) ON (p.pushed_at)",
            f"CREATE INDEX IF NOT EXISTS FOR (s:{self.SKILL}) ON (s.name)",
            f"CREATE INDEX IF NOT EXISTS FOR (t:{self.TECHNOLOGY}) ON (t.name)",
            f"CREATE INDEX IF NOT EXISTS FOR (d:{self.DEPLOYMENT}) ON (d.url)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{self.NARRATIVE}) ON (n.id)",
        ]

        with self.driver.session() as session:
            for index_query in indexes:
                session.run(index_query)
        logger.info("Created Neo4j indexes")

    def create_constraints(self) -> None:
        """Create uniqueness constraints."""
        constraints = [
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (p:{self.PERSON}) REQUIRE p.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (p:{self.PROJECT}) REQUIRE p.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (s:{self.SKILL}) REQUIRE (s.name, s.category) IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (t:{self.TECHNOLOGY}) REQUIRE t.name IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{self.NARRATIVE}) REQUIRE n.id IS UNIQUE",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    # Constraint may already exist
                    logger.debug(f"Constraint note: {e}")
        logger.info("Created Neo4j constraints")

    def clear(self) -> None:
        """Clear all data from the graph (use with caution!)."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Cleared all data from Neo4j")

    # =========================================================================
    # Person Operations
    # =========================================================================

    def upsert_person(self, person_id: str, name: str, email: Optional[str] = None,
                      properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Person node. Returns node ID."""
        query = f"""
        MERGE (p:{self.PERSON} {{id: $person_id}})
        SET p.name = $name,
            p.email = $email,
            p.updated_at = datetime()
        """

        props = properties or {}
        for key, value in props.items():
            query += f", p.{key} = ${key}"

        params = {
            "person_id": person_id,
            "name": name,
            "email": email,
            **props
        }

        with self.driver.session() as session:
            result = session.run(query, params)
            result.consume()

        logger.debug(f"Upserted person: {person_id}")
        return person_id

    # =========================================================================
    # Project Operations
    # =========================================================================

    def upsert_project(self, project_id: str, name: str, source: str,
                       url: Optional[str] = None,
                       description: Optional[str] = None,
                       properties: Optional[Dict[str, Any]] = None) -> str:
        """
        Create or update a Project node.

        Args:
            project_id: Unique identifier (e.g., github:owner/repo)
            name: Project name
            source: Source type (github, vercel, cloudflare)
            url: Project URL
            description: Project description
            properties: Additional properties
        """
        query = f"""
        MERGE (p:{self.PROJECT} {{id: $project_id}})
        SET p.name = $name,
            p.source = $source,
            p.url = $url,
            p.description = $description,
            p.updated_at = datetime()
        """

        props = properties or {}
        for key, value in props.items():
            query += f", p.{key} = ${key}"

        params = {
            "project_id": project_id,
            "name": name,
            "source": source,
            "url": url,
            "description": description,
            **props
        }

        with self.driver.session() as session:
            result = session.run(query, params)
            result.consume()

        logger.debug(f"Upserted project: {project_id}")
        return project_id

    def link_person_to_project(self, person_id: str, project_id: str) -> None:
        """Create OWNS relationship between Person and Project."""
        query = f"""
        MATCH (person:{self.PERSON} {{id: $person_id}})
        MATCH (project:{self.PROJECT} {{id: $project_id}})
        MERGE (person)-[r:{self.OWNS}]->(project)
        SET r.created_at = datetime()
        """

        with self.driver.session() as session:
            session.run(query, {"person_id": person_id, "project_id": project_id})
        logger.debug(f"Linked person {person_id} to project {project_id}")

    # =========================================================================
    # Skill Operations
    # =========================================================================

    def upsert_skill(self, name: str, category: str,
                     confidence: float = 1.0,
                     properties: Optional[Dict[str, Any]] = None) -> str:
        """
        Create or update a Skill node.

        Args:
            name: Skill name (e.g., "Python", "React")
            category: Skill category (language, framework, tool, etc.)
            confidence: Confidence score (0-1)
            properties: Additional properties
        """
        query = f"""
        MERGE (s:{self.SKILL} {{name: $name, category: $category}})
        SET s.confidence = $confidence,
            s.updated_at = datetime()
        """

        props = properties or {}
        for key, value in props.items():
            query += f", s.{key} = ${key}"

        params = {
            "name": name,
            "category": category,
            "confidence": confidence,
            **props
        }

        with self.driver.session() as session:
            result = session.run(query, params)
            result.consume()

        return f"{name}:{category}"

    def link_skill_to_project(self, skill_name: str, skill_category: str,
                                project_id: str,
                                evidence: Optional[str] = None) -> None:
        """Create REQUIRES_SKILL relationship between Project and Skill."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MATCH (s:{self.SKILL} {{name: $skill_name, category: $skill_category}})
        MERGE (p)-[r:{self.REQUIRES_SKILL}]->(s)
        SET r.evidence = $evidence,
            r.created_at = datetime()
        """

        with self.driver.session() as session:
            session.run(query, {
                "project_id": project_id,
                "skill_name": skill_name,
                "skill_category": skill_category,
                "evidence": evidence
            })

    def link_person_to_skill(self, person_id: str, skill_name: str,
                             skill_category: str,
                             confidence: float = 1.0,
                             evidence: Optional[str] = None) -> None:
        """Create HAS_SKILL relationship between Person and Skill."""
        query = f"""
        MATCH (p:{self.PERSON} {{id: $person_id}})
        MATCH (s:{self.SKILL} {{name: $skill_name, category: $skill_category}})
        MERGE (p)-[r:{self.HAS_SKILL}]->(s)
        SET r.confidence = $confidence,
            r.evidence = $evidence,
            r.updated_at = datetime()
        """

        with self.driver.session() as session:
            session.run(query, {
                "person_id": person_id,
                "skill_name": skill_name,
                "skill_category": skill_category,
                "confidence": confidence,
                "evidence": evidence
            })

    # =========================================================================
    # Technology Operations
    # =========================================================================

    def upsert_technology(self, name: str, tech_type: str = "library",
                          properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Technology node."""
        query = f"""
        MERGE (t:{self.TECHNOLOGY} {{name: $name}})
        SET t.type = $tech_type,
            t.updated_at = datetime()
        """

        props = properties or {}
        for key, value in props.items():
            query += f", t.{key} = ${key}"

        params = {
            "name": name,
            "tech_type": tech_type,
            **props
        }

        with self.driver.session() as session:
            result = session.run(query, params)
            result.consume()

        return name

    def link_project_to_technology(self, project_id: str, technology_name: str,
                                   evidence_type: str = "dependency") -> None:
        """Create USES_TECHNOLOGY relationship."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MATCH (t:{self.TECHNOLOGY} {{name: $tech_name}})
        MERGE (p)-[r:{self.USES_TECHNOLOGY}]->(t)
        SET r.evidence_type = $evidence_type,
            r.created_at = datetime()
        """

        with self.driver.session() as session:
            session.run(query, {
                "project_id": project_id,
                "tech_name": technology_name,
                "evidence_type": evidence_type
            })

    # =========================================================================
    # Deployment Operations
    # =========================================================================

    def upsert_deployment(self, deployment_id: str, url: str,
                          platform: str, project_id: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Deployment node."""
        query = f"""
        MERGE (d:{self.DEPLOYMENT} {{id: $deployment_id}})
        SET d.url = $url,
            d.platform = $platform,
            d.updated_at = datetime()
        """

        props = properties or {}
        for key, value in props.items():
            query += f", d.{key} = ${key}"

        params = {
            "deployment_id": deployment_id,
            "url": url,
            "platform": platform,
            **props
        }

        with self.driver.session() as session:
            result = session.run(query, params)
            result.consume()

        # Link to project if provided
        if project_id:
            self.link_project_to_deployment(project_id, deployment_id)

        return deployment_id

    def link_project_to_deployment(self, project_id: str, deployment_id: str) -> None:
        """Create DEPLOYED_ON relationship."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MATCH (d:{self.DEPLOYMENT} {{id: $deployment_id}})
        MERGE (p)-[r:{self.DEPLOYED_ON}]->(d)
        SET r.created_at = datetime()
        """

        with self.driver.session() as session:
            session.run(query, {
                "project_id": project_id,
                "deployment_id": deployment_id
            })

    # =========================================================================
    # Narrative Operations
    # =========================================================================

    def upsert_narrative(self, narrative_id: str, text: str,
                         source_project_id: str,
                         period_start: Optional[str] = None,
                         period_end: Optional[str] = None,
                         properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Narrative node and link it to a Project."""
        query = f"""
        MERGE (n:{self.NARRATIVE} {{id: $narrative_id}})
        SET n.text = $text,
            n.period_start = $period_start,
            n.period_end = $period_end,
            n.updated_at = datetime()
        WITH n
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MERGE (p)-[r:{self.DESCRIBED_BY}]->(n)
        SET r.created_at = datetime()
        """

        props = properties or {}
        for key, value in props.items():
            query += f", n.{key} = ${key}"

        params = {
            "narrative_id": narrative_id,
            "text": text,
            "project_id": source_project_id,
            "period_start": period_start,
            "period_end": period_end,
            **props
        }

        with self.driver.session() as session:
            result = session.run(query, params)
            result.consume()

        logger.debug(f"Upserted narrative: {narrative_id}")
        return narrative_id

    def link_narrative_to_skill(self, narrative_id: str, skill_name: str,
                                skill_category: str) -> None:
        """Create MENTIONS relationship between Narrative and Skill."""
        query = f"""
        MATCH (n:{self.NARRATIVE} {{id: $narrative_id}})
        MATCH (s:{self.SKILL} {{name: $skill_name, category: $skill_category}})
        MERGE (n)-[r:{self.MENTIONS}]->(s)
        SET r.created_at = datetime()
        """

        with self.driver.session() as session:
            session.run(query, {
                "narrative_id": narrative_id,
                "skill_name": skill_name,
                "skill_category": skill_category
            })

    def link_narrative_to_technology(self, narrative_id: str, technology_name: str) -> None:
        """Create MENTIONS relationship between Narrative and Technology."""
        query = f"""
        MATCH (n:{self.NARRATIVE} {{id: $narrative_id}})
        MATCH (t:{self.TECHNOLOGY} {{name: $tech_name}})
        MERGE (n)-[r:{self.MENTIONS}]->(t)
        SET r.created_at = datetime()
        """

        with self.driver.session() as session:
            session.run(query, {
                "narrative_id": narrative_id,
                "tech_name": technology_name
            })

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_person_skills(self, person_id: str) -> List[Dict[str, Any]]:
        """Get all skills for a person with confidence scores."""
        query = f"""
        MATCH (p:{self.PERSON} {{id: $person_id}})
        -[r:{self.HAS_SKILL}]->(s:{self.SKILL})
        RETURN s.name as name,
               s.category as category,
               r.confidence as confidence,
               r.evidence as evidence
        ORDER BY r.confidence DESC
        """

        with self.driver.session() as session:
            result = session.run(query, {"person_id": person_id})
            return [record.data() for record in result]

    def get_project_skills(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all skills associated with a project."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        -[r:{self.REQUIRES_SKILL}]->(s:{self.SKILL})
        RETURN s.name as name,
               s.category as category,
               r.evidence as evidence
        """

        with self.driver.session() as session:
            result = session.run(query, {"project_id": project_id})
            return [record.data() for record in result]

    def search_skills(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search skills by name (case-insensitive substring match)."""
        query = f"""
        MATCH (s:{self.SKILL})
        WHERE toLower(s.name) CONTAINS toLower($query)
        RETURN s.name as name,
               s.category as category,
               s.confidence as confidence
        ORDER BY s.confidence DESC
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(query, {"query": query_text, "limit": limit})
            return [record.data() for record in result]

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        queries = {
            "persons": f"MATCH (p:{self.PERSON}) RETURN count(p) as count",
            "projects": f"MATCH (p:{self.PROJECT}) RETURN count(p) as count",
            "skills": f"MATCH (s:{self.SKILL}) RETURN count(s) as count",
            "technologies": f"MATCH (t:{self.TECHNOLOGY}) RETURN count(t) as count",
            "deployments": f"MATCH (d:{self.DEPLOYMENT}) RETURN count(d) as count",
            "narratives": f"MATCH (n:{self.NARRATIVE}) RETURN count(n) as count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) as count",
        }

        stats = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query).single()
                stats[key] = result["count"] if result else 0

        return stats
