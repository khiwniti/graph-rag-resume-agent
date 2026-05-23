#!/usr/bin/env python3
"""
Setup script for Neo4j knowledge graph.

This script:
1. Checks if Neo4j is running
2. Creates indexes and constraints
3. Optionally loads sample data
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
from app.graph_store import Neo4jStore, KnowledgeGraphConfig, KnowledgeGraphBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_neo4j_running(uri: str) -> bool:
    """Check if Neo4j is running and accessible."""
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable

    try:
        driver = GraphDatabase(uri, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("RETURN 1").single()
        driver.close()
        return True
    except ServiceUnavailable as e:
        logger.warning(f"Neo4j not reachable: {e}")
        return False
    except Exception as e:
        logger.warning(f"Error connecting to Neo4j: {e}")
        return False


def setup_schema(config: KnowledgeGraphConfig) -> None:
    """Create indexes and constraints."""
    logger.info("Setting up Neo4j schema...")

    store = Neo4jStore(config)
    store.connect()

    try:
        store.create_indexes()
        store.create_constraints()
        logger.info("Schema setup complete!")
    except Exception as e:
        logger.error(f"Schema setup failed: {e}")
        raise
    finally:
        store.close()


def load_sample_data(config: KnowledgeGraphConfig) -> None:
    """Load sample data into the graph."""
    logger.info("Loading sample data...")

    store = Neo4jStore(config)
    store.connect()

    try:
        # Create person
        store.upsert_person(
            person_id="me",
            name="Developer",
            email="dev@example.com",
            properties={"title": "Software Engineer"}
        )

        # Create projects
        projects = [
            ("github:graph-rag", "Graph RAG Resume Agent", "github",
             "https://github.com/user/graph-rag-resume-agent", "Knowledge graph for resume RAG"),
            ("vercel:myapp", "My Web App", "vercel",
             "https://myapp.vercel.app", "Deployed web application"),
            ("cloudflare:worker", "Cloudflare Worker", "cloudflare",
             "https://worker.example.workers.dev", "Edge function"),
        ]

        for proj_id, name, source, url, desc in projects:
            store.upsert_project(
                project_id=proj_id,
                name=name,
                source=source,
                url=url,
                description=desc
            )
            store.link_person_to_project("me", proj_id)

        # Create skills
        skills = [
            ("Python", "language", 0.95),
            ("JavaScript", "language", 0.85),
            ("TypeScript", "language", 0.80),
            ("FastAPI", "framework", 0.90),
            ("React", "framework", 0.85),
            ("Neo4j", "database", 0.75),
            ("PostgreSQL", "database", 0.70),
            ("Docker", "tool", 0.80),
            ("Git", "tool", 0.90),
            ("AWS", "cloud", 0.65),
        ]

        for skill_name, category, confidence in skills:
            store.upsert_skill(skill_name, category, confidence)
            store.link_person_to_skill(
                "me", skill_name, category, confidence,
                evidence="Sample data"
            )

        # Create technologies
        techs = ["fastapi", "react", "neo4j", "postgresql", "docker"]
        for tech in techs:
            store.upsert_technology(tech)

        # Link projects to technologies
        store.link_project_to_technology("github:graph-rag", "fastapi")
        store.link_project_to_technology("github:graph-rag", "neo4j")
        store.link_project_to_technology("vercel:myapp", "react")

        logger.info("Sample data loaded successfully!")

        # Show stats
        stats = store.get_stats()
        print("\n" + "=" * 50)
        print("Sample Graph Statistics:")
        print("=" * 50)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 50)

    except Exception as e:
        logger.error(f"Failed to load sample data: {e}")
        raise
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description="Setup Neo4j knowledge graph")
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip Neo4j running check"
    )
    parser.add_argument(
        "--no-sample",
        action="store_true",
        help="Skip loading sample data"
    )
    parser.add_argument(
        "--uri",
        default=NEO4J_URI,
        help="Neo4j URI"
    )
    parser.add_argument(
        "--user",
        default=NEO4J_USER,
        help="Neo4j username"
    )
    parser.add_argument(
        "--password",
        default=NEO4J_PASSWORD,
        help="Neo4j password"
    )

    args = parser.parse_args()

    # Configure
    config = KnowledgeGraphConfig(
        uri=args.uri or "bolt://localhost:7687",
        user=args.user or "neo4j",
        password=args.password or "password",
        database=NEO4J_DATABASE or "neo4j",
    )

    # Check if Neo4j is running
    if not args.skip_check:
        logger.info(f"Checking Neo4j connection at {config.uri}...")
        if not check_neo4j_running(config.uri):
            print("\n" + "=" * 60)
            print("Neo4j is not running or not accessible.")
            print("\nTo start Neo4j with Docker:")
            print("  docker run -d --name neo4j \\")
            print("    -p 7474:7474 -p 7687:7687 \\")
            print("    -e NEO4J_AUTH=neo4j/password \\")
            print("    neo4j:5-community")
            print("\nOr set your Neo4j credentials in .env")
            print("=" * 60)

            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(0)

    # Setup schema
    setup_schema(config)

    # Load sample data
    if not args.no_sample:
        load_sample_data(config)

    logger.info("\nSetup complete! You can now:")
    logger.info("  - Query: python scripts/build_knowledge_graph.py query")
    logger.info("  - Stats: python scripts/build_knowledge_graph.py stats")
    logger.info("  - API:   python scripts/run_server.py")


if __name__ == "__main__":
    main()
