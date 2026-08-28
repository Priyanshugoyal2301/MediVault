"""
ai-service/rag/retriever.py

Hybrid retrieval for health Q&A (Plan B):
  1. BM25 lexical ranking over curated KB chunks (+ intent boost)
  2. Optional dense cosine ranking when MEDIVAULT_USE_DENSE=1 and embeddings exist
  3. Keyword match against the user's own report_values (owner-scoped)

Default path is BM25+intent — scientifically appropriate for ~O(10) chunks and
demo-reliable (no HF download / MD5 cosine theater).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .bm25 import BM25Index
from .intent import intent_boost_for_text

# Optional dense path — only imported when embeddings present / flag set
try:
    from .embedder import embed_text as _dense_embed_text
except Exception:  # noqa: BLE001
    _dense_embed_text = None  # type: ignore[assignment]


@dataclass(frozen=True)
class RetrievedChunk:
    """A single retrieved chunk from the knowledge base or user's reports."""

    text: str
    source: str
    source_url: str | None = None
    score: float = 0.0
    is_user_data: bool = False


_knowledge_chunks: list[dict] = []
_bm25_index: BM25Index | None = None
_retriever_mode: str = "bm25"  # "bm25" | "dense" | "hybrid"


def load_knowledge_base(chunks: list[dict], mode: str | None = None) -> None:
    """Load knowledge base chunks and build retrieval indexes.

    Each chunk dict must have: chunk_text, source_title, source_url.
    embedding is optional (required only for dense/hybrid modes).
    """
    global _knowledge_chunks, _bm25_index, _retriever_mode
    _knowledge_chunks = list(chunks)
    _bm25_index = BM25Index.build([c.get("chunk_text", "") for c in _knowledge_chunks])

    if mode:
        _retriever_mode = mode
    else:
        use_dense = os.getenv("MEDIVAULT_USE_DENSE", "0").strip().lower() in (
            "1", "true", "yes",
        )
        has_emb = any(c.get("embedding") for c in _knowledge_chunks)
        if use_dense and has_emb:
            _retriever_mode = "hybrid"
        else:
            _retriever_mode = "bm25"


def knowledge_base_stats() -> dict:
    return {
        "kb_chunks": len(_knowledge_chunks),
        "kb_ready": len(_knowledge_chunks) > 0,
        "kb_retriever": _retriever_mode,
    }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize_scores(raw: list[float]) -> list[float]:
    if not raw:
        return []
    lo, hi = min(raw), max(raw)
    if hi <= lo:
        return [0.0 for _ in raw]
    return [(s - lo) / (hi - lo) for s in raw]


def retrieve(
    query: str,
    user_report_values: list[dict] | None = None,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """Retrieve the most relevant chunks for *query*."""
    results: list[RetrievedChunk] = []

    if _knowledge_chunks and _bm25_index is not None:
        results.extend(_retrieve_kb(query, top_k=top_k))

    if user_report_values:
        query_lower = query.lower()
        for rv in user_report_values:
            test_name = rv.get("test_name", "")
            if not test_name:
                continue
            if _test_name_matches_query(test_name, query_lower):
                test_date = rv.get("date_of_test")
                date_str = str(test_date) if test_date else "unknown date"
                value = rv.get("value_numeric", rv.get("value_text", ""))
                unit = rv.get("unit", "")
                text = (
                    f"Your {test_name} result from {date_str}: "
                    f"{value} {unit}".strip()
                )
                results.append(RetrievedChunk(
                    text=text,
                    source=f"Your report from {date_str}",
                    source_url=None,
                    score=0.85,
                    is_user_data=True,
                ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]


def _retrieve_kb(query: str, top_k: int) -> list[RetrievedChunk]:
    n = len(_knowledge_chunks)
    assert _bm25_index is not None

    bm25_raw = _bm25_index.score(query)
    bm25_norm = _normalize_scores(bm25_raw)

    dense_norm = [0.0] * n
    if _retriever_mode in ("dense", "hybrid") and _dense_embed_text is not None:
        try:
            q_emb = _dense_embed_text(query)
            dense_raw = []
            for chunk in _knowledge_chunks:
                emb = chunk.get("embedding")
                if emb:
                    dense_raw.append(_cosine_similarity(q_emb, emb))
                else:
                    dense_raw.append(0.0)
            dense_norm = _normalize_scores(dense_raw)
        except Exception:  # noqa: BLE001
            dense_norm = [0.0] * n

    scored: list[tuple[float, dict]] = []
    for i, chunk in enumerate(_knowledge_chunks):
        boost = intent_boost_for_text(
            query,
            chunk.get("chunk_text", ""),
            chunk.get("source_title", ""),
        )
        if _retriever_mode == "dense":
            score = dense_norm[i] + boost
        elif _retriever_mode == "hybrid":
            # Prefer BM25 on tiny corpora; dense as mild rerank
            score = 0.7 * bm25_norm[i] + 0.3 * dense_norm[i] + boost
        else:
            score = bm25_norm[i] + boost
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[RetrievedChunk] = []
    for score, chunk in scored[:top_k]:
        if score <= 0:
            continue
        out.append(RetrievedChunk(
            text=chunk["chunk_text"],
            source=chunk.get("source_title", "Knowledge Base"),
            source_url=chunk.get("source_url"),
            score=round(float(score), 4),
            is_user_data=False,
        ))
    return out


def _test_name_matches_query(test_name: str, query_lower: str) -> bool:
    name_lower = test_name.lower()
    if name_lower in query_lower:
        return True

    _SYNONYMS: dict[str, list[str]] = {
        "haemoglobin": ["hb", "hemoglobin", "haemoglobin"],
        "total cholesterol": ["cholesterol", "tc"],
        "ldl cholesterol": ["ldl", "bad cholesterol"],
        "hdl cholesterol": ["hdl", "good cholesterol"],
        "triglycerides": ["tg", "triglyceride"],
        "tsh": ["thyroid", "tsh"],
        "hba1c": ["a1c", "hba1c", "glycated", "sugar test"],
        "fasting blood glucose": ["fasting glucose", "fbs", "blood sugar"],
        "white blood cell": ["wbc", "white blood", "leucocyte"],
        "red blood cell": ["rbc", "red blood"],
        "platelet": ["plt", "platelet"],
        "esr": ["sedimentation", "esr"],
    }

    for canonical, synonyms in _SYNONYMS.items():
        if name_lower.startswith(canonical) or canonical.startswith(name_lower):
            for syn in synonyms:
                if syn in query_lower:
                    return True
    return False
