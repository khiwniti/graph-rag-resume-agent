#!/usr/bin/env python3
"""
Demo script for Knowledge Graph.

Shows how to:
1. Connect to Neo4j
2. Add data
3. Query the graph
4. Use the RAG retriever
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph_store import Neo4jStore, KnowledgeGraphConfig, KnowledgeGraphBuilder
from app.extractors import SkillExtractor
from app.rag import HybridRetriever, Embedder

def print_header(text: str):
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def main():
    # Configuration
    config = KnowledgeGraphConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        database="neo4j",
    )

    print_header("Knowledge Graph Demo")
    print("This demo shows how to use the Neo4j knowledge graph.")

    # Initialize store
    print("\n1. Connecting to Neo4j...")
    store = Neo4jStore(config)

    try:
        store.connect()
        print("   ✓ Connected!")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("\n   Make sure Neo4j is running:")
        print("   docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \\")
        print("     -e NEO4J_AUTH=neo4j/password neo4j:5-community")
        return

    # Initialize schema
    print("\n2. Creating schema (indexes, constraints)...")
    store.create_indexes()
    store.create_constraints()
    print("   ✓ Schema ready!")

    # Add sample data
    print("\n3. Adding sample data...")

    # Person
    store.upsert_person(
        person_id="demo_user",
        name="Demo User",
        email="demo@example.com",
        properties={"title": "Full Stack Developer"}
    )

    # Projects
    store.upsert_project(
        project_id="github:demo-api",
        name="Demo API",
        source="github",
        url="https://github.com/demo/api",
        description="FastAPI backend"
    )

    store.upsert_project(
        project_id="github:demo-frontend",
        name="Demo Frontend",
        source="github",
        url="https://github.com/demo/frontend",
        description="React frontend"
    )

    # Skills
    skills_data = [
        ("Python", "language", 0.95),
        ("JavaScript", "language", 0.85),
        ("FastAPI", "framework", 0.90),
        ("React", "framework", 0.85),
        ("PostgreSQL", "database", 0.75),
        ("Docker", "tool", 0.80),
    ]

    for name, category, confidence in skills_data:
        store.upsert_skill(name, category, confidence)

    # Relationships
    store.link_person_to_project("demo_user", "github:demo-api")
    store.link_person_to_project("demo_user", "github:demo-frontend")

    for name, _, _ in skills_data:
        store.link_person_to_skill(
            "demo_user", name, "skill",
            confidence=0.8,
            evidence="Demo data"
        )

    # Link projects to skills
    store.link_skill_to_project("Python", "language", "github:demo-api", "import fastapi")
    store.link_skill_to_project("FastAPI", "framework", "github:demo-api", "from fastapi import FastAPI")
    store.link_skill_to_project("React", "framework", "github:demo-frontend", "import React")
    store.link_skill_to_project("JavaScript", "language", "github:demo-frontend", "import React")

    print("   ✓ Data added!")

    # Query skills
    print_header("Query: Skills for demo_user")
    skills = store.get_person_skills("demo_user")
    if skills:
        for skill in skills:
            print(f"   • {skill['name']} ({skill['category']}) - confidence: {skill['confidence']:.2f}")
    else:
        print("   No skills found.")

    # Search skills
    print_header("Search: 'python'")
    results = store.search_skills("python", limit=5)
    for result in results:
        print(f"   • {result['name']} ({result['category']}) - {result['confidence']:.2f}")

    # Get statistics
    print_header("Graph Statistics")
    stats = store.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Extract skills from code
    print_header("Extract Skills from Code")
    extractor = SkillExtractor()
    sample_code = """
from fastapi import FastAPI
import psycopg2
from typing import List

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
"""
    extracted = extractor.extract_from_file("demo.py", sample_code)
    print(f"   Found {len(extracted)} skills:")
    for skill in extracted:
        print(f"   • {skill.name} ({skill.category}) - confidence: {skill.confidence:.2f}")

    # RAG retrieval
    print_header("RAG Retrieval")
    embedder = Embedder()

    # Create vector store with sample data
    from app.rag.vector_store import VectorStore
    vector_store = VectorStore(dimension=384)

    # Add some embeddings
    sample_texts = [
        "Python programming with FastAPI",
        "React frontend development",
        "PostgreSQL database design",
        "Docker containerization",
    ]

    for text in sample_texts:
        embedding = embedder.embed(text)
        vector_store.add(embedding, {"text": text})

    # Search
    query = "What backend frameworks?"
    query_embedding = embedder.embed(query)
    results = vector_store.search(query_embedding, top_k=2)

    print(f"   Query: '{query}'")
    print("   Results:")
    for metadata, distance in results:
        print(f"   • {metadata.get('text', 'N/A')} (distance: {distance:.3f})")

    store.close()
    print("\n" + "=" * 60)
    print(" Demo complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
