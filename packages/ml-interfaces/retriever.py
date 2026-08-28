"""Retriever — knowledge + user-value evidence retrieval for Q&A."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .types import RetrievedDocument


@runtime_checkable
class Retriever(Protocol):
    """
    Rank relevant evidence chunks for a user question.

    Default: BM25 + intent boost + user value keyword match
    (services/ai-service/rag/retriever.py).
    Phase 3: USE_EMBEDDING_SEARCH=1 → SemanticRetriever (embeddings + FAISS)
    with BM25 FallbackRetriever.
    """

    def retrieve(
        self,
        query: str,
        user_report_values: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        """Return top_k evidence chunks, highest score first."""
        ...
