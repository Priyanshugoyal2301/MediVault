"""
Retriever adapters: BM25 (default) + Semantic (Phase 3) + Fallback.
"""

from __future__ import annotations

from typing import Any

from packages.ml_interfaces.types import RetrievedDocument
from packages.shared_utils import get_logger

from ..rag.retriever import retrieve as _bm25_retrieve

logger = get_logger(__name__)


class BM25Retriever:
    """Production default for Retriever Protocol — pure BM25(+intent) stack."""

    def retrieve(
        self,
        query: str,
        user_report_values: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        chunks = _bm25_retrieve(
            query=query,
            user_report_values=user_report_values,
            top_k=top_k,
        )
        return [
            RetrievedDocument(
                text=c.text,
                source=c.source,
                source_url=c.source_url,
                score=c.score,
                is_user_data=c.is_user_data,
            )
            for c in chunks
        ]


class SemanticRetrieverAdapter:
    """Phase 3 SemanticRetriever → RetrievedDocument for /qa."""

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from models.retrieval.infer import SemanticRetriever

            engine = SemanticRetriever()
        self._engine = engine
        self.last_hits: list[Any] = []

    def retrieve(
        self,
        query: str,
        user_report_values: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        hits = self._engine.retrieve(
            query=query,
            user_report_values=user_report_values,
            top_k=top_k,
        )
        self.last_hits = hits
        return [
            RetrievedDocument(
                text=h.text,
                source=h.source,
                source_url=h.source_url,
                score=float(h.similarity),
                is_user_data=bool(h.is_user_data),
            )
            for h in hits
        ]


class FallbackRetriever:
    """Semantic primary → BM25 on failure or empty."""

    def __init__(
        self,
        primary: SemanticRetrieverAdapter,
        fallback: BM25Retriever | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or BM25Retriever()
        self.last_path = "unset"

    def retrieve(
        self,
        query: str,
        user_report_values: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        try:
            docs = self.primary.retrieve(query, user_report_values, top_k)
            if docs:
                self.last_path = "semantic"
                return docs
            logger.warning("Semantic retrieval empty; falling back to BM25")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Semantic retrieval failed (%s); falling back to BM25",
                type(exc).__name__,
            )
        self.last_path = "bm25_fallback"
        return self.fallback.retrieve(query, user_report_values, top_k)
