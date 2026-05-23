#!/usr/bin/env python3
"""
Simple validation script - checks that all modules can be imported.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Run import validation."""
    print("\n" + "=" * 60)
    print("Graph RAG Resume Agent - Import Validation")
    print("=" * 60)

    # Test config (load directly to avoid app/__init__ cascading imports)
    print("\n1. Testing Configuration...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", str(Path(__file__).parent.parent / "app" / "config.py"))
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        _ = config.GITHUB_TOKEN, config.MAX_REPOS, config.DATA_DIR
        print(f"   ✅ Config constants loaded")
    except Exception as e:
        print(f"   ❌ Config failed: {e}")
        return 1

    # Test all modules that actually exist
    modules = [
        ("Pipeline", "app.pipeline", "GraphRAGPipeline"),
        ("GitHub Collector", "app.collectors.github_collector", "GitHubCollector"),
        ("Vercel Collector", "app.collectors.vercel_collector", "VercelCollector"),
        ("Cloudflare Collector", "app.collectors.cloudflare_collector", "CloudflareCollector"),
        ("Code Fetcher", "app.collectors.code_fetcher", "CodeFetcher"),
        ("Dependency Parser", "app.extractors.dependency_parser", "DependencyParser"),
        ("Source Analyzer", "app.extractors.source_analyzer", "SourceAnalyzer"),
        ("Skill Extractor", "app.extractors.skill_extractor", "SkillExtractor"),
        ("Narrative Builder", "app.extractors.narrative_builder", "NarrativeBuilder"),
        ("Neo4j Store", "app.graph_store.neo4j_store", "Neo4jStore"),
        ("Graph Builder", "app.graph_store.builder", "KnowledgeGraphBuilder"),
        ("Text Chunker", "app.rag.chunker", "TextChunker"),
        ("Embedder", "app.rag.embedder", "Embedder"),
        ("Vector Store", "app.rag.vector_store", "VectorStore"),
        ("Hybrid Retriever", "app.rag.retriever", "HybridRetriever"),
        ("Resume Agent", "app.agent.resume_agent", "ResumeAgent"),
    ]

    print("\n2. Testing Module Imports...")
    failed = []
    for name, module, class_name in modules:
        try:
            exec(f"from {module} import {class_name}")
            print(f"   ✅ {name}")
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            failed.append(name)

    # Test FastAPI app
    print("\n3. Testing FastAPI App...")
    try:
        from app.main import app
        print(f"   ✅ FastAPI App")
    except Exception as e:
        print(f"   ❌ FastAPI App: {e}")
        failed.append("FastAPI App")

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    if failed:
        print(f"\n❌ {len(failed)} module(s) failed to import:")
        for name in failed:
            print(f"   - {name}")
        print("\n💡 This is likely due to missing dependencies.")
        print("   Run: pip install -r requirements.txt")
        return 1
    else:
        print("\n✅ All modules imported successfully!")
        print("\n🎉 The Graph RAG Resume Agent is ready!")
        print("\nNext steps:")
        print("1. Add your API tokens to .env")
        print("2. Run: python scripts/run_collection.py")
        print("3. Run: python scripts/run_server.py")
        print('4. Query: curl -X POST http://localhost:8000/query -d \'{"question": "What are my skills?"}\'')
        return 0


if __name__ == "__main__":
    sys.exit(main())
