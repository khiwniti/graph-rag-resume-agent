"""Vector store - FAISS-based vector storage and similarity search."""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    faiss = None


class VectorStore:
    """
    FAISS-based vector store for similarity search.
    
    Features:
    - Add embeddings with metadata
    - Similarity search
    - Persistence to disk
    - Incremental updates
    """

    def __init__(
        self,
        index_path: str = "data/embeddings/faiss_index",
        dimension: int = 384,
        metric: str = "cosine"
    ):
        """
        Initialize vector store.
        
        Args:
            index_path: Path to save/load index
            dimension: Embedding dimension
            metric: Distance metric (cosine, l2)
        """
        self.index_path = index_path
        self.dimension = dimension
        self.metric = metric
        self.index = None
        self.metadata_store = []  # List of metadata dicts
        self._initialized = False

    def _initialize(self):
        """Initialize FAISS index."""
        if self._initialized:
            return
        
        if not HAS_FAISS:
            raise ImportError(
                "faiss not installed. Install with: pip install faiss-cpu"
            )
        
        # Create index
        if self.metric == "cosine":
            self.index = faiss.IndexFlatIP(self.dimension)
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
        
        self._initialized = True

    def add(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict[str, Any]]
    ):
        """
        Add embeddings to store.
        
        Args:
            embeddings: Embedding array (n, d)
            metadata: List of metadata dicts
        """
        self._initialize()
        
        # Normalize for cosine similarity
        if self.metric == "cosine":
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / np.where(norms == 0, 1, norms)
        
        self.index.add(embeddings.astype(np.float32))
        self.metadata_store.extend(metadata)

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding (1, d) or (d,)
            k: Number of results
            
        Returns:
            List of (metadata, score) tuples
        """
        self._initialize()
        
        # Ensure 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Normalize for cosine
        if self.metric == "cosine":
            norm = np.linalg.norm(query_embedding, axis=1, keepdims=True)
            query_embedding = query_embedding / np.where(norm == 0, 1, norm)
        
        # Search
        scores, indices = self.index.search(
            query_embedding.astype(np.float32),
            k
        )
        
        # Convert to results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata_store):
                results.append((
                    self.metadata_store[idx],
                    float(scores[0][i])
                ))
        
        return results

    def save(self, path: Optional[str] = None):
        """
        Save index and metadata to disk.
        
        Args:
            path: Save path (default: self.index_path)
        """
        self._initialize()
        save_path = path or self.index_path
        
        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, f"{save_path}.faiss")
        
        # Save metadata
        with open(f"{save_path}.metadata.pkl", "wb") as f:
            pickle.dump(self.metadata_store, f)
        
        # Save config
        config = {
            "dimension": self.dimension,
            "metric": self.metric,
        }
        with open(f"{save_path}.config.json", "w") as f:
            json.dump(config, f, indent=2)

    def load(self, path: Optional[str] = None) -> bool:
        """
        Load index and metadata from disk.
        
        Args:
            path: Load path (default: self.index_path)
            
        Returns:
            True if loaded successfully
        """
        load_path = path or self.index_path
        
        if not Path(f"{load_path}.faiss").exists():
            return False
        
        if not HAS_FAISS:
            raise ImportError("faiss not installed")
        
        # Load FAISS index
        self.index = faiss.read_index(f"{load_path}.faiss")
        
        # Load metadata
        with open(f"{load_path}.metadata.pkl", "rb") as f:
            self.metadata_store = pickle.load(f)
        
        # Load config
        config_path = f"{load_path}.config.json"
        if Path(config_path).exists():
            with open(config_path, "r") as f:
                config = json.load(f)
                self.dimension = config.get("dimension", self.dimension)
                self.metric = config.get("metric", self.metric)
        
        self._initialized = True
        return True

    def clear(self):
        """Clear the index."""
        self._initialize()
        self.index = faiss.IndexFlatIP(self.dimension) if self.metric == "cosine" else faiss.IndexFlatL2(self.dimension)
        self.metadata_store = []

    def count(self) -> int:
        """
        Get number of vectors in store.
        
        Returns:
            Number of vectors
        """
        self._initialize()
        return self.index.ntotal

    def get_stats(self) -> Dict[str, Any]:
        """
        Get store statistics.
        
        Returns:
            Dict with stats
        """
        return {
            "vector_count": self.count(),
            "dimension": self.dimension,
            "metric": self.metric,
            "index_path": self.index_path,
        }
