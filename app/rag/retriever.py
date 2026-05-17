"""Retriever - hybrid retrieval combining vector and graph search."""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np

from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.graph.query import GraphQuerier


class Retriever:
    """
    Hybrid retriever combining vector similarity with graph traversal.
    
    Features:
    - Vector-based similarity search
    - Graph-based relationship traversal
    - Reciprocal Rank Fusion for combining results
    - Citation-aware retrieval
    """

    def __init__(
        self,
        vector_store: VectorStore,
        graph_querier: Optional[GraphQuerier] = None,
        embedder: Optional[Embedder] = None,
        chunker: Optional[TextChunker] = None,
        index_path: str = "data/embeddings/faiss_index",
        graph_path: str = "data/graph/knowledge_graph.json"
    ):
        """
        Initialize retriever.
        
        Args:
            vector_store: Vector store instance
            graph_querier: Graph querier instance
            embedder: Embedder instance
            chunker: Text chunker instance
            index_path: Path to vector index
            graph_path: Path to graph file
        """
        self.vector_store = vector_store
        self.graph_querier = graph_querier or GraphQuerier(graph_path)
        self.embedder = embedder or Embedder()
        self.chunker = chunker or TextChunker()
        self.index_path = index_path
        self.graph_path = graph_path

    def retrieve(
        self,
        query: str,
        k: int = 10,
        use_graph: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: Query string
            k: Number of results
            use_graph: Whether to include graph-based results
            
        Returns:
            List of result dicts with text and metadata
        """
        # Embed query
        query_embedding = self.embedder.embed(query)
        
        # Vector search
        vector_results = self.vector_store.search(query_embedding, k=k)
        
        # Graph search (if enabled)
        graph_results = []
        if use_graph:
            graph_results = self._search_graph(query)
        
        # Combine results
        if graph_results and vector_results:
            # Reciprocal Rank Fusion
            combined = self._reciprocal_rank_fusion(
                vector_results,
                graph_results,
                k=k
            )
        elif vector_results:
            combined = vector_results
        elif graph_results:
            combined = graph_results
        else:
            combined = []
        
        return combined

    def _search_graph(self, query: str) -> List[Dict[str, Any]]:
        """
        Search graph for relevant nodes.
        
        Args:
            query: Query string
            
        Returns:
            List of graph results
        """
        results = []
        query_lower = query.lower()
        
        # Search skills
        skills = self.graph_querier.search_skills(query_lower)
        for skill in skills:
            results.append({
                "type": "skill",
                "text": f"Skill: {skill.get('name', '')} ({skill.get('category', '')})",
                "metadata": skill,
                "source": "graph",
            })
        
        # Get top skills
        top_skills = self.graph_querier.get_top_skills(limit=5)
        for skill in top_skills:
            if skill not in results:
                results.append({
                    "type": "skill",
                    "text": f"Top skill: {skill.get('name', '')} (confidence: {skill.get('confidence', 0):.2f})",
                    "metadata": skill,
                    "source": "graph",
                })
        
        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[Dict[str, Any], float]],
        graph_results: List[Dict[str, Any]],
        k: int
    ) -> List[Dict[str, Any]]:
        """
        Combine vector and graph results using Reciprocal Rank Fusion.
        
        Args:
            vector_results: Vector search results
            graph_results: Graph search results
            k: Number of final results
            
        Returns:
            Combined and ranked results
        """
        # Score by reciprocal rank
        fused_scores = {}
        
        # Vector results
        for i, (metadata, score) in enumerate(vector_results):
            key = str(metadata.get("chunk_id", str(i)))
            if key not in fused_scores:
                fused_scores[key] = {"metadata": metadata, "score": 0.0}
            fused_scores[key]["score"] += 1.0 / (i + 1)
        
        # Graph results
        for i, result in enumerate(graph_results):
            key = f"graph_{i}"
            if key not in fused_scores:
                fused_scores[key] = {
                    "metadata": result.get("metadata", {}),
                    "text": result.get("text", ""),
                    "score": 0.0
                }
            fused_scores[key]["score"] += 1.0 / (i + 1)
        
        # Sort by score
        sorted_results = sorted(
            fused_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        # Convert to final format
        final_results = []
        for item in sorted_results[:k]:
            final_results.append({
                "metadata": item["metadata"],
                "text": item.get("text", item["metadata"].get("text", "")),
                "score": item["score"],
            })
        
        return final_results

    def retrieve_with_citations(
        self,
        query: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve context with citation information.
        
        Args:
            query: Query string
            k: Number of results
            
        Returns:
            Dict with results and citation metadata
        """
        results = self.retrieve(query, k=k)
        
        # Extract citations
        citations = []
        seen_sources = set()
        
        for result in results:
            metadata = result.get("metadata", {})
            source = metadata.get("source", "unknown")
            
            if source not in seen_sources:
                citations.append({
                    "source": source,
                    "file_path": metadata.get("file_path", ""),
                    "repo_name": metadata.get("repo_name", ""),
                })
                seen_sources.add(source)
        
        return {
            "query": query,
            "context": results,
            "citations": citations,
            "result_count": len(results),
        }

    def build_index(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "text"
    ):
        """
        Build index from documents.
        
        Args:
            documents: List of document dicts
            text_field: Field containing text
        """
        # Chunk documents
        chunks = self.chunker.chunk_documents(documents, text_field)
        
        # Extract texts
        texts = [chunk["text"] for chunk in chunks]
        
        # Embed
        embeddings = self.embedder.embed(texts)
        
        # Add to vector store with metadata
        metadata = [chunk.get("metadata", {}) for chunk in chunks]
        self.vector_store.add(embeddings, metadata)
        
        # Save
        self.vector_store.save(self.index_path)
