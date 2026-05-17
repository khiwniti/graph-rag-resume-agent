#!/usr/bin/env python3
"""
Build embeddings from collected data for the Graph RAG Resume Agent.
This script loads the knowledge graph and creates vector embeddings for RAG.
"""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag.vector_store import VectorStore
from app.rag.embedder import Embedder
from app.rag.chunker import TextChunker
from app.graph.builder import GraphBuilder

def main():
    print("\n" + "="*70)
    print("Building Embeddings from Knowledge Graph")
    print("="*70)
    
    # Load the knowledge graph
    graph_path = Path("data/graph/knowledge_graph.json")
    if not graph_path.exists():
        print("❌ Error: Knowledge graph not found. Run build_graph_simple.py first.")
        sys.exit(1)
    
    print(f"\n📂 Loading graph from: {graph_path}")
    builder = GraphBuilder()
    builder.load_from_json(str(graph_path))
    
    # Extract text chunks from graph
    print("\n📝 Extracting text chunks from graph...")
    chunks = []
    
    # Get all nodes from graph
    for node in builder.graph.nodes(data=True):
        node_id, node_data = node
        if not node_data or not isinstance(node_data, dict):
            continue
        
        # Get properties
        props = node_data.get('properties', {})
        node_type = props.get('type', node_data.get('type', 'unknown'))
        
        # Extract text content based on node type
        text_parts = []
        metadata = {"node_id": node_id, "type": node_type}
        
        # Person node
        if node_type == "person" or "person" in node_id:
            text_parts.append(f"Person: {props.get('name', props.get('login', 'Unknown'))}")
            if 'bio' in props:
                text_parts.append(props['bio'])
        
        # Repository node
        elif node_type == "repository" or "repo" in node_id:
            repo_name = props.get('name', node_id)
            text_parts.append(f"Repository: {repo_name}")
            if 'description' in props and props['description']:
                text_parts.append(props['description'])
            if 'language' in props and props['language']:
                text_parts.append(f"Language: {props['language']}")
            metadata["repo_name"] = repo_name
            metadata["source"] = "github"
        
        # Project node
        elif node_type == "project" or "project" in node_id:
            project_name = props.get('name', node_id)
            text_parts.append(f"Project: {project_name}")
            if 'framework' in props and props['framework']:
                text_parts.append(f"Framework: {props['framework']}")
            if 'description' in props and props['description']:
                text_parts.append(props['description'])
            metadata["project_name"] = project_name
            metadata["source"] = props.get('platform', 'vercel')
        
        # Skill node
        elif node_type == "skill" or "skill" in node_id:
            skill_name = props.get('name', node_id.replace('skill:', ''))
            text_parts.append(f"Skill: {skill_name}")
            if 'category' in props:
                text_parts.append(f"Category: {props['category']}")
            metadata["skill_name"] = skill_name
            metadata["source"] = "extracted"
        
        # Create chunk
        if text_parts:
            text = " ".join(text_parts)
            chunks.append({
                "text": text,
                "metadata": metadata
            })
    
    print(f"✅ Extracted {len(chunks)} chunks from graph")
    
    if not chunks:
        print("⚠️  No chunks to embed. The graph may be empty.")
        sys.exit(0)
    
    # Initialize components
    print("\n🔧 Initializing embedding components...")
    embedder = Embedder()
    vector_store = VectorStore()
    chunker = TextChunker()
    
    # Extract texts
    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    
    # Generate embeddings
    print(f"\n📊 Generating embeddings for {len(texts)} chunks...")
    print("   (This may take a while on first run as models are downloaded)")
    
    try:
        embeddings = embedder.embed(texts)
        print(f"✅ Generated embeddings with shape: {embeddings.shape}")
    except Exception as e:
        print(f"❌ Error generating embeddings: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Add to vector store
    print("\n💾 Adding embeddings to vector store...")
    vector_store.add(embeddings, metadatas)
    
    # Save vector store
    index_path = "data/embeddings/faiss_index"
    print(f"\n💾 Saving vector store to: {index_path}.*")
    vector_store.save(index_path)
    
    # Print stats
    print("\n" + "="*70)
    print("✅ Embeddings Built Successfully!")
    print("="*70)
    print(f"Chunks processed: {len(chunks)}")
    print(f"Embedding dimension: {embeddings.shape[1] if len(embeddings.shape) > 1 else embeddings.shape[0]}")
    print(f"Vector store saved to: {index_path}.*")
    print(f"  - {index_path}.faiss")
    print(f"  - {index_path}.metadata.pkl")
    print(f"  - {index_path}.config.json")
    print("\n🚀 Ready to query with RAG!")

if __name__ == "__main__":
    main()
