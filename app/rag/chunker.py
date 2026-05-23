"""Text chunking for RAG embeddings."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, List


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    text: str
    chunk_id: str
    source: str
    start_idx: int = 0
    end_idx: int = 0
    metadata: dict = None


class TextChunker:
    """
    Chunks text for embedding and RAG retrieval.

    Strategies:
    - Fixed size: Split by character count
    - Sentence-based: Split by sentence boundaries
    - Semantic: Split by paragraph/section boundaries
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize chunker.

        Args:
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, source: str = "") -> List[TextChunk]:
        """
        Split text into chunks.

        Args:
            text: Text to chunk
            source: Source identifier

        Returns:
            List of TextChunk objects
        """
        chunks = []

        # Split by paragraphs first
        paragraphs = self._split_paragraphs(text)

        current_chunk = ""
        start_idx = 0

        for i, para in enumerate(paragraphs):
            if len(current_chunk) + len(para) <= self.chunk_size:
                # Add to current chunk
                current_chunk += para + "\n\n"
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunk = TextChunk(
                        text=current_chunk.strip(),
                        chunk_id=f"{source}_chunk_{len(chunks)}",
                        source=source,
                        start_idx=start_idx,
                        end_idx=start_idx + len(current_chunk),
                        metadata={"paragraph": i},
                    )
                    chunks.append(chunk)

                # Handle overlap
                if self.overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.overlap:]
                    start_idx = len(text) - len(overlap_text)
                    current_chunk = overlap_text + para
                else:
                    current_chunk = para
                    start_idx = start_idx + len(current_chunk) - self.overlap

        # Add final chunk
        if current_chunk:
            chunk = TextChunk(
                text=current_chunk.strip(),
                chunk_id=f"{source}_chunk_{len(chunks)}",
                source=source,
                start_idx=start_idx,
                end_idx=start_idx + len(current_chunk),
                metadata={"paragraph": len(paragraphs) - 1},
            )
            chunks.append(chunk)

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def chunk_by_sentences(self, text: str, source: str = "") -> List[TextChunk]:
        """Split text by sentences."""
        chunks = []
        # Simple sentence split
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = ""
        for i, sentence in enumerate(sentences):
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(TextChunk(
                        text=current_chunk.strip(),
                        chunk_id=f"{source}_sent_{len(chunks)}",
                        source=source,
                        metadata={"sentence_range": f"{i - 1}-{i}"},
                    ))
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(TextChunk(
                text=current_chunk.strip(),
                chunk_id=f"{source}_sent_{len(chunks)}",
                source=source,
                metadata={"sentence_range": f"{len(sentences) - 1}"},
            ))

        return chunks
