"""GPU-accelerated FAISS vector store — for Kaggle/GPU environments.

Drop-in GPU vector store that mirrors the app.rag.vector_store.VectorStore API
but with CUDA-accelerated similarity search via faiss-gpu.

Usage:
    from app.rag.gpu_faiss_store import GPUFAISSStore
    store = GPUFAISSStore(dimension=384)
    store.add(embedding, metadata)
    results = store.search(query_emb, top_k=10)
    store.save("/path/to/index")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    _FAISS_AVAILABLE = False


class GPUFAISSStore:
    """FAISS vector store with automatic GPU offload.

    Falls back to CPU if faiss-gpu isn't available.
    """

    def __init__(self, dimension: int = 384, use_gpu: bool = True,
                 gpu_temp_memory_mb: int = 512):
        """Initialize GPU-accelerated FAISS index.

        Args:
            dimension: Embedding vector dimension.
            use_gpu: Try to use GPU. Falls back to CPU silently.
            gpu_temp_memory_mb: GPU scratch memory in MB.
        """
        if not _FAISS_AVAILABLE:
            raise ImportError(
                "faiss is required. Install with: pip install faiss-cpu"
            )

        self.dimension = dimension
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self._next_id = 0
        self._gpu_res = None

        # Create CPU index first (required for GPU transfer)
        self._cpu_index = faiss.IndexFlatL2(dimension)

        # Move to GPU if available
        if use_gpu and faiss.get_num_gpus() > 0:
            try:
                self._gpu_res = faiss.StandardGpuResources()
                self._gpu_res.setTempMemory(gpu_temp_memory_mb * 1024 * 1024)
                self._index = faiss.index_cpu_to_gpu(
                    self._gpu_res, 0, self._cpu_index
                )
                logger.info(
                    f"FAISS on GPU: {faiss.get_num_gpus()} GPU(s), "
                    f"{gpu_temp_memory_mb} MB scratch"
                )
            except Exception as e:
                logger.warning(f"GPU FAISS init failed, using CPU: {e}")
                self._index = self._cpu_index
        else:
            self._index = self._cpu_index
            logger.info("FAISS on CPU")

    @property
    def ntotal(self) -> int:
        """Number of vectors in the index."""
        return self._index.ntotal

    def add(self, embedding: np.ndarray,
            metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a single embedding.

        Args:
            embedding: Float32 array of shape (dimension,) or (1, dimension).
            metadata: Optional metadata dict.

        Returns:
            ID of the added embedding.
        """
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)

        idx_start = self._next_id
        for i in range(embedding.shape[0]):
            self.metadata[self._next_id + i] = metadata or {}
        self._next_id += embedding.shape[0]

        self._index.add(embedding.astype(np.float32))
        return idx_start

    def add_batch(self, embeddings: np.ndarray,
                  metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[int]:
        """Add a batch of embeddings.

        Args:
            embeddings: Float32 array of shape (N, dimension).
            metadata_list: Optional list of metadata dicts, one per embedding.

        Returns:
            List of IDs for the added embeddings.
        """
        if metadata_list is None:
            metadata_list = [{}] * embeddings.shape[0]

        ids = []
        for i, meta in enumerate(metadata_list):
            ids.append(self.add(embeddings[i:i + 1], meta))
        return ids

    def search(self, query_embedding: np.ndarray,
               top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Search for top_k nearest neighbors.

        Args:
            query_embedding: Float32 array of shape (dimension,) or (1, dimension).
            top_k: Number of results.

        Returns:
            List of (metadata, distance) tuples.
        """
        if self.ntotal == 0:
            return []

        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        k = min(top_k, self.ntotal)
        distances, indices = self._index.search(
            query_embedding.astype(np.float32), k
        )

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx >= 0 and idx in self.metadata:
                results.append((self.metadata[idx], float(dist)))

        return results

    def save(self, path: str) -> None:
        """Save index and metadata to disk.

        Transfers GPU index to CPU before saving.

        Args:
            path: File path for the FAISS index (metadata saved as path.json).
        """
        # Move to CPU if on GPU
        if self._gpu_res is not None:
            cpu_idx = faiss.index_gpu_to_cpu(self._index)
        else:
            cpu_idx = self._index

        faiss.write_index(cpu_idx, path)
        logger.info(f"Saved FAISS index ({self.ntotal} vectors) to {path}")

        # Save metadata
        meta_path = Path(path).with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump({str(k): v for k, v in self.metadata.items()}, f)
        logger.info(f"Saved metadata ({len(self.metadata)} entries) to {meta_path}")

    @classmethod
    def load(cls, path: str, use_gpu: bool = True) -> "GPUFAISSStore":
        """Load index and metadata from disk.

        Args:
            path: File path for the FAISS index.
            use_gpu: Whether to move to GPU after loading.

        Returns:
            Loaded GPUFAISSStore.
        """
        if not _FAISS_AVAILABLE:
            raise ImportError("faiss is required")

        cpu_idx = faiss.read_index(path)
        dimension = cpu_idx.d

        store = cls.__new__(cls)
        store.dimension = dimension
        store._next_id = 0
        store._cpu_index = cpu_idx
        store._gpu_res = None

        # Move to GPU
        if use_gpu and faiss.get_num_gpus() > 0:
            try:
                store._gpu_res = faiss.StandardGpuResources()
                store._gpu_res.setTempMemory(512 * 1024 * 1024)
                store._index = faiss.index_cpu_to_gpu(
                    store._gpu_res, 0, store._cpu_index
                )
            except Exception as e:
                logger.warning(f"GPU load failed, using CPU: {e}")
                store._index = store._cpu_index
        else:
            store._index = store._cpu_index

        # Load metadata
        meta_path = Path(path).with_suffix(".json")
        store.metadata = {}
        if meta_path.exists():
            with open(meta_path) as f:
                store.metadata = {int(k): v for k, v in json.load(f).items()}
            store._next_id = max(store.metadata.keys(), default=-1) + 1

        logger.info(f"Loaded FAISS index ({store.ntotal} vectors, dim={dimension})")
        return store

    def clear(self) -> None:
        """Clear the index and metadata."""
        self._next_id = 0
        self.metadata.clear()
        if self._gpu_res is not None:
            self._index = faiss.index_cpu_to_gpu(
                self._gpu_res, 0, faiss.IndexFlatL2(self.dimension)
            )
            self._cpu_index = faiss.IndexFlatL2(self.dimension)
        else:
            self._index = faiss.IndexFlatL2(self.dimension)
            self._cpu_index = self._index
