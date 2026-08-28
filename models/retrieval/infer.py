"""
SemanticRetriever — embedding + vector index medical retrieval.

Does not answer medically; only ranks context chunks for synthesis.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .chunking import load_kb_directory
from .config_loader import artifacts_dir, load_config
from .embeddings import create_embedding_backend, load_embedding_backend
from .schema import RetrievalHit
from .vector_store import create_store, load_store


def _user_value_hits(
    query: str,
    user_report_values: list[dict[str, Any]] | None,
) -> list[RetrievalHit]:
    if not user_report_values:
        return []
    # Reuse synonym map lightly without importing OCR packages deeply
    try:
        from services.ai_service.rag.retriever import _test_name_matches_query
    except Exception:

        def _test_name_matches_query(name: str, q: str) -> bool:  # type: ignore
            return (name or "").lower() in (q or "").lower()

    q = (query or "").lower()
    hits: list[RetrievalHit] = []
    for i, rv in enumerate(user_report_values):
        test_name = rv.get("test_name", "") or ""
        if not test_name:
            continue
        if not _test_name_matches_query(test_name, q):
            continue
        test_date = rv.get("date_of_test")
        date_str = str(test_date) if test_date else "unknown date"
        value = rv.get("value_numeric", rv.get("value_text", ""))
        unit = rv.get("unit", "")
        text = f"Your {test_name} result from {date_str}: {value} {unit}".strip()
        hits.append(
            RetrievalHit(
                document_id="user_values",
                chunk_id=f"user::{i}",
                text=text,
                source="Your lab results",
                source_url=None,
                similarity=0.85,
                metadata={"test_name": test_name},
                is_user_data=True,
            )
        )
    return hits


def resolve_repo_path(path_str: str | Path) -> Path:
    """Resolve config paths relative to package dir (../../datasets/...), else repo root."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    pkg = Path(__file__).resolve().parent  # models/retrieval
    # Config YAML uses paths relative to this package (e.g. ../../datasets/...)
    if ".." in p.parts or p.parts[:1] == (".",):
        return (pkg / p).resolve()
    cand = (pkg / p).resolve()
    if cand.exists():
        return cand
    repo = pkg.parents[1]  # MediVault
    return (repo / p).resolve()


class SemanticRetriever:
    """
    Semantic medical retrieval engine.

    Pipeline: query → embed → vector search (FAISS/numpy) → top-k hits (+ user values).
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        auto_build_if_missing: bool = True,
    ) -> None:
        self.config = config or load_config(validate=True)
        self._embedder = None
        self._store = None
        self._chunks: dict[str, dict[str, Any]] = {}
        self.backend_name = "uninitialized"
        self.store_name = "uninitialized"
        self._load_or_build(auto_build_if_missing=auto_build_if_missing)

    def _load_or_build(self, *, auto_build_if_missing: bool) -> None:
        art = artifacts_dir(self.config)
        try:
            if (art / "chunks.json").exists() and (art / "embedder_meta.json").exists():
                self._embedder = load_embedding_backend(art)
                self._store = load_store(art)
                rows = json.loads((art / "chunks.json").read_text(encoding="utf-8"))
                self._chunks = {r["chunk_id"]: r for r in rows}
                self.backend_name = getattr(self._embedder, "name", "loaded")
                self.store_name = getattr(self._store, "name", "loaded")
                return
        except Exception:
            self._embedder = None
            self._store = None

        if not auto_build_if_missing:
            raise FileNotFoundError("Retrieval artifacts missing; run train.py")
        self.build_index()

    def build_index(self) -> Path:
        """Chunk KB, embed, and write vector index + chunk metadata."""
        cfg = self.config
        kb_dir = resolve_repo_path(cfg["paths"]["knowledge_base"])
        chunking = cfg.get("chunking") or {}
        chunks = load_kb_directory(
            kb_dir,
            target_words=int(chunking.get("target_words") or 300),
            overlap_words=int(chunking.get("overlap_words") or 50),
        )
        if not chunks:
            # Minimal fallback so service still starts
            chunks = [
                {
                    "document_id": "empty",
                    "chunk_id": "empty::0",
                    "source_title": "Empty KB",
                    "source_url": None,
                    "chunk_text": "No knowledge base documents found.",
                    "chunk_index": 0,
                    "metadata": {},
                }
            ]

        backend = create_embedding_backend(
            cfg.get("embedding_backend") or "auto", cfg
        )
        texts = [c["chunk_text"] for c in chunks]
        t0 = time.perf_counter()
        backend.fit(texts)
        vectors = backend.encode(texts)
        embed_ms = (time.perf_counter() - t0) * 1000

        store = create_store(cfg.get("vector_store") or "faiss")
        ids = [c["chunk_id"] for c in chunks]
        store.build(vectors, ids)

        art = artifacts_dir(cfg)
        art.mkdir(parents=True, exist_ok=True)
        backend.save(art)
        store.save(art)
        # also keep numpy copy for portability if faiss used
        if store.name == "faiss":
            from .vector_store import NumpyVectorStore

            np_store = NumpyVectorStore()
            np_store.build(vectors, ids)
            np_store.save(art)

        (art / "chunks.json").write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        meta = {
            "n_chunks": len(chunks),
            "embedding_backend": getattr(backend, "name", "unknown"),
            "vector_store": getattr(store, "name", "unknown"),
            "dim": int(vectors.shape[1]),
            "embed_build_ms": embed_ms,
            "primary_architecture": cfg.get("primary_architecture"),
            "fallback_architecture": cfg.get("fallback_architecture"),
        }
        (art / "index_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

        self._embedder = backend
        self._store = store
        self._chunks = {c["chunk_id"]: c for c in chunks}
        self.backend_name = getattr(backend, "name", "unknown")
        self.store_name = getattr(store, "name", "unknown")
        return art

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievalHit]:
        assert self._embedder is not None and self._store is not None
        k = int(top_k or self.config.get("default_top_k") or 5)
        qv = self._embedder.encode([query or ""])
        # over-fetch if filtering
        fetch_k = k * 3 if metadata_filter else k
        ranked = self._store.search(qv, top_k=fetch_k)[0]
        hits: list[RetrievalHit] = []
        for chunk_id, score in ranked:
            row = self._chunks.get(chunk_id)
            if not row:
                continue
            meta = dict(row.get("metadata") or {})
            if metadata_filter:
                ok = True
                for mk, mv in metadata_filter.items():
                    if str(meta.get(mk, row.get(mk, ""))).lower() != str(mv).lower():
                        ok = False
                        break
                if not ok:
                    continue
            hits.append(
                RetrievalHit(
                    document_id=str(row.get("document_id") or ""),
                    chunk_id=chunk_id,
                    text=str(row.get("chunk_text") or ""),
                    source=str(row.get("source_title") or "knowledge"),
                    source_url=row.get("source_url"),
                    similarity=float(score),
                    metadata=meta,
                    is_user_data=False,
                )
            )
            if len(hits) >= k:
                break
        return hits

    def retrieve(
        self,
        query: str,
        user_report_values: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        kb = self.search(query, top_k=top_k)
        user = _user_value_hits(query, user_report_values)
        merged = user + kb
        merged.sort(key=lambda h: h.similarity, reverse=True)
        return merged[:top_k]

    @property
    def index_size(self) -> int:
        return len(self._chunks)
