"""Text chunker - splits documents into retrievable chunks."""
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


class TextChunker:
    """
    Splits text documents into chunks for embedding and retrieval.
    
    Strategies:
    - Fixed size with overlap
    - Sentence-based
    - Paragraph-based
    - Code-aware (by function/class)
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dicts with text and metadata
        """
        metadata = metadata or {}
        chunks = []
        
        # Simple fixed-size chunking with overlap
        start = 0
        chunk_idx = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end
                sentence_end = re.search(r'[.!?]\s', text[start:end])
                if sentence_end:
                    end = start + sentence_end.end()
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunk = {
                    "chunk_id": f"chunk_{chunk_idx}",
                    "text": chunk_text,
                    "start": start,
                    "end": end,
                    "metadata": metadata.copy(),
                }
                chunks.append(chunk)
                chunk_idx += 1
            
            # Move with overlap
            start += self.chunk_size - self.chunk_overlap
        
        # Handle case where no chunks were created
        if not chunks and text.strip():
            chunks.append({
                "chunk_id": "chunk_0",
                "text": text.strip(),
                "start": 0,
                "end": len(text),
                "metadata": metadata.copy(),
            })
        
        return chunks

    def chunk_code(
        self,
        code: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Split code into chunks by function/class.
        
        Args:
            code: Code to chunk
            file_path: Path to the code file
            metadata: Optional metadata
            
        Returns:
            List of chunk dicts
        """
        metadata = metadata or {}
        metadata["file_path"] = file_path
        metadata["chunk_type"] = "code"
        
        # Detect language
        ext = Path(file_path).suffix.lower()
        
        if ext == ".py":
            chunks = self._chunk_python(code, metadata)
        elif ext in [".ts", ".tsx", ".js", ".jsx"]:
            chunks = self._chunk_javascript(code, metadata)
        else:
            # Fallback to text chunking
            chunks = self.chunk_text(code, metadata)
        
        return chunks

    def _chunk_python(
        self,
        code: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk Python code by function/class."""
        chunks = []
        lines = code.split("\n")
        
        current_chunk = []
        current_indent = 0
        chunk_idx = 0
        
        for i, line in enumerate(lines):
            # Check for function or class definition
            if re.match(r'^(def|class)\s+\w+', line):
                # Save previous chunk if exists
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    if len(chunk_text.strip()) >= self.min_chunk_size:
                        chunks.append({
                            "chunk_id": f"chunk_{chunk_idx}",
                            "text": chunk_text,
                            "line_start": i - len(current_chunk),
                            "line_end": i,
                            "metadata": metadata.copy(),
                        })
                        chunk_idx += 1
                    current_chunk = []
            
            current_chunk.append(line)
            
            # Limit chunk size
            if len("\n".join(current_chunk)) > self.chunk_size:
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "chunk_id": f"chunk_{chunk_idx}",
                    "text": chunk_text,
                    "line_start": i - len(current_chunk),
                    "line_end": i,
                    "metadata": metadata.copy(),
                })
                chunk_idx += 1
                current_chunk = []
        
        # Save remaining
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append({
                    "chunk_id": f"chunk_{chunk_idx}",
                    "text": chunk_text,
                    "line_start": len(lines) - len(current_chunk),
                    "line_end": len(lines),
                    "metadata": metadata.copy(),
                })
        
        return chunks

    def _chunk_javascript(
        self,
        code: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk JavaScript/TypeScript code by function."""
        # For now, use text chunking
        # Could be enhanced to parse AST
        return self.chunk_text(code, metadata)

    def chunk_documents(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Chunk multiple documents.
        
        Args:
            documents: List of document dicts
            text_field: Field containing text
            
        Returns:
            List of all chunks
        """
        all_chunks = []
        
        for doc in documents:
            text = doc.get(text_field, "")
            metadata = {k: v for k, v in doc.items() if k != text_field}
            
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
