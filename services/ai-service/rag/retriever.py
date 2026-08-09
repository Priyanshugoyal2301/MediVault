"""
ai-service/rag/retriever.py

Hybrid retrieval for health Q&A:
  1. Semantic search against knowledge_documents (cosine similarity via embeddings)
  2. Keyword search against the user's own report_values (test name matching)

Both result sets are merged, deduplicated, and ranked by relevance score.

PRIVACY RULE:
  User report data is ONLY retrieved for the requesting user (owner_id scoped).
  Knowledge documents are shared and have no owner_id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .embedder import embed_text


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetrievedChunk:
    """A single retrieved chunk from the knowledge base or user's reports."""

    text: str
    source: str          # e.g. "NHS Cholesterol Guidelines" or "Your report from 2025-01-15"
    source_url: str | None = None
    score: float = 0.0   # 0.0–1.0, higher is more relevant
    is_user_data: bool = False  # True if from user's own reports


# ---------------------------------------------------------------------------
# In-memory knowledge base (loaded at startup or by tests)
# ---------------------------------------------------------------------------

_knowledge_chunks: list[dict] = []  # [{chunk_text, source_title, source_url, embedding}, ...]


def load_knowledge_base(chunks: list[dict]) -> None:
    """Load pre-embedded knowledge base chunks into memory for retrieval.

    Each chunk dict must have: chunk_text, source_title, source_url, embedding (list[float]).
    Called once at startup or by the ingestion pipeline.
    """
    global _knowledge_chunks
    _knowledge_chunks = list(chunks)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    user_report_values: list[dict] | None = None,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """Retrieve the most relevant chunks for *query*.

    Args:
        query: The user's question text.
        user_report_values: Optional list of the user's own report_values dicts
            (from the health-service DB, already owner-scoped).
            Each dict should have: test_name, value_numeric, unit, date_of_test, panel.
        top_k: Maximum number of results to return.

    Returns:
        List of RetrievedChunk, sorted by score descending.
    """
    results: list[RetrievedChunk] = []

    # 1. Semantic search against knowledge base
    if _knowledge_chunks:
        query_embedding = embed_text(query)

        scored = []
        for chunk in _knowledge_chunks:
            if "embedding" in chunk and chunk["embedding"]:
                sim = _cosine_similarity(query_embedding, chunk["embedding"])
                scored.append((sim, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        for score, chunk in scored[:top_k]:
            results.append(RetrievedChunk(
                text=chunk["chunk_text"],
                source=chunk.get("source_title", "Knowledge Base"),
                source_url=chunk.get("source_url"),
                score=round(score, 4),
                is_user_data=False,
            ))

    # 2. Keyword search against user's own report values
    if user_report_values:
        query_lower = query.lower()
        # Extract test names mentioned in the query
        for rv in user_report_values:
            test_name = rv.get("test_name", "")
            if not test_name:
                continue
            # Check if the test name (or a fuzzy match) appears in the query
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
                    score=0.85,  # High relevance for user's own data
                    is_user_data=True,
                ))

    # Sort by score, take top_k
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]


def _test_name_matches_query(test_name: str, query_lower: str) -> bool:
    """Check if a test name is mentioned in the query (fuzzy keyword match)."""
    # Normalise test name for comparison
    name_lower = test_name.lower()

    # Direct substring match
    if name_lower in query_lower:
        return True

    # Common abbreviation / synonym mapping
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
