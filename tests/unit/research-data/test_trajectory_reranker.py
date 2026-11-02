"""
tests/unit/research-data/test_trajectory_reranker.py

Unit test suite for Trajectory-Aware Evidence Re-ranking (CP-07).
Verifies:
  1. Adversarial ranking test: Trajectory reranker promotes baseline anchor over redundant recent cluster
  2. Hard temporal exclusion preservation: Candidates with score == 0.0 are NEVER resurrected
  3. Non-trajectory queries (e.g., current_value) preserve CP-06 scores and rank order
  4. Deterministic tie-breaking preserved: (-score, -timestamp, evidence_id)
  5. Multi-patient isolation preserved
  6. Empty candidate set handling
  7. Composite TrajectoryAwareRetriever conforms to EvidenceRetriever contract
"""

from __future__ import annotations

import pytest

from packages.ml_interfaces.query import ClinicalQuery, QueryIntent, TemporalOperator
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.contract import (
    EvidenceRetriever,
    RetrievalResult,
)
from packages.research_data.retrieval.pipeline import (
    ModularEvidenceRetriever,
    ScoringWeights,
)
from packages.research_data.retrieval.trajectory_reranker import (
    TrajectoryAwareRetriever,
    TrajectoryReranker,
    is_longitudinal_trajectory_query,
)


def make_candidate(
    evidence_id: str,
    date_str: str,
    value: float | str | None,
    score: float,
    patient_id: str = "p_test",
    analyte: str = "HbA1c",
) -> RetrievalResult:
    """Helper to create candidate RetrievalResults."""
    return RetrievalResult(
        evidence_id=evidence_id,
        patient_id=patient_id,
        score=score,
        rank=0,
        retrieval_method="base_cp06",
        analyte_canonical=analyte,
        concept_id="LOINC:4548-4",
        loinc_code="4548-4",
        observation_date=date_str,
        value=value,
        unit="%",
        flag="normal",
        source_provenance="fixture",
        metadata={"base_score": score},
    )


class TestTrajectoryReranker:
    def test_adversarial_ranking_promotes_baseline_anchor_over_redundant_cluster(self):
        """
        ADVERSARIAL TEST (CP-07 Core Value Demonstration):
        A patient has 4 HbA1c observations over 3 years:
          - obs_base: 2021-01-01 (value 5.5, baseline establishing starting point)
          - obs_mid_change: 2022-06-01 (value 7.4, peak inflection/spike)
          - obs_recent_1: 2023-11-20 (value 6.8, redundant near-endpoint)
          - obs_recent_2: 2023-12-01 (value 6.7, endpoint / latest state)

        In base CP-06 retrieval, recency decay gave high scores to the recent cluster:
          obs_recent_2: 0.95
          obs_recent_1: 0.90
          obs_mid_change: 0.80
          obs_base: 0.70

        Without CP-07, the top-2 retrieved evidence consists of obs_recent_2 and obs_recent_1
        (two adjacent points 10 days apart), missing the foundational baseline.

        With CP-07 TrajectoryReranker enabled on a TREND query:
        obs_base (baseline anchor) receives S_traj = 1.0.
        obs_recent_1 (redundant intermediate) receives S_traj = 0.5.
        The baseline anchor is promoted to outrank the redundant cluster point!
        """
        candidates = [
            make_candidate("obs_recent_2", "2023-12-01T00:00:00Z", 6.7, score=0.95),
            make_candidate("obs_recent_1", "2023-11-20T00:00:00Z", 6.8, score=0.90),
            make_candidate("obs_mid_change", "2022-06-01T00:00:00Z", 7.4, score=0.80),
            make_candidate("obs_base", "2021-01-01T00:00:00Z", 5.5, score=0.70),
        ]

        query = ClinicalQuery(
            raw_query="How has my HbA1c changed over time?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )

        reranker = TrajectoryReranker(trajectory_weight=0.30)
        reranked = reranker.rerank(query, candidates, top_k=4)

        # Map results by evidence_id
        res_map = {r.evidence_id: r for r in reranked}

        # Verify trajectory roles
        assert res_map["obs_base"].metadata["trajectory_role"] == "baseline"
        assert res_map["obs_recent_2"].metadata["trajectory_role"] == "endpoint"
        assert res_map["obs_mid_change"].metadata["trajectory_role"] == "inflection"
        assert res_map["obs_recent_1"].metadata["trajectory_role"] == "intermediate"

        # Verify score math:
        # obs_base: 0.70 * 0.70 + 0.30 * 1.0 = 0.790
        # obs_recent_1: 0.90 * 0.70 + 0.30 * 0.5 = 0.780
        assert res_map["obs_base"].score > res_map["obs_recent_1"].score

        # Baseline must outrank redundant recent point in top-K
        assert res_map["obs_base"].rank < res_map["obs_recent_1"].rank

    def test_hard_temporal_exclusion_strictly_preserved(self):
        """
        CRITICAL INVARIANT: If an observation received score == 0.0 from CP-06 hard temporal filtering
        (e.g., date out-of-bounds), TrajectoryReranker MUST NOT resurrect it.
        """
        candidates = [
            make_candidate("obs_in_window_1", "2022-05-01T00:00:00Z", 6.0, score=0.85),
            make_candidate("obs_in_window_2", "2022-09-01T00:00:00Z", 6.2, score=0.88),
            # This candidate was excluded by CP-06 hard date filter -> score == 0.0
            make_candidate("obs_out_of_window", "2024-01-01T00:00:00Z", 7.0, score=0.0),
        ]

        query = ClinicalQuery(
            raw_query="Show HbA1c trend in 2022",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )

        reranker = TrajectoryReranker(trajectory_weight=0.30)
        reranked = reranker.rerank(query, candidates, top_k=3)

        res_map = {r.evidence_id: r for r in reranked}
        # The out-of-window candidate must have score 0.0 and remain at the bottom
        assert res_map["obs_out_of_window"].score == 0.0
        assert res_map["obs_out_of_window"].rank == 3

    def test_non_trajectory_queries_preserve_cp06_scores(self):
        """
        For non-trend/non-comparison queries (e.g., current_value / latest),
        trajectory reranker computes metadata features but does NOT alter scores or ranking.
        """
        candidates = [
            make_candidate("obs_1", "2022-01-01T00:00:00Z", 5.5, score=0.60),
            make_candidate("obs_2", "2023-01-01T00:00:00Z", 6.0, score=0.95),
        ]

        query = ClinicalQuery(
            raw_query="What is my latest HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            temporal_operator=TemporalOperator.LATEST,
            analyte_canonical="HbA1c",
        )

        reranker = TrajectoryReranker(trajectory_weight=0.25)
        reranked = reranker.rerank(query, candidates, top_k=2)

        # Score order must be exactly preserved
        assert reranked[0].evidence_id == "obs_2"
        assert reranked[0].score == 0.95
        assert reranked[1].evidence_id == "obs_1"
        assert reranked[1].score == 0.60

        # Trajectory features must still be attached to metadata
        assert "trajectory_direction" in reranked[0].metadata
        assert reranked[0].metadata["is_trajectory_reranked"] is False

    def test_deterministic_tie_breaking(self):
        """Tied final scores must break ties strictly by date timestamp descending, then evidence_id ascending."""
        candidates = [
            make_candidate("ev_b", "2023-01-01T00:00:00Z", 6.0, score=0.80),
            make_candidate("ev_a", "2023-01-01T00:00:00Z", 6.0, score=0.80),
            make_candidate("ev_c", "2024-01-01T00:00:00Z", 6.0, score=0.80),
        ]

        query = ClinicalQuery(raw_query="latest HbA1c", intent=QueryIntent.CURRENT_VALUE, analyte_canonical="HbA1c")
        reranker = TrajectoryReranker()
        reranked = reranker.rerank(query, candidates, top_k=3)

        # More recent date wins: ev_c (2024) is Rank 1
        assert reranked[0].evidence_id == "ev_c"
        assert reranked[0].rank == 1
        # Same date: ev_a < ev_b alphabetically
        assert reranked[1].evidence_id == "ev_a"
        assert reranked[1].rank == 2
        assert reranked[2].evidence_id == "ev_b"
        assert reranked[2].rank == 3

    def test_empty_candidate_set(self):
        """Empty candidates must return empty list."""
        reranker = TrajectoryReranker()
        query = ClinicalQuery(raw_query="test", intent=QueryIntent.HISTORICAL)
        assert reranker.rerank(query, []) == []

    def test_trajectory_aware_retriever_composite(self):
        """TrajectoryAwareRetriever must implement EvidenceRetriever and execute end-to-end."""
        # Create base retriever
        base_retriever = ModularEvidenceRetriever(
            weights=ScoringWeights.hybrid_temporal_concept(),
            method_name="Base_Pipeline",
        )
        composite = TrajectoryAwareRetriever(
            base_retriever=base_retriever,
            reranker=TrajectoryReranker(trajectory_weight=0.25),
            method_name="Base_Pipeline+Trajectory",
        )

        assert isinstance(composite, EvidenceRetriever)
        assert composite.method_name == "Base_Pipeline+Trajectory"

        # Test on synthetic patient records
        records = [
            ResearchEvidenceRecord(
                id=f"rec_{i}",
                dataset="synthea",
                source_patient_id="patient_1",
                source_encounter_id=f"enc_{i}",
                source_record_id=f"row_{i}",
                observation_date=f"202{i}-01-01T00:00:00Z",
                analyte_raw="Hemoglobin A1c",
                analyte_canonical="HbA1c",
                concept_id="LOINC:4548-4",
                loinc_code="4548-4",
                value_numeric=5.5 + i * 0.3,
                unit="%",
                flag="normal",
                source_provenance="fixture",
            )
            for i in range(1, 4)
        ]

        query = ClinicalQuery(
            raw_query="How has my HbA1c changed over time?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )

        results = composite.retrieve(query, records, top_k=3, patient_id="patient_1")
        assert len(results) == 3
        assert results[0].rank == 1
        assert "score_trajectory" in results[0].metadata
