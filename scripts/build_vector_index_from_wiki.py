"""Build FAISS vector index from the exported wiki vault (data/wiki).

Goal: make /query hybrid retrieval usable without re-running the full collection pipeline.

This indexes markdown pages in data/wiki (concepts/sections/etc.) with lightweight metadata.
It is safe for Neo4j Aura free tier because it only touches the local FAISS index.

Usage:
  python scripts/build_vector_index_from_wiki.py --wiki-dir data/wiki --limit 2000

Outputs:
  data/embeddings/faiss_index.faiss
  data/embeddings/faiss_index.json

Notes:
- We intentionally do NOT ingest conversation artifacts.
- Pages are ranked by frontmatter confidence when available.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repo root is on sys.path when running as a script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.config import EMBEDDINGS_DIR, EMBEDDING_MODEL
from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore


@dataclass
class WikiDoc:
    path: str
    title: str
    doc_type: str
    confidence: float
    text: str


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(md: str) -> Tuple[Dict[str, Any], str]:
    """Parse a tiny YAML-ish frontmatter without adding PyYAML dependency."""
    m = _FRONTMATTER_RE.search(md)
    if not m:
        return {}, md
    block = m.group(1)
    rest = md[m.end() :]

    meta: Dict[str, Any] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        meta[k] = v

    return meta, rest


def _load_wiki_docs(wiki_dir: Path) -> List[WikiDoc]:
    out: List[WikiDoc] = []
    for p in wiki_dir.rglob("*.md"):
        try:
            md = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        meta, body = _parse_frontmatter(md)
        title = str(meta.get("title") or p.stem)
        doc_type = str(meta.get("type") or "document")
        try:
            conf = float(meta.get("confidence") or 0.0)
        except Exception:
            conf = 0.0

        # Keep body reasonably sized (embedder cost guard)
        body = body.strip()
        if not body:
            continue
        if len(body) > 20_000:
            body = body[:20_000]

        out.append(
            WikiDoc(
                path=str(p.relative_to(wiki_dir)),
                title=title,
                doc_type=doc_type,
                confidence=conf,
                text=body,
            )
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki-dir", default="data/wiki")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--chunk-size", type=int, default=500)
    ap.add_argument("--overlap", type=int, default=50)
    ap.add_argument("--reset", action="store_true", help="delete existing faiss_index.* first")
    args = ap.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        raise SystemExit(f"wiki dir not found: {wiki_dir}")

    index_prefix = EMBEDDINGS_DIR / "faiss_index"
    index_file = index_prefix.with_suffix(".faiss")
    meta_file = index_prefix.with_suffix(".json")

    if args.reset:
        index_file.unlink(missing_ok=True)
        meta_file.unlink(missing_ok=True)

    docs = _load_wiki_docs(wiki_dir)
    docs.sort(key=lambda d: (d.confidence, d.path), reverse=True)
    if args.limit and args.limit > 0:
        docs = docs[: args.limit]

    print(f"Loaded {len(docs)} wiki docs from {wiki_dir}")

    chunker = TextChunker(chunk_size=args.chunk_size, overlap=args.overlap)
    embedder = Embedder(model_name=EMBEDDING_MODEL)
    store = VectorStore(dimension=384, index_path=str(index_prefix))

    # Collect all chunks first (bounded by limit + chunking)
    chunk_texts: List[str] = []
    chunk_metas: List[Dict[str, Any]] = []

    for d in docs:
        # Include title for better semantic retrieval
        text = f"# {d.title}\n\n{d.text}"
        chunks = chunker.chunk(text, source=d.path)
        for c in chunks:
            chunk_texts.append(c.text)
            chunk_metas.append(
                {
                    "type": "wiki",
                    "wiki_type": d.doc_type,
                    "wiki_path": d.path,
                    "title": d.title,
                    "confidence": d.confidence,
                    "chunk_id": c.chunk_id,
                }
            )

    print(f"Prepared {len(chunk_texts)} chunks for embedding")

    # Embed in batches
    batch_size = 32
    added = 0
    for i in range(0, len(chunk_texts), batch_size):
        batch_texts = chunk_texts[i : i + batch_size]
        batch_metas = chunk_metas[i : i + batch_size]
        embeddings = embedder.embed_batch(batch_texts)
        for emb, meta in zip(embeddings, batch_metas):
            store.add(emb, meta)
            added += 1
        if (i // batch_size) % 20 == 0:
            print(f"Embedded+added {added}/{len(chunk_texts)}")

    store.save()
    # Force file presence check
    print(f"Saved FAISS index: {index_file}")
    print(f"Saved metadata:   {meta_file}")
    try:
        idx = store.index
        if idx != "mock" and getattr(idx, "ntotal", None) is not None:
            print(f"Index vectors: {idx.ntotal}")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
