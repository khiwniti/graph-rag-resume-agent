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
    - File: Source code files within a project
    - Module: Logical module/directory grouping
    - Function: Function/method definitions
    - Class: Class/struct definitions
    - Route: API route/endpoint definitions
    - Config: Configuration entries (env vars, build settings)
    - Domain: DNS domains

    Relationships:
    - (:Person)-[:OWNS]->(:Project)
    - (:Person)-[:HAS_SKILL]->(:Skill)
    - (:Project)-[:USES_TECHNOLOGY]->(:Technology)
    - (:Project)-[:DEPLOYED_ON]->(:Deployment)
    - (:Skill)<-[:REQUIRES_SKILL]-(:Project)
    - (:Project)-[:DESCRIBED_BY]->(:Narrative)
    - (:Narrative)-[:MENTIONS]->(:Skill|:Technology)
    - (:Project)-[:CONTAINS_FILE]->(:File)
    - (:File)-[:CONTAINS]->(:Function|:Class|:Module)
    - (:Class)-[:CONTAINS_METHOD]->(:Function)
    - (:Function)-[:CALLS]->(:Function)
    - (:Class)-[:INHERITS]->(:Class)
    - (:File)-[:IMPORTS]->(:File|:Module)
    - (:Project)-[:EXPOSES]->(:Route)
    - (:Route)-[:HANDLED_BY]->(:Function)
    - (:Project)-[:CONFIGURES]->(:Config)
    - (:Project)-[:HAS_DOMAIN]->(:Domain)
    - (:File)-[:DOCUMENTED_BY]->(:Narrative)  # README sections → source files
    """

    # Node labels
    PERSON = "Person"
    PROJECT = "Project"
    SKILL = "Skill"
    TECHNOLOGY = "Technology"
    DEPLOYMENT = "Deployment"
    NARRATIVE = "Narrative"
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    MODULE = "Module"
    ROUTE = "Route"
    CONFIG = "Config"
    DOMAIN = "Domain"

    # Relationship types
    OWNS = "OWNS"
    HAS_SKILL = "HAS_SKILL"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    DEPLOYED_ON = "DEPLOYED_ON"
    REQUIRES_SKILL = "REQUIRES_SKILL"
    RELATED_TO = "RELATED_TO"
    DESCRIBED_BY = "DESCRIBED_BY"
    MENTIONS = "MENTIONS"
    CONTAINS_FILE = "CONTAINS_FILE"
    CONTAINS = "CONTAINS"
    CONTAINS_METHOD = "CONTAINS_METHOD"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPORTS = "IMPORTS"
    EXPOSES = "EXPOSES"
    HANDLED_BY = "HANDLED_BY"
    CONFIGURES = "CONFIGURES"
    HAS_DOMAIN = "HAS_DOMAIN"
    DOCUMENTED_BY = "DOCUMENTED_BY"

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
            f"CREATE INDEX IF NOT EXISTS FOR (f:{self.FILE}) ON (f.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (f:{self.FILE}) ON (f.path)",
            f"CREATE INDEX IF NOT EXISTS FOR (fn:{self.FUNCTION}) ON (fn.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (c:{self.CLASS}) ON (c.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (m:{self.MODULE}) ON (m.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (r:{self.ROUTE}) ON (r.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (cf:{self.CONFIG}) ON (cf.id)",
            f"CREATE INDEX IF NOT EXISTS FOR (dm:{self.DOMAIN}) ON (dm.name)",
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
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (f:{self.FILE}) REQUIRE f.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (fn:{self.FUNCTION}) REQUIRE fn.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (c:{self.CLASS}) REQUIRE c.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (m:{self.MODULE}) REQUIRE m.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (r:{self.ROUTE}) REQUIRE r.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (cf:{self.CONFIG}) REQUIRE cf.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (dm:{self.DOMAIN}) REQUIRE dm.name IS UNIQUE",
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
    # File Operations
    # =========================================================================

    def upsert_file(self, file_id: str, path: str, project_id: Optional[str] = None,
                    language: str = "", properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a File node."""
        query = f"""
        MERGE (f:{self.FILE} {{id: $file_id}})
        SET f.path = $path,
            f.language = $language,
            f.updated_at = datetime()
        """
        props = properties or {}
        for key, value in props.items():
            query += f", f.{key} = ${key}"

        with self.driver.session() as session:
            session.run(query, {
                "file_id": file_id, "path": path, "language": language, **props
            })

        if project_id:
            self.link_project_to_file(project_id, file_id)
        return file_id

    def link_project_to_file(self, project_id: str, file_id: str) -> None:
        """Create CONTAINS_FILE relationship."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MATCH (f:{self.FILE} {{id: $file_id}})
        MERGE (p)-[r:{self.CONTAINS_FILE}]->(f)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"project_id": project_id, "file_id": file_id})

    # =========================================================================
    # Function Operations
    # =========================================================================

    def upsert_function(self, function_id: str, name: str, file_id: str,
                        signature: str = "", line_start: int = 0, line_end: int = 0,
                        properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Function node and link to its File."""
        query = f"""
        MERGE (fn:{self.FUNCTION} {{id: $function_id}})
        SET fn.name = $name,
            fn.signature = $signature,
            fn.line_start = $line_start,
            fn.line_end = $line_end,
            fn.updated_at = datetime()
        """
        props = properties or {}
        for key, value in props.items():
            query += f", fn.{key} = ${key}"

        with self.driver.session() as session:
            session.run(query, {
                "function_id": function_id, "name": name, "signature": signature,
                "line_start": line_start, "line_end": line_end, **props
            })

        if file_id:
            self.link_file_to_function(file_id, function_id)
        return function_id

    def link_file_to_function(self, file_id: str, function_id: str) -> None:
        """Create CONTAINS relationship from File to Function."""
        query = f"""
        MATCH (f:{self.FILE} {{id: $file_id}})
        MATCH (fn:{self.FUNCTION} {{id: $function_id}})
        MERGE (f)-[r:{self.CONTAINS}]->(fn)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"file_id": file_id, "function_id": function_id})

    def link_function_call(self, caller_id: str, callee_id: str) -> None:
        """Create CALLS relationship between two Function nodes."""
        query = f"""
        MATCH (caller:{self.FUNCTION} {{id: $caller_id}})
        MATCH (callee:{self.FUNCTION} {{id: $callee_id}})
        MERGE (caller)-[r:{self.CALLS}]->(callee)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"caller_id": caller_id, "callee_id": callee_id})

    # =========================================================================
    # Class Operations
    # =========================================================================

    def upsert_class(self, class_id: str, name: str, file_id: str,
                     bases: Optional[List[str]] = None,
                     line_start: int = 0, line_end: int = 0,
                     properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Class node and link to its File."""
        query = f"""
        MERGE (c:{self.CLASS} {{id: $class_id}})
        SET c.name = $name,
            c.bases = $bases,
            c.line_start = $line_start,
            c.line_end = $line_end,
            c.updated_at = datetime()
        """
        props = properties or {}
        for key, value in props.items():
            query += f", c.{key} = ${key}"

        bases_list = bases or []
        with self.driver.session() as session:
            session.run(query, {
                "class_id": class_id, "name": name, "bases": bases_list,
                "line_start": line_start, "line_end": line_end, **props
            })

        if file_id:
            self.link_file_to_class(file_id, class_id)
        return class_id

    def link_file_to_class(self, file_id: str, class_id: str) -> None:
        """Create CONTAINS relationship from File to Class."""
        query = f"""
        MATCH (f:{self.FILE} {{id: $file_id}})
        MATCH (c:{self.CLASS} {{id: $class_id}})
        MERGE (f)-[r:{self.CONTAINS}]->(c)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"file_id": file_id, "class_id": class_id})

    def link_class_to_method(self, class_id: str, function_id: str) -> None:
        """Create CONTAINS_METHOD relationship from Class to Function."""
        query = f"""
        MATCH (c:{self.CLASS} {{id: $class_id}})
        MATCH (fn:{self.FUNCTION} {{id: $function_id}})
        MERGE (c)-[r:{self.CONTAINS_METHOD}]->(fn)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"class_id": class_id, "function_id": function_id})

    def link_class_inheritance(self, child_class_id: str, parent_class_id: str) -> None:
        """Create INHERITS relationship from child Class to parent Class."""
        query = f"""
        MATCH (child:{self.CLASS} {{id: $child_id}})
        MATCH (parent:{self.CLASS} {{id: $parent_id}})
        MERGE (child)-[r:{self.INHERITS}]->(parent)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"child_id": child_class_id, "parent_id": parent_class_id})

    # =========================================================================
    # Module Operations
    # =========================================================================

    def upsert_module(self, module_id: str, name: str,
                      properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Module node (directory/package grouping)."""
        query = f"""
        MERGE (m:{self.MODULE} {{id: $module_id}})
        SET m.name = $name,
            m.updated_at = datetime()
        """
        props = properties or {}
        for key, value in props.items():
            query += f", m.{key} = ${key}"

        with self.driver.session() as session:
            session.run(query, {"module_id": module_id, "name": name, **props})
        return module_id

    def link_file_to_module(self, file_id: str, module_id: str) -> None:
        """Create CONTAINS relationship from Module to File."""
        query = f"""
        MATCH (m:{self.MODULE} {{id: $module_id}})
        MATCH (f:{self.FILE} {{id: $file_id}})
        MERGE (m)-[r:{self.CONTAINS}]->(f)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"file_id": file_id, "module_id": module_id})

    # =========================================================================
    # Import / Cross-file Dependency Operations
    # =========================================================================

    def link_file_import(self, file_id: str, imported_file_id: str) -> None:
        """Create IMPORTS relationship between two File nodes."""
        query = f"""
        MATCH (f:{self.FILE} {{id: $file_id}})
        MATCH (imported:{self.FILE} {{id: $imported_id}})
        MERGE (f)-[r:{self.IMPORTS}]->(imported)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"file_id": file_id, "imported_id": imported_file_id})

    # =========================================================================
    # Route Operations
    # =========================================================================

    def upsert_route(self, route_id: str, method: str, path: str,
                     handler_function_id: Optional[str] = None,
                     properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Route node (API endpoint)."""
        query = f"""
        MERGE (r:{self.ROUTE} {{id: $route_id}})
        SET r.method = $method,
            r.path = $path,
            r.updated_at = datetime()
        """
        props = properties or {}
        for key, value in props.items():
            query += f", r.{key} = ${key}"

        with self.driver.session() as session:
            session.run(query, {
                "route_id": route_id, "method": method, "path": path, **props
            })

        if handler_function_id:
            self.link_route_to_function(route_id, handler_function_id)
        return route_id

    def link_project_to_route(self, project_id: str, route_id: str) -> None:
        """Create EXPOSES relationship from Project to Route."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MATCH (r:{self.ROUTE} {{id: $route_id}})
        MERGE (p)-[rel:{self.EXPOSES}]->(r)
        SET rel.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"project_id": project_id, "route_id": route_id})

    def link_route_to_function(self, route_id: str, function_id: str) -> None:
        """Create HANDLED_BY relationship from Route to Function."""
        query = f"""
        MATCH (r:{self.ROUTE} {{id: $route_id}})
        MATCH (fn:{self.FUNCTION} {{id: $function_id}})
        MERGE (r)-[rel:{self.HANDLED_BY}]->(fn)
        SET rel.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"route_id": route_id, "function_id": function_id})

    # =========================================================================
    # Config Operations
    # =========================================================================

    def upsert_config(self, config_id: str, key: str, value: str = "",
                      config_type: str = "env_var",
                      properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Config node (env var, build setting, etc.)."""
        query = f"""
        MERGE (cf:{self.CONFIG} {{id: $config_id}})
        SET cf.key = $key,
            cf.value = $value,
            cf.config_type = $config_type,
            cf.updated_at = datetime()
        """
        props = properties or {}
        for key_p, value_p in props.items():
            query += f", cf.{key_p} = ${key_p}"

        with self.driver.session() as session:
            session.run(query, {
                "config_id": config_id, "key": key, "value": value,
                "config_type": config_type, **props
            })
        return config_id

    def link_project_to_config(self, project_id: str, config_id: str) -> None:
        """Create CONFIGURES relationship from Project to Config."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MATCH (cf:{self.CONFIG} {{id: $config_id}})
        MERGE (p)-[r:{self.CONFIGURES}]->(cf)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"project_id": project_id, "config_id": config_id})

    # =========================================================================
    # Domain Operations
    # =========================================================================

    def upsert_domain(self, domain_name: str,
                      properties: Optional[Dict[str, Any]] = None) -> str:
        """Create or update a Domain node."""
        query = f"""
        MERGE (d:{self.DOMAIN} {{name: $domain_name}})
        SET d.updated_at = datetime()
        """
        props = properties or {}
        for key, value in props.items():
            query += f", d.{key} = ${key}"

        with self.driver.session() as session:
            session.run(query, {"domain_name": domain_name, **props})
        return domain_name

    def link_project_to_domain(self, project_id: str, domain_name: str) -> None:
        """Create HAS_DOMAIN relationship from Project to Domain."""
        query = f"""
        MATCH (p:{self.PROJECT} {{id: $project_id}})
        MATCH (d:{self.DOMAIN} {{name: $domain_name}})
        MERGE (p)-[r:{self.HAS_DOMAIN}]->(d)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"project_id": project_id, "domain_name": domain_name})

    # =========================================================================
    # Documentation Link Operations
    # =========================================================================

    def link_file_to_documentation(self, file_id: str, narrative_id: str) -> None:
        """Create DOCUMENTED_BY relationship from File to Narrative (README section)."""
        query = f"""
        MATCH (f:{self.FILE} {{id: $file_id}})
        MATCH (n:{self.NARRATIVE} {{id: $narrative_id}})
        MERGE (f)-[r:{self.DOCUMENTED_BY}]->(n)
        SET r.created_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, {"file_id": file_id, "narrative_id": narrative_id})

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
            "files": f"MATCH (f:{self.FILE}) RETURN count(f) as count",
            "functions": f"MATCH (fn:{self.FUNCTION}) RETURN count(fn) as count",
            "classes": f"MATCH (c:{self.CLASS}) RETURN count(c) as count",
            "modules": f"MATCH (m:{self.MODULE}) RETURN count(m) as count",
            "routes": f"MATCH (r:{self.ROUTE}) RETURN count(r) as count",
            "configs": f"MATCH (cf:{self.CONFIG}) RETURN count(cf) as count",
            "domains": f"MATCH (d:{self.DOMAIN}) RETURN count(d) as count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) as count",
        }

        stats = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query).single()
                stats[key] = result["count"] if result else 0

        return stats
