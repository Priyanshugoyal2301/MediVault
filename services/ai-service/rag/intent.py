"""
Lightweight intent router for lab-panel FAQ queries.

Boosts BM25 scores when the query clearly maps to a panel/topic that a chunk
covers. Deterministic, no ML model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass(frozen=True)
class Intent:
    name: str
    keywords: tuple[str, ...]
    boost: float = 0.15


# Ordered: first match wins for primary intent; all matching intents contribute boosts.
_INTENTS: tuple[Intent, ...] = (
    Intent("cbc", ("haemoglobin", "hemoglobin", "hb", "wbc", "rbc", "platelet", "mcv", "esr", "pcv", "neutrophil", "lymphocyte", "eosinophil", "monocyte", "cbc"), 0.18),
    Intent("lipid", ("ldl", "hdl", "cholesterol", "triglyceride", "lipid", "vldl", "non-hdl"), 0.18),
    Intent("thyroid", ("tsh", "thyroid", "t3", "t4", "hypothyroid", "hyperthyroid", "anti-tpo", "hashimoto"), 0.18),
    Intent("hba1c", ("hba1c", "a1c", "diabetes", "glycated", "glucose", "sugar", "pre-diabetes", "prediabetes"), 0.18),
    Intent("general", ("exercise", "diet", "lifestyle", "doctor", "consult", "healthy"), 0.05),
)


def detect_intents(query: str) -> list[Intent]:
    q = (query or "").lower()
    tokens = set(_WORD.findall(q))
    hits: list[Intent] = []
    for intent in _INTENTS:
        for kw in intent.keywords:
            if " " in kw or "-" in kw:
                if kw in q:
                    hits.append(intent)
                    break
            elif kw in tokens or kw in q:
                hits.append(intent)
                break
    return hits


def intent_boost_for_text(query: str, chunk_text: str, source_title: str = "") -> float:
    """Return additive score boost if chunk appears to match detected intents."""
    intents = detect_intents(query)
    if not intents:
        return 0.0
    hay = f"{source_title} {chunk_text}".lower()
    boost = 0.0
    for intent in intents:
        # Chunk relevance: any intent keyword appears in chunk/source
        if any(kw in hay for kw in intent.keywords):
            boost += intent.boost
    return min(boost, 0.35)
