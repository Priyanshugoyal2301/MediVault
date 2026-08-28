"""
Load knowledge-base chunks into the in-memory retriever at AI service startup.

Plan B default: BM25 + intent (no embeddings). Demo-reliable, no HF download.

Optional dense path:
  MEDIVAULT_USE_DENSE=1 → try MiniLM embeddings and hybrid BM25+dense ranking.
  Falls back to BM25-only if MiniLM is unavailable.

Legacy note: MEDIVAULT_FAST_KB=1 previously meant MD5 cosine theater. That path
is removed. FAST_KB now means "skip dense model load" (BM25-only) — still the
recommended demo default.
"""

from __future__ import annotations

import os
from typing import Any

from packages.shared_utils import get_logger

from .ingester import load_documents
from .retriever import load_knowledge_base, knowledge_base_stats

logger = get_logger(__name__)


def bootstrap_knowledge_base() -> dict[str, Any]:
    """
    Load KB files into memory and build BM25 (optionally dense) indexes.
    Safe to call multiple times (replaces in-memory store).
    """
    docs = load_documents()
    if not docs:
        logger.warning("KB bootstrap: no documents found under data/knowledge-base/")
        load_knowledge_base([])
        return {
            "kb_chunks": 0,
            "kb_embedder": "none",
            "kb_retriever": "none",
            "kb_ready": False,
        }

    # FAST_KB (default) → BM25 only. Dense when:
    #   USE_EMBEDDING_SEARCH=1  (new ML feature flag), OR
    #   MEDIVAULT_USE_DENSE=1 and FAST_KB is off (legacy).
    fast = os.getenv("MEDIVAULT_FAST_KB", "1").strip().lower() in (
        "1", "true", "yes",
    )
    legacy_dense = os.getenv("MEDIVAULT_USE_DENSE", "0").strip().lower() in (
        "1", "true", "yes",
    )
    flag_dense = False
    try:
        from ..core.feature_flags import get_feature_flags

        flag_dense = get_feature_flags().use_embedding_search
    except Exception:  # noqa: BLE001
        flag_dense = os.getenv("USE_EMBEDDING_SEARCH", "0").strip().lower() in (
            "1", "true", "yes",
        )
    use_dense = flag_dense or (not fast and legacy_dense)

    embedder_name = "none"
    mode = "bm25"

    if use_dense:
        try:
            from .embedder import embed_text

            _ = embed_text("warmup")
            for d in docs:
                d["embedding"] = embed_text(d["chunk_text"])
            embedder_name = "all-MiniLM-L6-v2"
            mode = "hybrid"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "KB bootstrap: MiniLM unavailable (%s); using BM25-only",
                type(exc).__name__,
            )
            for d in docs:
                d.pop("embedding", None)
            embedder_name = "none"
            mode = "bm25"
    else:
        # Ensure no stale embeddings confuse hybrid mode
        for d in docs:
            d.pop("embedding", None)

    load_knowledge_base(docs, mode=mode)
    stats = knowledge_base_stats()
    logger.info(
        "KB bootstrap complete: chunks=%s retriever=%s embedder=%s",
        stats.get("kb_chunks"),
        stats.get("kb_retriever"),
        embedder_name,
    )
    return {
        "kb_chunks": stats.get("kb_chunks", len(docs)),
        "kb_embedder": embedder_name,
        "kb_retriever": stats.get("kb_retriever", mode),
        "kb_ready": True,
    }
