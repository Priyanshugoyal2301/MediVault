"""
packages/research-data/retrieval/contract.py

Versioned Retrieval Contract for Longitudinal Evidence Retrieval (CP-06).
Retrieves atomic Evidence Observations from a specific patient's longitudinal history.

Guarantees:
  1. Patient isolation: queries only search the target patient's evidence.
  2. Preserved provenance: each result links directly to a ResearchEvidenceRecord.
  3. Deterministic tie-breaking: identical scores produce identical rankings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol, Sequence, runtime_checkable

from packages.ml_interfaces.query import ClinicalQuery
from packages.research_data.models import ResearchEvidenceRecord


@dataclass
class RetrievalResult:
    """
    Standardized atomic retrieval result representing a single Evidence Observation.
    Preserves clinical metadata, relevance score, rank, and source provenance.
    """

    evidence_id: str
    patient_id: str
    score: float
    rank: int
    retrieval_method: str
    analyte_canonical: str | None
    concept_id: str | None
    loinc_code: str | None
    observation_date: str
    value: float | str | None
    unit: str | None
    flag: str | None
    source_provenance: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetrievalResult:
        return cls(
            evidence_id=data["evidence_id"],
            patient_id=data["patient_id"],
            score=float(data["score"]),
            rank=int(data["rank"]),
            retrieval_method=data["retrieval_method"],
            analyte_canonical=data.get("analyte_canonical"),
            concept_id=data.get("concept_id"),
            loinc_code=data.get("loinc_code"),
            observation_date=data["observation_date"],
            value=data.get("value"),
            unit=data.get("unit"),
            flag=data.get("flag"),
            source_provenance=data.get("source_provenance", ""),
            metadata=dict(data.get("metadata", {})),
        )


def parse_date_to_timestamp(date_str: str) -> float:
    """
    Helper to convert an ISO date or datetime string to a timestamp for tie-breaking.
    Fallback to 0.0 on malformed input.
    """
    if not date_str:
        return 0.0
    try:
        # Support full ISO datetime or YYYY-MM-DD
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").timestamp()
        except Exception:
            return 0.0


def sort_and_rank_results(
    results: list[RetrievalResult], top_k: int = 10
) -> list[RetrievalResult]:
    """
    Applies deterministic tie-breaking and assigns 1-indexed ranks.
    Ordering precedence:
      1. Descending score (rounded to 6 decimal places)
      2. Descending observation date timestamp (more recent first)
      3. Ascending evidence_id (lexicographical tie-breaker)
    """
    sorted_res = sorted(
        results,
        key=lambda r: (
            -round(r.score, 6),
            -parse_date_to_timestamp(r.observation_date),
            r.evidence_id,
        ),
    )
    ranked: list[RetrievalResult] = []
    for rank_idx, item in enumerate(sorted_res[:top_k], start=1):
        item.rank = rank_idx
        ranked.append(item)
    return ranked


def filter_patient_evidence(
    evidence: Sequence[ResearchEvidenceRecord], target_patient_id: str
) -> list[ResearchEvidenceRecord]:
    """
    Strict patient-scoped filtering.
    Retrieval MUST NEVER consider observations from any patient other than target_patient_id.
    """
    if not target_patient_id:
        return []
    return [r for r in evidence if r.source_patient_id == target_patient_id]


@runtime_checkable
class EvidenceRetriever(Protocol):
    """
    Versioned Retrieval Contract (CP-06).
    Every retriever in the experimental progression implements this interface.
    """

    def retrieve(
        self,
        query: ClinicalQuery,
        evidence: Sequence[ResearchEvidenceRecord],
        top_k: int = 10,
        patient_id: str | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieves top_k evidence records for a patient query.
        """
        ...
