"""Map ML ranking output → NormalizationResult."""

from __future__ import annotations

from typing import Any, Sequence

from .schema import AlternativeMatch, NormalizationResult, NormalizationStatus
from .vocabulary import loinc_for


def build_result(
    raw_name: str,
    ranked: Sequence[tuple[str, float]],
    *,
    backend: str,
    min_confidence: float,
    metadata: dict[str, Any] | None = None,
) -> NormalizationResult:
    """
    ranked: list of (canonical, score) best-first.
    score expected in [0, 1].
    """
    ranked = list(ranked)
    if not ranked:
        return NormalizationResult(
            raw_name=raw_name,
            canonical_name=(raw_name or "").strip() or raw_name,
            confidence=0.0,
            loinc=None,
            alternatives=[],
            status=NormalizationStatus.UNKNOWN,
            unknown_term=True,
            backend=backend,
            metadata=metadata or {},
        )

    top_name, top_score = ranked[0]
    alts = [
        AlternativeMatch(
            canonical_name=n,
            confidence=float(s),
            loinc=loinc_for(n),
        )
        for n, s in ranked[1:4]
    ]

    if top_score >= min_confidence:
        return NormalizationResult(
            raw_name=raw_name,
            canonical_name=top_name,
            confidence=float(top_score),
            loinc=loinc_for(top_name),
            alternatives=alts,
            status=NormalizationStatus.NORMALIZED,
            unknown_term=False,
            backend=backend,
            metadata=metadata or {},
        )

    # Low-confidence: do not invent — pass through surface
    surface = (raw_name or "").strip()
    return NormalizationResult(
        raw_name=raw_name,
        canonical_name=surface,
        confidence=float(top_score),
        loinc=None,
        alternatives=[
            AlternativeMatch(canonical_name=top_name, confidence=float(top_score), loinc=loinc_for(top_name)),
            *alts,
        ],
        status=NormalizationStatus.UNKNOWN,
        unknown_term=True,
        backend=backend,
        metadata={**(metadata or {}), "best_guess": top_name},
    )
