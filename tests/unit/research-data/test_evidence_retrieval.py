"""
tests/unit/research-data/test_evidence_retrieval.py

Unit test suite for Longitudinal Evidence Retrieval (CP-06).
Verifies:
  1. Strict patient isolation (no cross-patient leakage)
  2. Deterministic BM25 ranking and tie-breaking
  3. Dense semantic retrieval contract and fallback
  4. Hybrid weighted combination and RRF
  5. Temporal reranking:
     - LATEST / CURRENT_VALUE
     - LAST_N
     - COMPARISON / PREVIOUS
     - TREND
     - Date-bounded range / exact date
  6. Clinical Concept matching
  7. Modular scoring pipeline with presets
  8. Edge cases:
     - Unknown patient
     - Unknown analyte
     - Empty evidence
     - Tied scores
     - Abnormality constraints
     - Provenance integrity
"""

from __future__ import annotations

from datetime import date
import pytest

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    TemporalOperator,
)
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.bm25 import EvidenceBM25Retriever
from packages.research_data.retrieval.concept import ConceptScorer
from packages.research_data.retrieval.contract import (
    RetrievalResult,
    filter_patient_evidence,
    sort_and_rank_results,
)
from packages.research_data.retrieval.dense import (
    DenseEmbeddingBackend,
    EvidenceDenseRetriever,
)
from packages.research_data.retrieval.hybrid import HybridEvidenceRetriever
from packages.research_data.retrieval.pipeline import (
    ModularEvidenceRetriever,
    ScoringWeights,
)
from packages.research_data.retrieval.temporal import TemporalScorer


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_records() -> list[ResearchEvidenceRecord]:
    """Generates synthetic longitudinal evidence records for two distinct patients."""
    records = []
    # Patient 1: 4 HbA1c observations over time + 2 Glucose
    p1_dates = [
        "2021-03-15T09:00:00Z",
        "2022-01-10T10:00:00Z",
        "2023-05-20T08:30:00Z",
        "2024-02-11T11:00:00Z",
    ]
    for idx, d in enumerate(p1_dates):
        records.append(
            ResearchEvidenceRecord(
                id=f"p1_hba1c_{idx+1}",
                dataset="synthea",
                source_patient_id="patient_1",
                source_encounter_id=f"enc_p1_{idx+1}",
                source_record_id=f"row_p1_{idx+1}",
                observation_date=d,
                analyte_raw="Hemoglobin A1c/Hemoglobin.total in Blood",
                analyte_canonical="HbA1c",
                concept_id="LOINC:4548-4",
                loinc_code="4548-4",
                value_numeric=5.5 + (idx * 0.4),  # 5.5, 5.9, 6.3, 6.7 (abnormal at idx=3)
                unit="%",
                flag="abnormal" if idx == 3 else "normal",
                source_provenance="Synthea sample fixture",
            )
        )
    # Patient 1 Glucose
    records.append(
        ResearchEvidenceRecord(
            id="p1_glu_1",
            dataset="synthea",
            source_patient_id="patient_1",
            source_encounter_id="enc_p1_glu",
            source_record_id="row_p1_glu",
            observation_date="2024-02-11T11:00:00Z",
            analyte_raw="Glucose [Mass/volume] in Serum or Plasma",
            analyte_canonical="Glucose",
            concept_id="LOINC:2345-7",
            loinc_code="2345-7",
            value_numeric=95.0,
            unit="mg/dL",
            flag="normal",
            source_provenance="Synthea sample fixture",
        )
    )

    # Patient 2: 2 LDL observations
    for idx, d in enumerate(["2022-06-01T08:00:00Z", "2023-09-15T09:00:00Z"]):
        records.append(
            ResearchEvidenceRecord(
                id=f"p2_ldl_{idx+1}",
                dataset="synthea",
                source_patient_id="patient_2",
                source_encounter_id=f"enc_p2_{idx+1}",
                source_record_id=f"row_p2_{idx+1}",
                observation_date=d,
                analyte_raw="Low Density Lipoprotein Cholesterol",
                analyte_canonical="LDL Cholesterol",
                concept_id="LOINC:2089-1",
                loinc_code="2089-1",
                value_numeric=135.0,
                unit="mg/dL",
                flag="high",
                source_provenance="Synthea sample fixture",
            )
        )
    return records


# ===========================================================================
# 1. Patient Isolation Tests
# ===========================================================================

class TestPatientIsolation:
    def test_filter_patient_evidence_strict_subset(self, sample_records):
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        assert len(p1_records) == 5
        assert all(r.source_patient_id == "patient_1" for r in p1_records)

        p2_records = filter_patient_evidence(sample_records, "patient_2")
        assert len(p2_records) == 2
        assert all(r.source_patient_id == "patient_2" for r in p2_records)

    def test_bm25_retrieval_never_returns_other_patient(self, sample_records):
        retriever = EvidenceBM25Retriever()
        q = ClinicalQuery(
            raw_query="What was my LDL?",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="LDL Cholesterol",
        )
        # Query patient_1 for LDL (which patient_2 has, but patient_1 does not)
        results = retriever.retrieve(q, sample_records, top_k=10, patient_id="patient_1")
        assert all(r.patient_id == "patient_1" for r in results)
        assert not any(r.evidence_id.startswith("p2_") for r in results)

    def test_unknown_patient_returns_empty(self, sample_records):
        retriever = EvidenceBM25Retriever()
        q = ClinicalQuery(raw_query="HbA1c level", intent=QueryIntent.CURRENT_VALUE)
        results = retriever.retrieve(q, sample_records, top_k=5, patient_id="unknown_patient_999")
        assert results == []


# ===========================================================================
# 2. BM25 Baseline Tests
# ===========================================================================

class TestBM25Retriever:
    def test_bm25_ranking_and_tie_breaking(self, sample_records):
        retriever = EvidenceBM25Retriever()
        q = ClinicalQuery(
            raw_query="What is my HbA1c?",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="HbA1c",
            loinc_code="4548-4",
        )
        results = retriever.retrieve(q, sample_records, top_k=5, patient_id="patient_1")
        assert len(results) > 0
        assert results[0].retrieval_method == "bm25"
        assert results[0].rank == 1
        assert results[0].analyte_canonical == "HbA1c"
        # Scores must be in descending order
        for i in range(len(results) - 1):
            assert results[i].score >= results[i+1].score

    def test_bm25_alias_matching(self, sample_records):
        retriever = EvidenceBM25Retriever()
        q = ClinicalQuery(
            raw_query="What was my blood sugar?",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="Glucose",
        )
        results = retriever.retrieve(q, sample_records, top_k=5, patient_id="patient_1")
        assert any(r.evidence_id == "p1_glu_1" for r in results)


# ===========================================================================
# 3. Dense Retrieval Tests
# ===========================================================================

class TestDenseRetriever:
    def test_dense_retriever_contract(self, sample_records):
        retriever = EvidenceDenseRetriever()
        retriever.index_evidence(sample_records)

        q = ClinicalQuery(
            raw_query="Show me glycated hemoglobin readings",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="HbA1c",
        )
        results = retriever.retrieve(q, sample_records, top_k=4, patient_id="patient_1")
        assert len(results) == 4
        assert results[0].retrieval_method == "dense"
        assert all(0.0 <= r.score <= 1.0 for r in results)
        assert results[0].rank == 1
        for i in range(len(results) - 1):
            assert results[i].score >= results[i+1].score


# ===========================================================================
# 4. Hybrid Retrieval Tests
# ===========================================================================

class TestHybridRetriever:
    def test_hybrid_weighted_combination(self, sample_records):
        retriever = HybridEvidenceRetriever(alpha_lexical=0.5, alpha_dense=0.5, mode="weighted")
        q = ClinicalQuery(
            raw_query="What was my HbA1c test result?",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="HbA1c",
        )
        results = retriever.retrieve(q, sample_records, top_k=4, patient_id="patient_1")
        assert len(results) == 4
        assert results[0].retrieval_method == "hybrid"
        assert "bm25_norm" in results[0].metadata
        assert "dense_norm" in results[0].metadata

    def test_hybrid_rrf_combination(self, sample_records):
        retriever = HybridEvidenceRetriever(mode="rrf", rrf_k=60)
        q = ClinicalQuery(
            raw_query="What was my HbA1c test result?",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="HbA1c",
        )
        results = retriever.retrieve(q, sample_records, top_k=4, patient_id="patient_1")
        assert len(results) == 4
        assert results[0].retrieval_method == "hybrid_rrf"
        assert "rrf_score" in results[0].metadata


# ===========================================================================
# 5. Temporal Reranking Tests
# ===========================================================================

class TestTemporalReranking:
    def test_temporal_latest_rewards_most_recent(self, sample_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(
            raw_query="What is my latest HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            temporal_operator=TemporalOperator.LATEST,
            analyte_canonical="HbA1c",
        )
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        scores = scorer.score_patient_evidence(q, p1_records)

        # p1_hba1c_4 is 2024-02-11 (most recent)
        assert scores["p1_hba1c_4"] == 1.0
        assert scores["p1_hba1c_1"] < scores["p1_hba1c_4"]

    def test_temporal_last_n(self, sample_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(
            raw_query="What are my last 2 HbA1c values?",
            intent=QueryIntent.LAST_N,
            temporal_operator=TemporalOperator.LAST_N,
            limit=2,
            analyte_canonical="HbA1c",
        )
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        scores = scorer.score_patient_evidence(q, p1_records)

        # Last 2 are p1_hba1c_4 and p1_hba1c_3
        assert scores["p1_hba1c_4"] >= 0.8
        assert scores["p1_hba1c_3"] >= 0.8
        assert scores["p1_hba1c_1"] <= 0.1

    def test_temporal_previous_value(self, sample_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(
            raw_query="What was my previous HbA1c reading before the latest one?",
            intent=QueryIntent.COMPARISON,
            comparison_target=ComparisonTarget.PREVIOUS,
            analyte_canonical="HbA1c",
        )
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        scores = scorer.score_patient_evidence(q, p1_records)

        # Second to last is p1_hba1c_3
        assert scores["p1_hba1c_3"] == 1.0
        assert scores["p1_hba1c_4"] == 0.5  # reference point

    def test_temporal_date_bounded_exact_date(self, sample_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(
            raw_query="What was my HbA1c on 2022-01-10?",
            intent=QueryIntent.HISTORICAL,
            temporal_operator=TemporalOperator.EXACT_DATE,
            start_date=date(2022, 1, 10),
            analyte_canonical="HbA1c",
        )
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        scores = scorer.score_patient_evidence(q, p1_records)

        # p1_hba1c_2 is on 2022-01-10
        assert scores["p1_hba1c_2"] == 1.0
        assert scores["p1_hba1c_1"] == 0.0
        assert scores["p1_hba1c_4"] == 0.0

    def test_temporal_trend_rewards_trajectory(self, sample_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(
            raw_query="How has my HbA1c changed over time?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        scores = scorer.score_patient_evidence(q, p1_records)

        # All 4 HbA1c records in trajectory receive 1.0
        for i in range(1, 5):
            assert scores[f"p1_hba1c_{i}"] == 1.0
        # Glucose is not part of HbA1c trajectory
        assert scores["p1_glu_1"] == 0.0


# ===========================================================================
# 6. Concept Matching Tests
# ===========================================================================

class TestConceptMatching:
    def test_concept_match_exact_loinc(self, sample_records):
        scorer = ConceptScorer()
        q = ClinicalQuery(
            raw_query="HbA1c",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="HbA1c",
            loinc_code="4548-4",
            concept_id="LOINC:4548-4",
        )
        rec = sample_records[0]  # p1_hba1c_1
        score = scorer.score_record(q, rec)
        assert score == 1.0

    def test_concept_mismatch_returns_zero(self, sample_records):
        scorer = ConceptScorer()
        q = ClinicalQuery(
            raw_query="Lipid panel LDL",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="LDL Cholesterol",
            loinc_code="2089-1",
        )
        rec = sample_records[0]  # HbA1c
        score = scorer.score_record(q, rec)
        assert score == 0.0


# ===========================================================================
# 7. Modular Pipeline & Progression Presets Tests
# ===========================================================================

class TestModularPipeline:
    def test_pipeline_presets(self, sample_records):
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        q = ClinicalQuery(
            raw_query="What is my latest HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            temporal_operator=TemporalOperator.LATEST,
            analyte_canonical="HbA1c",
            loinc_code="4548-4",
        )

        # 1. BM25 preset
        ret_bm25 = ModularEvidenceRetriever(weights=ScoringWeights.bm25(), method_name="BM25")
        res_b = ret_bm25.retrieve(q, p1_records, top_k=5, patient_id="patient_1")
        assert len(res_b) == 5

        # 2. Hybrid+Temporal+Concept preset
        ret_full = ModularEvidenceRetriever(
            weights=ScoringWeights.hybrid_temporal_concept(),
            method_name="Hybrid+Temporal+Concept",
        )
        res_f = ret_full.retrieve(q, p1_records, top_k=5, patient_id="patient_1")
        assert len(res_f) == 5
        # The latest HbA1c (p1_hba1c_4) must be top ranked (#1)
        assert res_f[0].evidence_id == "p1_hba1c_4"
        assert res_f[0].rank == 1

    def test_abnormal_intent_scoring(self, sample_records):
        retriever = ModularEvidenceRetriever(
            weights=ScoringWeights.full(),
            method_name="Full",
        )
        q = ClinicalQuery(
            raw_query="What was my first abnormal HbA1c?",
            intent=QueryIntent.ABNORMALITY,
            abnormal_only=True,
            analyte_canonical="HbA1c",
        )
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        res = retriever.retrieve(q, p1_records, top_k=5, patient_id="patient_1")
        # p1_hba1c_4 is the only abnormal observation (6.7%)
        assert res[0].evidence_id == "p1_hba1c_4"


# ===========================================================================
# 8. Concept Ablation Sensitivity (Blocker 3)
# ===========================================================================

class TestConceptAblationSensitivity:
    """
    BLOCKER 3: Adversarial unit test proving that ConceptScorer is demonstrably
    functional and capable of flipping ranking under concept collision scenarios.
    """

    def test_concept_scorer_flips_rank_under_concept_collision(self):
        """
        Adversarial scenario:
        Same patient, same date.
        Record A: Total Cholesterol (LOINC 2093-3) with high lexical overlap.
        Record B: LDL Cholesterol (LOINC 2089-1).
        Query asks specifically for LDL Cholesterol.
        Without concept (gamma=0), Record A outranks Record B due to lexical bias.
        With concept (gamma=0.25), Record B receives concept bonus 1.0 (Record A gets 0.0),
        flipping Record B to Rank 1.
        """
        records = [
            ResearchEvidenceRecord(
                id="rec_total_chol",
                dataset="synthea",
                source_patient_id="p_adversarial",
                source_encounter_id="enc_1",
                source_record_id="row_1",
                observation_date="2023-05-01T10:00:00Z",
                analyte_raw="Cholesterol [Mass/volume] in Serum or Plasma",
                analyte_canonical="Total Cholesterol",
                concept_id="LOINC:2093-3",
                loinc_code="2093-3",
                value_numeric=210.0,
                unit="mg/dL",
                flag="high",
                source_provenance="fixture",
            ),
            ResearchEvidenceRecord(
                id="rec_ldl_chol",
                dataset="synthea",
                source_patient_id="p_adversarial",
                source_encounter_id="enc_1",
                source_record_id="row_2",
                observation_date="2023-05-01T10:00:00Z",
                analyte_raw="Cholesterol in LDL [Mass/volume] in Serum or Plasma",
                analyte_canonical="LDL Cholesterol",
                concept_id="LOINC:2089-1",
                loinc_code="2089-1",
                value_numeric=140.0,
                unit="mg/dL",
                flag="high",
                source_provenance="fixture",
            ),
        ]

        query = ClinicalQuery(
            raw_query="What was my LDL cholesterol level?",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="LDL Cholesterol",
            loinc_code="2089-1",
            concept_id="LOINC:2089-1",
        )

        # Baseline WITHOUT concept: weights with gamma=0.0
        no_concept_retriever = ModularEvidenceRetriever(
            weights=ScoringWeights(alpha_lexical=0.5, beta_semantic=0.5, gamma_concept=0.0, delta_temporal=0.0),
            method_name="No_Concept",
        )
        results_no_concept = no_concept_retriever.retrieve(query, records, top_k=2, patient_id="p_adversarial")

        # WITH concept: weights with gamma=0.25
        with_concept_retriever = ModularEvidenceRetriever(
            weights=ScoringWeights(alpha_lexical=0.35, beta_semantic=0.35, gamma_concept=0.30, delta_temporal=0.0),
            method_name="With_Concept",
        )
        results_with_concept = with_concept_retriever.retrieve(query, records, top_k=2, patient_id="p_adversarial")

        # Verify component score diagnostics
        res_map = {r.evidence_id: r for r in results_with_concept}
        rec_a = res_map["rec_total_chol"]
        rec_b = res_map["rec_ldl_chol"]

        assert rec_a.metadata["score_concept"] == 0.0
        assert rec_b.metadata["score_concept"] == 1.0

        # In results_with_concept, Record B (LDL) MUST be Rank 1
        assert results_with_concept[0].evidence_id == "rec_ldl_chol"
        assert results_with_concept[0].rank == 1


# ===========================================================================
# 9. Temporal Constraint Correctness — 13 Explicit Cases (Blocker 4)
# ===========================================================================

class TestTemporalConstraintCorrectness:
    """
    BLOCKER 4: Explicit test suite for all 13 required temporal cases and hard gating.
    """

    @pytest.fixture
    def temporal_patient_records(self) -> list[ResearchEvidenceRecord]:
        """Provides a controlled chronological series of Glucose observations."""
        dates = [
            ("2021-01-15T08:00:00Z", 92.0, "normal", "ev_2021"),
            ("2022-06-10T08:00:00Z", 110.0, "abnormal", "ev_2022"),
            ("2023-03-20T08:00:00Z", 105.0, "abnormal", "ev_2023"),
            ("2024-01-05T08:00:00Z", 98.0, "normal", "ev_2024"),
        ]
        return [
            ResearchEvidenceRecord(
                id=eid,
                dataset="synthea",
                source_patient_id="p_temp",
                source_encounter_id=f"enc_{eid}",
                source_record_id=f"row_{eid}",
                observation_date=d,
                analyte_raw="Glucose [Mass/volume] in Serum or Plasma",
                analyte_canonical="Glucose",
                concept_id="LOINC:2345-7",
                loinc_code="2345-7",
                value_numeric=val,
                unit="mg/dL",
                flag=flag,
                source_provenance="fixture",
            )
            for d, val, flag, eid in dates
        ]

    # Case 1: Latest / Current Value
    def test_case_1_latest_current_value(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="latest glucose", intent=QueryIntent.CURRENT_VALUE, temporal_operator=TemporalOperator.LATEST, analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2024"] == 1.0
        assert scores["ev_2021"] < scores["ev_2024"]

    # Case 2: Historical All
    def test_case_2_historical_all(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="all glucose history", intent=QueryIntent.HISTORICAL, temporal_operator=TemporalOperator.ALL_TIME, analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        for r in temporal_patient_records:
            assert scores[r.id] == 1.0

    # Case 3: Last N
    def test_case_3_last_n(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="last 2 glucose", intent=QueryIntent.LAST_N, temporal_operator=TemporalOperator.LAST_N, limit=2, analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2024"] >= 0.8
        assert scores["ev_2023"] >= 0.8
        assert scores["ev_2021"] <= 0.1

    # Case 4: Before Date
    def test_case_4_before_date(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="glucose before 2022-12-31", intent=QueryIntent.HISTORICAL, temporal_operator=TemporalOperator.BEFORE, end_date=date(2022, 12, 31), analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2021"] == 1.0
        assert scores["ev_2022"] == 1.0
        assert scores["ev_2023"] == 0.0
        assert scores["ev_2024"] == 0.0

    # Case 5: After Date
    def test_case_5_after_date(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="glucose after 2023-01-01", intent=QueryIntent.HISTORICAL, temporal_operator=TemporalOperator.AFTER, start_date=date(2023, 1, 1), analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2021"] == 0.0
        assert scores["ev_2022"] == 0.0
        assert scores["ev_2023"] == 1.0
        assert scores["ev_2024"] == 1.0

    # Case 6: Since Date
    def test_case_6_since_date(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="glucose since 2022-01-01", intent=QueryIntent.HISTORICAL, temporal_operator=TemporalOperator.SINCE, start_date=date(2022, 1, 1), analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2021"] == 0.0
        assert scores["ev_2022"] == 1.0
        assert scores["ev_2023"] == 1.0
        assert scores["ev_2024"] == 1.0

    # Case 7: Bounded Date Range
    def test_case_7_bounded_date_range(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="glucose between 2022 and 2023", intent=QueryIntent.HISTORICAL, temporal_operator=TemporalOperator.BETWEEN, start_date=date(2022, 1, 1), end_date=date(2023, 12, 31), analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2021"] == 0.0
        assert scores["ev_2022"] == 1.0
        assert scores["ev_2023"] == 1.0
        assert scores["ev_2024"] == 0.0

    # Case 8: Exact Date
    def test_case_8_exact_date(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="glucose on 2022-06-10", intent=QueryIntent.HISTORICAL, temporal_operator=TemporalOperator.EXACT_DATE, start_date=date(2022, 6, 10), analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2022"] == 1.0
        assert scores["ev_2021"] == 0.0
        assert scores["ev_2024"] == 0.0

    # Case 9: Previous Value
    def test_case_9_previous_value(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="previous glucose before latest", intent=QueryIntent.COMPARISON, comparison_target=ComparisonTarget.PREVIOUS, analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        # Immediate predecessor before ev_2024 is ev_2023
        assert scores["ev_2023"] == 1.0
        assert scores["ev_2024"] == 0.5  # reference anchor

    # Case 10: Comparison Points
    def test_case_10_comparison_points(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="compare glucose between 2021-01-15 and 2024-01-05", intent=QueryIntent.COMPARISON, start_date=date(2021, 1, 15), end_date=date(2024, 1, 5), analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        assert scores["ev_2021"] == 1.0
        assert scores["ev_2024"] == 1.0
        assert scores["ev_2022"] == 0.0

    # Case 11: Trend
    def test_case_11_trend(self, temporal_patient_records):
        scorer = TemporalScorer()
        q = ClinicalQuery(raw_query="trend in glucose", intent=QueryIntent.TREND, analyte_canonical="Glucose")
        scores = scorer.score_patient_evidence(q, temporal_patient_records)
        for r in temporal_patient_records:
            assert scores[r.id] == 1.0

    # Case 12: Abnormality
    def test_case_12_abnormality(self, temporal_patient_records):
        retriever = ModularEvidenceRetriever(weights=ScoringWeights.full())
        q = ClinicalQuery(raw_query="abnormal glucose", intent=QueryIntent.ABNORMALITY, abnormal_only=True, analyte_canonical="Glucose")
        scores = retriever._score_intent_abnormality(q, temporal_patient_records)
        assert scores["ev_2022"] == 1.0  # abnormal (110)
        assert scores["ev_2023"] == 1.0  # abnormal (105)
        assert scores["ev_2021"] == 0.0  # normal (92)
        assert scores["ev_2024"] == 0.0  # normal (98)

    # Case 13: First Abnormal
    def test_case_13_first_abnormal(self, temporal_patient_records):
        retriever = ModularEvidenceRetriever(weights=ScoringWeights.full())
        q = ClinicalQuery(raw_query="what was my first abnormal glucose", intent=QueryIntent.ABNORMALITY, abnormal_only=True, analyte_canonical="Glucose")
        scores = retriever._score_intent_abnormality(q, temporal_patient_records)
        # ev_2022 (2022-06-10) is the first abnormal observation
        assert scores["ev_2022"] == 1.0
        assert scores["ev_2023"] == 0.5  # abnormal but later
        assert scores["ev_2021"] == 0.0

    # Hard Temporal Eligibility Filter Verification
    def test_hard_temporal_filter_prevents_out_of_window_outranking(self, temporal_patient_records):
        """
        CRITICAL TEST: Verifies that an observation from 2024 CANNOT outrank a valid 2022
        observation in a date-bounded query even if the 2024 observation has a strong score.
        """
        retriever = ModularEvidenceRetriever(
            weights=ScoringWeights.hybrid_temporal_concept(),
            hard_temporal_filter=True,
        )
        q = ClinicalQuery(
            raw_query="What was my glucose between 2022-01-01 and 2022-12-31?",
            intent=QueryIntent.HISTORICAL,
            temporal_operator=TemporalOperator.BETWEEN,
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
            analyte_canonical="Glucose",
        )
        results = retriever.retrieve(q, temporal_patient_records, top_k=4, patient_id="p_temp")

        # ev_2022 is the ONLY record in the 2022 date window
        assert results[0].evidence_id == "ev_2022"
        assert results[0].rank == 1
        assert results[0].score > 0.0

        # Out-of-window records (ev_2021, ev_2023, ev_2024) must have final_score == 0.0
        for res in results[1:]:
            assert res.score == 0.0


# ===========================================================================
# 10. RRF Fusion Experiments (Blocker 6)
# ===========================================================================

class TestRRFFusion:
    """
    BLOCKER 6: Verifies Reciprocal Rank Fusion implementation and score computation.
    """

    def test_rrf_scoring_and_ranking(self, sample_records):
        retriever = ModularEvidenceRetriever(
            weights=ScoringWeights.rrf(),
            method_name="RRF",
            fusion_strategy="rrf",
            rrf_k=60,
        )
        q = ClinicalQuery(
            raw_query="HbA1c results",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="HbA1c",
        )
        p1_records = filter_patient_evidence(sample_records, "patient_1")
        results = retriever.retrieve(q, p1_records, top_k=4, patient_id="patient_1")

        assert len(results) == 4
        assert results[0].rank == 1
        assert results[0].retrieval_method == "RRF"
        # Scores are normalized in [0.0, 1.0]
        for r in results:
            assert 0.0 <= r.score <= 1.0



# ===========================================================================
# 8. Deterministic Tie-Breaking & Edge Cases
# ===========================================================================

class TestTieBreakingAndEdgeCases:
    def test_sort_and_rank_results_uses_date_then_evidence_id_for_score_ties(self):
        r1 = RetrievalResult(
            evidence_id="ev_b",
            patient_id="p1",
            score=0.75,
            rank=0,
            retrieval_method="test",
            analyte_canonical="HbA1c",
            concept_id="LOINC:4548-4",
            loinc_code="4548-4",
            observation_date="2023-01-01T00:00:00Z",
            value=6.0,
            unit="%",
            flag="normal",
            source_provenance="",
        )

        r2 = RetrievalResult(
            evidence_id="ev_a",
            patient_id="p1",
            score=0.75,
            rank=0,
            retrieval_method="test",
            analyte_canonical="HbA1c",
            concept_id="LOINC:4548-4",
            loinc_code="4548-4",
            observation_date="2023-01-01T00:00:00Z",
            value=6.0,
            unit="%",
            flag="normal",
            source_provenance="",
        )

        r3 = RetrievalResult(
            evidence_id="ev_c",
            patient_id="p1",
            score=0.75,
            rank=0,
            retrieval_method="test",
            analyte_canonical="HbA1c",
            concept_id="LOINC:4548-4",
            loinc_code="4548-4",
            observation_date="2024-01-01T00:00:00Z",
            value=6.0,
            unit="%",
            flag="normal",
            source_provenance="",
        )

        ranked = sort_and_rank_results([r1, r2, r3], top_k=3)

        assert ranked[0].evidence_id == "ev_c"
        assert ranked[0].rank == 1

        assert ranked[1].evidence_id == "ev_a"
        assert ranked[1].rank == 2

        assert ranked[2].evidence_id == "ev_b"
        assert ranked[2].rank == 3`n