"""
ai-service/rag/embedder.py

Sentence-transformer embedding module.

Uses all-MiniLM-L6-v2 (384 dimensions, ~80MB model, fast inference).
The model is lazy-loaded as a singleton to avoid repeated downloads and to
keep import-time fast for tests that don't need the model.

ARCHITECTURE NOTE:
  Embeddings are generated at two points:
    1. Knowledge base ingestion (one-shot, via ingester.py)
    2. Query-time (per user question, via retriever.py)
  The same model MUST be used for both to ensure cosine similarity is valid.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"
_EMBEDDING_DIM = 384

_model: SentenceTransformer | None = None
_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    """Lazy-load the sentence-transformer model (thread-safe singleton)."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single text string → 384-dim vector."""
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts → list of 384-dim vectors."""
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
    return [e.tolist() for e in embeddings]


def get_embedding_dim() -> int:
    """Return the embedding dimensionality (384 for MiniLM-L6-v2)."""
    return _EMBEDDING_DIM
