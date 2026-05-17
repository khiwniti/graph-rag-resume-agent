"""Embedder - creates embeddings for text chunks."""
from typing import List, Dict, Any, Optional, Union
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None


class Embedder:
    """
    Creates embeddings for text using sentence-transformers.
    
    Supports:
    - Local embeddings with sentence-transformers
    - Multiple embedding models
    - Batch embedding for efficiency
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        """
        Initialize embedder.
        
        Args:
            model_name: Name of embedding model
            device: Device to run on (cpu, cuda)
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self._model_loaded = False

    def _load_model(self):
        """Load embedding model lazily."""
        if self._model_loaded:
            return
        
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self._model_loaded = True

    def embed(
        self,
        text: Union[str, List[str]],
        normalize: bool = True
    ) -> np.ndarray:
        """
        Create embedding(s) for text.
        
        Args:
            text: Single string or list of strings
            normalize: Whether to normalize embeddings
            
        Returns:
            Embedding array(s)
        """
        self._load_model()
        
        if isinstance(text, str):
            text = [text]
        
        embeddings = self.model.encode(
            text,
            normalize_embeddings=normalize,
            show_progress_bar=len(text) > 10
        )
        
        return embeddings

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Create embeddings in batches.
        
        Args:
            texts: List of texts
            batch_size: Batch size for processing
            normalize: Whether to normalize embeddings
            
        Returns:
            Embedding array
        """
        self._load_model()
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch,
                normalize_embeddings=normalize,
                show_progress_bar=True
            )
            all_embeddings.append(batch_embeddings)
        
        return np.vstack(all_embeddings)

    def get_embedding_dimension(self) -> int:
        """
        Get embedding dimension.
        
        Returns:
            Dimension of embeddings
        """
        self._load_model()
        return self.model.get_sentence_embedding_dimension()

    def embed_with_metadata(
        self,
        chunks: List[Dict[str, Any]],
        text_field: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Embed chunks and attach embeddings to metadata.
        
        Args:
            chunks: List of chunk dicts
            text_field: Field containing text
            
        Returns:
            Chunks with embeddings added
        """
        texts = [chunk.get(text_field, "") for chunk in chunks]
        embeddings = self.embed(texts)
        
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i].tolist()
        
        return chunks
