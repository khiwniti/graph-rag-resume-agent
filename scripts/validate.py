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
    
    # Test config
    print("\n1. Testing Configuration...")
    try:
        from app.config import GITHUB_TOKEN, MAX_REPOS, DATA_DIR
        print(f"   ✅ Config constants loaded")
    except Exception as e:
        print(f"   ❌ Config failed: {e}")
        return 1
    
    # Test all modules
    modules = [
        ("Pipeline", "app.pipeline", "GraphRAGPipeline"),
        ("GitHub Collector", "app.collectors.github_collector", "GitHubCollector"),
        ("Vercel Collector", "app.collectors.vercel_collector", "VercelCollector"),
        ("Cloudflare Collector", "app.collectors.cloudflare_collector", "CloudflareCollector"),
        ("Conversation Collector", "app.collectors.conversation_collector", "ConversationCollector"),
        ("Code Fetcher", "app.collectors.code_fetcher", "CodeFetcher"),
        ("GitHub Normalizer", "app.normalizers.github_normalizer", "GitHubNormalizer"),
        ("Vercel Normalizer", "app.normalizers.vercel_normalizer", "VercelNormalizer"),
        ("Cloudflare Normalizer", "app.normalizers.cloudflare_normalizer", "CloudflareNormalizer"),
        ("Conversation Normalizer", "app.normalizers.conversation_normalizer", "ConversationNormalizer"),
        ("Dependency Parser", "app.extractors.dependency_parser", "DependencyParser"),
        ("Source Analyzer", "app.extractors.source_analyzer", "SourceAnalyzer"),
        ("Skill Extractor", "app.extractors.skill_extractor", "SkillExtractor"),
        ("Evidence Ranker", "app.extractors.evidence_ranker", "EvidenceRanker"),
        ("Graph Builder", "app.graph.builder", "GraphBuilder"),
        ("Graph Serializer", "app.graph.serializer", "GraphSerializer"),
        ("Graph Querier", "app.graph.query", "GraphQuerier"),
        ("Text Chunker", "app.rag.chunker", "TextChunker"),
        ("Embedder", "app.rag.embedder", "Embedder"),
        ("Vector Store", "app.rag.vector_store", "VectorStore"),
        ("Retriever", "app.rag.retriever", "Retriever"),
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
    
    # Test schemas
    print("\n4. Testing Schemas...")
    try:
        from app.models.schemas import RepositorySnapshot, SkillEvidence
        print(f"   ✅ Schemas")
    except Exception as e:
        print(f"   ❌ Schemas: {e}")
        failed.append("Schemas")
    
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
        print("4. Query: curl -X POST http://localhost:8000/query -d '{\"question\": \"What are my skills?\"}'")
        return 0


if __name__ == "__main__":
    sys.exit(main())
