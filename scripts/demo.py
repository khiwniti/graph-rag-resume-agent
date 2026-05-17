#!/usr/bin/env python3
"""
Demo script - Shows the Graph RAG Resume Agent components working.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("\n" + "=" * 70)
print("Graph RAG Resume Agent - Component Demo")
print("=" * 70)

# Demo 1: Configuration
print("\n1. ✅ Configuration Loaded")
from app.config import MAX_REPOS, MAX_FILES_PER_REPO
print(f"   Max repos: {MAX_REPOS}, Max files per repo: {MAX_FILES_PER_REPO}")

# Demo 2: Graph Builder
print("\n2. ✅ Knowledge Graph Builder")
from app.graph.builder import GraphBuilder
builder = GraphBuilder()
builder.add_node("person", "user", {"name": "Developer"})
builder.add_node("skill", "Python", {"confidence": 0.95})
builder.add_node("skill", "FastAPI", {"confidence": 0.90})
builder.add_edge("user", "Python", "SKILLED_IN")
builder.add_edge("user", "FastAPI", "SKILLED_IN")
print(f"   Created graph: {builder.graph.number_of_nodes()} nodes, {builder.graph.number_of_edges()} edges")

# Demo 3: Skill Extractor
print("\n3. ✅ Skill Extractor")
from app.extractors.skill_extractor import SkillExtractor
extractor = SkillExtractor()
skills = extractor.extract_from_text("Using Python with FastAPI and React")
print(f"   Extracted {len(skills)} skills: {[s['name'] for s in skills]}")

# Demo 4: Text Chunker
print("\n4. ✅ RAG Text Chunker")
from app.rag.chunker import TextChunker
chunker = TextChunker()
chunks = chunker.chunk("FastAPI is a modern web framework for building APIs with Python.")
print(f"   Created {len(chunks)} chunk(s)")

# Demo 5: Résumé Agent
print("\n5. ✅ Résumé Agent")
from app.agent.resume_agent import ResumeAgent
agent = ResumeAgent()
print(f"   Agent initialized successfully")

# Demo 6: FastAPI App
print("\n6. ✅ FastAPI Application")
from app.main import app
print(f"   API with {len(app.routes)} endpoints registered")
print(f"   Endpoints: {[r.path for r in app.routes if hasattr(r, 'path')][:5]}...")

print("\n" + "=" * 70)
print("✅ All Components Working!")
print("=" * 70)
print("\nNext steps:")
print("1. Run collection: python scripts/run_collection.py")
print("2. Start server: python scripts/run_server.py")
print("3. Query: curl -X POST http://localhost:8000/query -d '{\"question\": \"Skills?\"}'")
