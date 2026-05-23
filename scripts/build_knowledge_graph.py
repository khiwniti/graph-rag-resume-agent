#!/usr/bin/env python3
"""
Build Knowledge Graph from collected data.

This script orchestrates the full knowledge graph creation pipeline:
1. Collect data from GitHub, Vercel, Cloudflare
2. Extract skills and dependencies
3. Build Neo4j knowledge graph
4. Query and display results
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    GITHUB_TOKEN, VERCEL_TOKEN, CLOUDFLARE_TOKEN,
    CLOUDFLARE_ACCOUNT_ID, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
    DATA_DIR, GRAPH_DIR
)
from app.graph_store import Neo4jStore, KnowledgeGraphConfig, KnowledgeGraphBuilder
from app.extractors import SkillExtractor, DependencyParser, SourceAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_graph(store: Neo4jStore) -> None:
    """Create a sample knowledge graph for testing."""
    logger.info("Creating sample knowledge graph...")

    # Create indexes and constraints
    store.create_indexes()
    store.create_constraints()

    # Add person
    store.upsert_person(
        person_id="me",
        name="Developer",
        email="dev@example.com",
        properties={"title": "Software Engineer"}
    )

    # Add projects
    store.upsert_project(
        project_id="github:myproject",
        name="My Project",
        source="github",
        url="https://github.com/user/myproject",
        description="Sample project"
    )

    store.upsert_project(
        project_id="vercel:myapp",
        name="My App",
        source="vercel",
        url="https://myapp.vercel.app",
        description="Deployed app"
    )

    # Add skills
    store.upsert_skill("Python", "language", confidence=0.95)
    store.upsert_skill("FastAPI", "framework", confidence=0.85)
    store.upsert_skill("React", "framework", confidence=0.80)
    store.upsert_skill("Neo4j", "database", confidence=0.75)

    # Add technologies
    store.upsert_technology("fastapi", "framework")
    store.upsert_technology("react", "library")

    # Create relationships
    store.link_person_to_project("me", "github:myproject")
    store.link_person_to_project("me", "vercel:myapp")

    store.link_person_to_skill("me", "Python", "language", confidence=0.95,
                               evidence="Source code analysis")
    store.link_person_to_skill("me", "FastAPI", "framework", confidence=0.85,
                               evidence="Project dependencies")
    store.link_person_to_skill("me", "React", "framework", confidence=0.80,
                               evidence="Frontend code")

    store.link_project_to_technology("github:myproject", "fastapi")
    store.link_project_to_technology("vercel:myapp", "react")

    logger.info("Sample graph created successfully!")


def query_skills(store: Neo4jStore, person_id: str = "me") -> None:
    """Query and display skills for a person."""
    print("\n" + "=" * 60)
    print(f"Skills for {person_id}:")
    print("=" * 60)

    skills = store.get_person_skills(person_id)
    if not skills:
        print("No skills found. Run 'create_sample' first.")
        return

    for skill in skills:
        print(f"  - {skill['name']} ({skill['category']}): "
              f"confidence={skill['confidence']:.2f}")


def get_stats(store: Neo4jStore) -> None:
    """Display graph statistics."""
    stats = store.get_stats()
    print("\n" + "=" * 60)
    print("Knowledge Graph Statistics:")
    print("=" * 60)
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(
        description="Build and query Neo4j knowledge graph"
    )
    parser.add_argument(
        "action",
        choices=["create_sample", "query", "stats", "clear"],
        help="Action to perform"
    )
    parser.add_argument(
        "--neo4j-uri",
        default=NEO4J_URI,
        help="Neo4j URI (default: from config)"
    )
    parser.add_argument(
        "--neo4j-user",
        default=NEO4J_USER,
        help="Neo4j username (default: from config)"
    )
    parser.add_argument(
        "--neo4j-password",
        default=NEO4J_PASSWORD,
        help="Neo4j password (default: from config)"
    )
    parser.add_argument(
        "--person-id",
        default="me",
        help="Person ID for queries (default: me)"
    )

    args = parser.parse_args()

    # Create Neo4j configuration
    config = KnowledgeGraphConfig(
        uri=args.neo4j_uri or "bolt://localhost:7687",
        user=args.neo4j_user or "neo4j",
        password=args.neo4j_password or "",
        database=NEO4J_DATABASE or "neo4j",
    )

    # Connect to Neo4j
    try:
        store = Neo4jStore(config)
        store.connect()
        logger.info(f"Connected to Neo4j at {config.uri}")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.info("Make sure Neo4j is running and credentials are correct")
        sys.exit(1)

    try:
        if args.action == "create_sample":
            create_sample_graph(store)
            get_stats(store)

        elif args.action == "query":
            query_skills(store, args.person_id)

        elif args.action == "stats":
            get_stats(store)

        elif args.action == "clear":
            confirm = input("Are you sure you want to clear the graph? (yes/no): ")
            if confirm == "yes":
                store.clear()
                logger.info("Graph cleared")
            else:
                logger.info("Cancelled")

    finally:
        store.close()
        logger.info("Disconnected from Neo4j")


if __name__ == "__main__":
    main()
