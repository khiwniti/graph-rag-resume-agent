"""GPU-accelerated embedder — patches sentence-transformers for CUDA.

On Kaggle/Colab, this transparently accelerates embedding generation by
moving the model to GPU. Falls back to CPU gracefully.

Usage:
    from app.rag.gpu_embedder import GPUEmbedder
    embedder = GPUEmbedder("all-MiniLM-L6-v2")
    vec = embedder.embed("Hello world")           # single
    vecs = embedder.embed_batch(["a", "b", "c"])  # batch (GPU-accelerated)
"""

from __future__ import annotations

import logging
from typing import List, Optional

import torch
import numpy as np

logger = logging.getLogger(__name__)


def get_best_device() -> str:
    """Return the best available PyTorch device."""
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0) or "unknown"
        mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        logger.info(f"GPU detected: {gpu_name} ({mem_gb:.1f} GB)")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        logger.info("Apple MPS detected")
    else:
        device = "cpu"
        logger.info("No GPU — falling back to CPU")
    return device


class GPUEmbedder:
    """Sentence-transformer embedder with automatic GPU offload.

    Drop-in replacement for `app.rag.embedder.Embedder` with identical API
    but CUDA/MPS acceleration.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 device: Optional[str] = None,
                 batch_size: int = 64):
        """Initialize GPU embedder.

        Args:
            model_name: HuggingFace sentence-transformer model name.
            device: One of 'cuda', 'mps', 'cpu', or None for auto-detect.
            batch_size: Batch size for encode() calls.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self._device = device or get_best_device()
        self._model = None
        self._dimension: Optional[int] = None

    @property
    def model(self):
        """Lazy-load the SentenceTransformer on the target device."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(
                    self.model_name, device=self._device
                )
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(
                    f"Loaded '{self.model_name}' on {self._device} "
                    f"(dim={self._dimension}, batch={self.batch_size})"
                )
            except ImportError:
                logger.warning("sentence-transformers not installed; using mock")
                self._model = "mock"
                self._dimension = 384
        return self._model

    @property
    def dimension(self) -> int:
        """Return embedding dimension (forces lazy load if needed)."""
        if self._dimension is None:
            _ = self.model  # trigger load
        return self._dimension or 384

    def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        if self.model == "mock":
            return self._mock_embed(text)
        emb = self.model.encode([text], batch_size=1, show_progress_bar=False)[0]
        return emb.tolist()

    def embed_batch(self, texts: List[str],
                    show_progress: bool = True) -> List[List[float]]:
        """Embed a batch of texts — GPU-accelerated."""
        if not texts:
            return []
        if self.model == "mock":
            return [self._mock_embed(t) for t in texts]
        embs = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return embs.tolist()

    def embed_batch_numpy(self, texts: List[str],
                          show_progress: bool = True) -> np.ndarray:
        """Embed a batch and return a float32 numpy array (for FAISS)."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        if self.model == "mock":
            return np.array([self._mock_embed(t) for t in texts], dtype=np.float32)
        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        ).astype(np.float32)

    def similarity(self, text1: str, text2: str) -> float:
        """Cosine similarity between two texts."""
        import numpy as np
        e1 = np.array(self.embed(text1), dtype=np.float32)
        e2 = np.array(self.embed(text2), dtype=np.float32)
        dot = float(np.dot(e1, e2))
        n1 = float(np.linalg.norm(e1))
        n2 = float(np.linalg.norm(e2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def _mock_embed(self, text: str) -> List[float]:
        """Deterministic mock embedding for testing."""
        import hashlib
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        d = self.dimension
        return [((h >> (i % 32)) % 1000) / 1000.0 - 0.5 for i in range(d)]
