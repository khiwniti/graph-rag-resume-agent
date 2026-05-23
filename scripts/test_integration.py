#!/usr/bin/env python3
"""
Integration test for the Graph RAG pipeline vector indexing path.
Tests chunking, embedding, and vector store indexing without needing Neo4j or real APIs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_vector_indexing():
    """Test that repo data can be chunked, embedded, and stored."""
    from app.rag.chunker import TextChunker
    from app.rag.embedder import Embedder
    from app.rag.vector_store import VectorStore

    print("\n" + "=" * 60)
    print("Integration Test: Vector Indexing")
    print("=" * 60)

    chunker = TextChunker(chunk_size=200, overlap=20)
    embedder = Embedder()
    store = VectorStore(dimension=384, index_path=None)  # In-memory only

    # Simulate a repo narrative
    repo_text = """Project: Graph RAG Resume Agent

Description: A knowledge graph system that ingests GitHub, Vercel, and Cloudflare data.

Languages: Python, JavaScript
Skills: Neo4j, FastAPI, FAISS, Sentence Transformers

README: This project builds a career-spanning knowledge graph using RAG techniques.
It clones repositories, extracts skills, generates narratives via LLM, and indexes everything.
"""

    chunks = chunker.chunk(repo_text, source="test:graph-rag")
    print(f"\n📄 Chunked into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks[:3]):
        print(f"   Chunk {i}: {chunk.text[:80]}...")

    texts = [c.text for c in chunks]
    embeddings = embedder.embed_batch(texts)
    print(f"\n🔢 Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")

    for emb, chunk in zip(embeddings, chunks):
        doc_id = store.add(emb, {
            "type": "project",
            "project_id": "test:graph-rag",
            "source": "github",
            "chunk_id": chunk.chunk_id,
        })
        print(f"   Stored chunk as doc_id={doc_id}")

    # Search
    query = "What is the RAG system about?"
    query_emb = embedder.embed(query)
    results = store.search(query_emb, top_k=3)
    print(f"\n🔍 Query: '{query}'")
    print(f"   Found {len(results)} matches")
    for meta, dist in results:
        print(f"   - {meta.get('chunk_id', 'unknown')} (distance={dist:.3f})")

    print("\n✅ Vector indexing integration test passed!")
    return True


def test_pipeline_structural():
    """Test that the pipeline can be instantiated and has all required components."""
    from app.pipeline import GraphRAGPipeline

    print("\n" + "=" * 60)
    print("Integration Test: Pipeline Structure")
    print("=" * 60)

    pipeline = GraphRAGPipeline(max_repos=3)

    assert pipeline.github_collector is not None
    assert pipeline.vercel_collector is not None
    assert pipeline.cloudflare_collector is not None
    assert pipeline.narrative_builder is not None
    assert pipeline.chunker is not None
    assert pipeline.embedder is not None
    assert pipeline.vector_store is not None

    print("\n✅ Pipeline has all required components")
    print("   - GitHub collector")
    print("   - Vercel collector")
    print("   - Cloudflare collector")
    print("   - Narrative builder")
    print("   - Text chunker")
    print("   - Embedder")
    print("   - Vector store")
    return True


def main():
    print("\n" + "=" * 60)
    print("Graph RAG Resume Agent - Integration Tests")
    print("=" * 60)

    ok = True
    ok &= test_vector_indexing()
    ok &= test_pipeline_structural()

    print("\n" + "=" * 60)
    if ok:
        print("✅ All integration tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
