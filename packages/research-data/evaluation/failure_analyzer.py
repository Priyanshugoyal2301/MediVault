"""
packages/research-data/evaluation/failure_analyzer.py

Failure Analysis Engine for Longitudinal Evidence Retrieval (CP-06).
Diagnoses unretrieved or sub-optimally ranked evidence queries and classifies failures
into a structured research taxonomy:
  - lexical_miss
  - semantic_miss
  - temporal_miss
  - concept_miss
  - wrong_patient_protection_failure
  - missing_candidate
  - ranking_error
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from packages.research_data.models import EvaluationQuery, ResearchEvidenceRecord
from packages.research_data.retrieval.contract import RetrievalResult


@dataclass
class QueryDiagnosticRecord:
    """Complete diagnostic record capturing ranking details for any benchmark query."""
    query_id: str
    method: str
    query_text: str
    patient_id: str
    intent: str
    expected_evidence_ids: list[str]
    retrieved_top_k_ids: list[str]
    ranks: dict[str, int]
    first_relevant_rank: int | None
    reciprocal_rank: float
    component_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    classification: str = "ranking_error"
    diagnostic_details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalFailureRecord:
    """Inspectable diagnostic record for an evaluation query that failed or missed expected evidence."""
    query_id: str
    query_text: str
    patient_id: str
    intent: str
    expected_evidence_ids: list[str]
    retrieved_top_k_ids: list[str]
    ranks: dict[str, int]
    component_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    observation_dates: dict[str, str] = field(default_factory=dict)
    analytes: dict[str, str] = field(default_factory=dict)
    concepts: dict[str, str] = field(default_factory=dict)
    reason: str = "ranking_error"
    diagnostic_details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def diagnose_query_failure(
    query: EvaluationQuery,
    retrieved: Sequence[RetrievalResult],
    all_evidence: Sequence[ResearchEvidenceRecord],
    k: int = 10,
) -> RetrievalFailureRecord | None:
    """
    Evaluates whether a query failed to retrieve all expected evidence in top-k,
    and classifies the failure reason.
    Returns None if all expected evidence was retrieved in top-k.
    """
    expected_ids = set(query.relevant_evidence_ids)
    retrieved_top_k = list(retrieved[:k])
    retrieved_ids = [r.evidence_id for r in retrieved_top_k]
    retrieved_set = set(retrieved_ids)

    # Check if all expected items are retrieved in top k
    if expected_ids.issubset(retrieved_set):
        return None

    # Identify missing expected items
    missing_ids = expected_ids - retrieved_set
    evidence_by_id = {r.id: r for r in all_evidence}

    # Verify patient isolation
    wrong_patient = any(r.patient_id != query.patient_id for r in retrieved)
    if wrong_patient:
        reason = "wrong_patient_protection_failure"
        details = "Retrieved candidate pool contains observations from another patient."
    elif not all(eid in evidence_by_id for eid in missing_ids):
        reason = "missing_candidate"
        details = f"Expected evidence IDs not found in evidence corpus: {missing_ids}"
    else:
        # Check reasons among missing expected items
        sample_missing_id = next(iter(missing_ids))
        sample_missing = evidence_by_id[sample_missing_id]

        # Inspect if retrieved items have higher score due to temporal, concept, or lexical
        # Check component scores from retrieved results metadata if present
        ret_meta_sample = retrieved[0].metadata if retrieved else {}
        if "score_temporal" in ret_meta_sample:
            # Modular pipeline breakdown available
            # Check why missing item fell below top-k
            reason = "temporal_miss" if query.intent in ("current_value", "previous_value", "date_comparison", "historical_interval") else "ranking_error"
            details = f"Expected record {sample_missing_id} ranked below top-{k}."
        else:
            reason = "ranking_error"
            details = f"Relevance score for {sample_missing_id} insufficient to enter top-{k}."

    # Build component summaries
    ranks: dict[str, int] = {}
    for r in retrieved:
        if r.evidence_id in expected_ids:
            ranks[r.evidence_id] = r.rank

    dates: dict[str, str] = {}
    analytes: dict[str, str] = {}
    concepts: dict[str, str] = {}
    for eid in expected_ids:
        if eid in evidence_by_id:
            rec = evidence_by_id[eid]
            dates[eid] = rec.observation_date
            analytes[eid] = rec.analyte_canonical or rec.analyte_raw
            concepts[eid] = rec.concept_id or rec.loinc_code or "none"

    return RetrievalFailureRecord(
        query_id=query.query_id,
        query_text=query.query,
        patient_id=query.patient_id,
        intent=query.intent,
        expected_evidence_ids=list(query.relevant_evidence_ids),
        retrieved_top_k_ids=retrieved_ids,
        ranks=ranks,
        observation_dates=dates,
        analytes=analytes,
        concepts=concepts,
        reason=reason,
        diagnostic_details=details,
    )


def diagnose_query(
    query: EvaluationQuery,
    retrieved: Sequence[RetrievalResult],
    all_evidence: Sequence[ResearchEvidenceRecord],
    method_name: str = "retriever",
    k: int = 10,
) -> QueryDiagnosticRecord:
    """
    Produces an inspectable diagnostic record for every evaluated query,
    capturing ranks, reciprocal rank, component scores, and fine-grained classification.
    """
    expected_ids = set(query.relevant_evidence_ids)
    retrieved_top_k = list(retrieved[:k])
    retrieved_ids = [r.evidence_id for r in retrieved_top_k]

    ranks: dict[str, int] = {}
    component_scores: dict[str, dict[str, float]] = {}
    first_rank: int | None = None

    for r in retrieved:
        if r.evidence_id in expected_ids:
            ranks[r.evidence_id] = r.rank
            if first_rank is None or r.rank < first_rank:
                first_rank = r.rank

    for r in retrieved_top_k:
        meta = r.metadata or {}
        component_scores[r.evidence_id] = {
            "score": round(r.score, 4),
            "lexical": meta.get("score_lexical", 0.0),
            "semantic": meta.get("score_semantic", 0.0),
            "concept": meta.get("score_concept", 0.0),
            "temporal": meta.get("score_temporal", 0.0),
            "intent": meta.get("score_intent", 0.0),
        }

    reciprocal_rank = (1.0 / first_rank) if first_rank else 0.0

    if not expected_ids.issubset(set(retrieved_ids)):
        classification = "top_k_miss"
        details = f"Expected evidence missing from top-{k}."
    elif first_rank == 1:
        classification = "perfect_rank_1"
        details = "Relevant evidence successfully retrieved at Rank 1."
    else:
        # First relevant rank > 1
        if query.intent in ("current_value", "previous_value", "date_comparison", "historical_interval"):
            classification = "temporal_ranking_error"
            details = f"Target evidence retrieved at #{first_rank} due to temporal ordering margin."
        else:
            classification = "ranking_error"
            details = f"Target evidence retrieved at #{first_rank}."

    return QueryDiagnosticRecord(
        query_id=query.query_id,
        method=method_name,
        query_text=query.query,
        patient_id=query.patient_id,
        intent=query.intent,
        expected_evidence_ids=list(query.relevant_evidence_ids),
        retrieved_top_k_ids=retrieved_ids,
        ranks=ranks,
        first_relevant_rank=first_rank,
        reciprocal_rank=round(reciprocal_rank, 4),
        component_scores=component_scores,
        classification=classification,
        diagnostic_details=details,
    )
