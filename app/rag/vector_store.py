"""Vector store using FAISS for similarity search."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VectorStore:
    """
    FAISS-based vector store for RAG.

    Stores embeddings with metadata for semantic search.
    """

    def __init__(self, dimension: int = 384, index_path: Optional[str] = None):
        """
        Initialize vector store.

        Args:
            dimension: Embedding dimension
            index_path: Path to save/load index
        """
        self.dimension = dimension
        self.index_path = index_path
        self._index = None
        self._metadata: Dict[int, Dict[str, Any]] = {}
        self._next_id = 0

    @property
    def index(self):
        """Lazy-load FAISS index."""
        if self._index is None:
            self._load_or_create_index()
        return self._index

    def _load_or_create_index(self):
        """Load existing index or create new one."""
        try:
            import faiss
        except ImportError:
            logger.warning("FAISS not installed, using in-memory store")
            self._index = "mock"
            return

        if self.index_path and Path(self.index_path).exists():
            # Load existing index
            self._index = faiss.read_index(self.index_path)
            self._load_metadata()
            logger.info(f"Loaded FAISS index from {self.index_path}")
        else:
            # Create new index
            self._index = faiss.IndexFlatL2(self.dimension)
            logger.info(f"Created new FAISS index with dimension {self.dimension}")

    def _load_metadata(self) -> None:
        """Load metadata from disk."""
        if self.index_path:
            meta_path = Path(self.index_path).with_suffix('.json')
            if meta_path.exists():
                with open(meta_path) as f:
                    data = json.load(f)
                    self._metadata = {int(k): v for k, v in data.items()}
                    self._next_id = max(self._metadata.keys(), default=-1) + 1

    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        if self.index_path:
            meta_path = Path(self.index_path).with_suffix('.json')
            with open(meta_path, 'w') as f:
                json.dump(self._metadata, f)

    def add(self, embedding: List[float], metadata: Dict[str, Any]) -> int:
        """
        Add embedding to store.

        Args:
            embedding: Embedding vector
            metadata: Associated metadata

        Returns:
            ID of added embedding
        """
        if self.index == "mock":
            doc_id = self._next_id
            self._next_id += 1
            self._metadata[doc_id] = metadata
            return doc_id

        import numpy as np

        embedding_array = np.array([embedding], dtype='float32')
        self.index.add(embedding_array)

        doc_id = self._next_id
        self._next_id += 1

        self._metadata[doc_id] = metadata
        self._save_metadata()

        return doc_id

    def search(self, query_embedding: List[float],
               top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar embeddings.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results

        Returns:
            List of (metadata, distance) tuples
        """
        if self.index == "mock":
            # Simple mock: return all metadata with random-ish distances
            import random
            results = []
            for doc_id, meta in list(self._metadata.items())[:top_k]:
                results.append((meta, random.uniform(0.5, 2.0)))
            return results

        import numpy as np

        if self.index.ntotal == 0:
            return []

        query_array = np.array([query_embedding], dtype='float32')
        distances, indices = self.index.search(query_array, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx in self._metadata:
                results.append((
                    self._metadata[idx],
                    float(distances[0][i])
                ))

        return results

    def save(self) -> None:
        """Save index to disk."""
        if self.index_path and self._index != "mock":
            import faiss
            faiss.write_index(self._index, self.index_path)
            self._save_metadata()
            logger.info(f"Saved FAISS index to {self.index_path}")

    def clear(self) -> None:
        """Clear the vector store."""
        self._index = None
        self._metadata = {}
        self._next_id = 0
