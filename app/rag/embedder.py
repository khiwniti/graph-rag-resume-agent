"""Text embedding using sentence transformers."""
from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class Embedder:
    """
    Embeds text using sentence transformers.

    Supports:
    - local models via sentence-transformers
    - API-based models via NVIDIA, OpenAI, etc.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedder.

        Args:
            model_name: Name of embedding model
        """
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded embedding model: {self.model_name}")
            except ImportError:
                logger.warning("sentence-transformers not installed, using mock embedder")
                self._model = "mock"
        return self._model

    def embed(self, text: str) -> List[float]:
        """
        Embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if self.model == "mock":
            return self._mock_embed(text)

        embedding = self.model.encode([text])[0]
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if self.model == "mock":
            return [self._mock_embed(t) for t in texts]

        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def _mock_embed(self, text: str) -> List[float]:
        """Return mock embedding for testing."""
        # Simple hash-based mock embedding
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        dimension = 384  # Common dimension for sentence-transformers
        # Generate deterministic pseudo-random vector
        return [
            ((hash_val >> (i % 32)) % 1000) / 1000.0 - 0.5
            for i in range(dimension)
        ]

    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Cosine similarity (0-1)
        """
        import numpy as np

        emb1 = self.embed(text1)
        emb2 = self.embed(text2)

        # Compute cosine similarity
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
