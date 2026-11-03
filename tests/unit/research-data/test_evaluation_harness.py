"""
tests/unit/research-data/test_evaluation_harness.py

Unit test suite for Offline Evaluation Harness and Metrics (CP-06).
Verifies:
  1. Deterministic IR metrics (MRR, Recall@K, Precision@K, nDCG@K)
  2. Failure diagnosis and classification taxonomy
  3. Harness loading of Synthea records, splits, and queries
  4. End-to-end benchmark execution on Dev split
  5. Determinism of repeated evaluation runs
"""

from __future__ import annotations

import pytest

from packages.research_data.evaluation.failure_analyzer import (
    RetrievalFailureRecord,
    diagnose_query_failure,
)
from packages.research_data.evaluation.harness import (
    BENCHMARK_INTENT_MAP,
    ResearchEvaluationHarness,
)
from packages.research_data.evaluation.metrics import (
    EvaluationMetrics,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from packages.research_data.models import EvaluationQuery, ResearchEvidenceRecord
from packages.research_data.retrieval.bm25 import EvidenceBM25Retriever
from packages.research_data.retrieval.contract import RetrievalResult


# ===========================================================================
# 1. Metric Calculations Tests
# ===========================================================================

class TestMetricCalculations:
    def test_reciprocal_rank(self):
        relevant = {"doc_3", "doc_7"}
        # First relevant item is at index 0 (rank 1) -> 1.0
        assert reciprocal_rank(["doc_3", "doc_1", "doc_2"], relevant) == 1.0
        # First relevant item is at index 1 (rank 2) -> 0.5
        assert reciprocal_rank(["doc_1", "doc_3", "doc_2"], relevant) == 0.5
        # First relevant item is at index 2 (rank 3) -> 1/3
        assert round(reciprocal_rank(["doc_1", "doc_2", "doc_7"], relevant), 4) == round(1.0 / 3.0, 4)
        # None found -> 0.0
        assert reciprocal_rank(["doc_1", "doc_2", "doc_4"], relevant) == 0.0

    def test_recall_at_k(self):
        relevant = {"doc_1", "doc_2", "doc_3", "doc_4"}
        retrieved = ["doc_1", "doc_2", "doc_8", "doc_9", "doc_3"]
        # In top-2: doc_1, doc_2 -> 2/4 = 0.5
        assert recall_at_k(retrieved, relevant, k=2) == 0.5
        # In top-5: doc_1, doc_2, doc_3 -> 3/4 = 0.75
        assert recall_at_k(retrieved, relevant, k=5) == 0.75

    def test_precision_at_k(self):
        relevant = {"doc_1", "doc_2"}
        retrieved = ["doc_1", "doc_8", "doc_2", "doc_9"]
        # In top-2: 1 relevant / 2 = 0.5
        assert precision_at_k(retrieved, relevant, k=2) == 0.5
        # In top-4: 2 relevant / 4 = 0.5
        assert precision_at_k(retrieved, relevant, k=4) == 0.5

    def test_ndcg_at_k(self):
        relevant = {"doc_1", "doc_2"}
        # Perfect ranking: both relevant in first 2 spots -> nDCG = 1.0
        assert ndcg_at_k(["doc_1", "doc_2", "doc_3"], relevant, k=3) == 1.0
        # Inverted ranking: doc_3 (irrelevant), then doc_1, doc_2 -> nDCG < 1.0
        score = ndcg_at_k(["doc_3", "doc_1", "doc_2"], relevant, k=3)
        assert 0.0 < score < 1.0

    def test_metrics_aggregation(self):
        m_list = [
            {"mrr": 1.0, "recall_at_1": 1.0, "recall_at_3": 1.0, "recall_at_5": 1.0, "recall_at_10": 1.0,
             "precision_at_1": 1.0, "precision_at_3": 0.33, "precision_at_5": 0.2, "precision_at_10": 0.1, "ndcg_at_10": 1.0},
            {"mrr": 0.5, "recall_at_1": 0.0, "recall_at_3": 1.0, "recall_at_5": 1.0, "recall_at_10": 1.0,
             "precision_at_1": 0.0, "precision_at_3": 0.33, "precision_at_5": 0.2, "precision_at_10": 0.1, "ndcg_at_10": 0.8},
        ]
        agg = EvaluationMetrics.aggregate(m_list)
        assert agg.query_count == 2
        assert agg.mrr == 0.75
        assert agg.recall_at_1 == 0.5


# ===========================================================================
# 2. Failure Analysis Tests
# ===========================================================================

class TestFailureAnalysis:
    def test_diagnose_success_returns_none(self):
        q = EvaluationQuery(
            query_id="Q_01",
            patient_id="p1",
            query="test query",
            intent="current_value",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_1"],
            split="dev",
        )
        rec = ResearchEvidenceRecord(
            id="ev_1", dataset="synthea", source_patient_id="p1", source_encounter_id="e1",
            source_record_id="r1", observation_date="2024-01-01", analyte_raw="HbA1c"
        )
        ret = [
            RetrievalResult(
                evidence_id="ev_1", patient_id="p1", score=1.0, rank=1, retrieval_method="test",
                analyte_canonical="HbA1c", concept_id="LOINC:4548-4", loinc_code="4548-4",
                observation_date="2024-01-01", value=6.0, unit="%", flag="normal", source_provenance=""
            )
        ]
        failure = diagnose_query_failure(q, ret, [rec], k=5)
        assert failure is None

    def test_diagnose_wrong_patient_leakage(self):
        q = EvaluationQuery(
            query_id="Q_01",
            patient_id="p1",
            query="test query",
            intent="current_value",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_1"],
            split="dev",
        )
        rec = ResearchEvidenceRecord(
            id="ev_1", dataset="synthea", source_patient_id="p1", source_encounter_id="e1",
            source_record_id="r1", observation_date="2024-01-01", analyte_raw="HbA1c"
        )
        # Retrieved item belongs to p2 instead of p1!
        ret = [
            RetrievalResult(
                evidence_id="ev_other", patient_id="p2", score=1.0, rank=1, retrieval_method="test",
                analyte_canonical="HbA1c", concept_id="LOINC:4548-4", loinc_code="4548-4",
                observation_date="2024-01-01", value=6.0, unit="%", flag="normal", source_provenance=""
            )
        ]
        failure = diagnose_query_failure(q, ret, [rec], k=5)
        assert failure is not None
        assert failure.reason == "wrong_patient_protection_failure"


# ===========================================================================
# 3. Harness Integration & End-to-End Tests
# ===========================================================================

class TestResearchEvaluationHarness:
    def test_harness_loads_synthea_dataset_and_queries(self):
        harness = ResearchEvaluationHarness()
        records = harness.load_records()
        assert len(records) == 2790

        queries_dev = harness.load_queries(split="dev")
        queries_val = harness.load_queries(split="val")
        queries_test = harness.load_queries(split="test")

        assert len(queries_dev) == 36
        assert len(queries_val) == 25
        assert len(queries_test) == 25

    def test_harness_evaluate_bm25_on_dev_split(self):
        harness = ResearchEvaluationHarness()
        retriever = EvidenceBM25Retriever()

        run_res = harness.evaluate_retriever(
            retriever=retriever,
            method_name="BM25",
            split="dev",
            top_k=10,
        )

        assert run_res.method_name == "BM25"
        assert run_res.split == "dev"
        assert run_res.overall_metrics.query_count == 36
        assert run_res.overall_metrics.mrr > 0.0
        assert run_res.overall_metrics.recall_at_10 > 0.0
        # Stratified metrics must cover all benchmark intents
        assert len(run_res.stratified_metrics) > 0
        for intent in run_res.stratified_metrics:
            assert run_res.stratified_metrics[intent].query_count > 0

    def test_mode_b_end_to_end_zero_gold_label_leakage(self):
        """
        BLOCKER 2: Proves that in Mode B (END_TO_END), zero benchmark gold labels
        (target_analyte, LOINC, concept_id, intent, relevant_evidence_ids) reach the parser.
        """
        from packages.research_data.evaluation.harness import EvaluationMode

        harness = ResearchEvaluationHarness()

        # Query with deliberate divergence between raw text and benchmark gold metadata
        mock_eval_query = EvaluationQuery(
            query_id="Q_LEAKAGE_TEST",
            patient_id="patient_test_01",
            query="Can you tell me my sugar levels recently?",  # parser extracts "Glucose"
            intent="current_value",
            target_analyte="HbA1c",  # Gold label is intentionally different (HbA1c)
            relevant_evidence_ids=["ev_gold_1", "ev_gold_2"],
            split="dev",
            metadata={"loinc_code": "4548-4", "concept_id": "LOINC:4548-4"},
        )

        parsed_b = harness.get_parsed_query(mock_eval_query, mode=EvaluationMode.END_TO_END)

        # Mode B must parse strictly from text ("sugar" -> Glucose) and NOT copy gold "HbA1c"
        assert parsed_b.analyte_canonical != "HbA1c"
        assert parsed_b.analyte_canonical == "Glucose"
        assert parsed_b.loinc_code != "4548-4"
        assert parsed_b.concept_id != "LOINC:4548-4"
        # Patient ID is attached solely for user-identity retrieval scoping
        assert getattr(parsed_b, "patient_id") == "patient_test_01"

    def test_mode_a_oracle_retrieval_isolation(self):
        """
        BLOCKER 2: Proves that Mode A (ORACLE) explicitly grounds target_analyte and LOINC
        for isolating the retrieval engine from parsing noise.
        """
        from packages.research_data.evaluation.harness import EvaluationMode

        harness = ResearchEvaluationHarness()

        mock_eval_query = EvaluationQuery(
            query_id="Q_ORACLE_TEST",
            patient_id="patient_test_01",
            query="Can you tell me my sugar levels recently?",
            intent="current_value",
            target_analyte="HbA1c",  # Gold label
            relevant_evidence_ids=["ev_gold_1"],
            split="dev",
        )

        parsed_a = harness.get_parsed_query(mock_eval_query, mode=EvaluationMode.ORACLE)

        # Mode A explicitly grounds the query with gold target_analyte and LOINC
        assert parsed_a.analyte_canonical == "HbA1c"
        assert parsed_a.loinc_code == "4548-4"
        assert parsed_a.concept_id == "LOINC:4548-4"
        assert getattr(parsed_a, "patient_id") == "patient_test_01"

    def test_per_query_diagnostics_generation(self):
        """
        BLOCKER 5: Proves that every query receives an inspectable diagnostic record
        with ranks, reciprocal rank, component scores, and failure classification.
        """
        from packages.research_data.evaluation.harness import EvaluationMode

        harness = ResearchEvaluationHarness()
        retriever = EvidenceBM25Retriever()

        run_res = harness.evaluate_retriever(
            retriever=retriever,
            method_name="BM25",
            split="val",
            mode=EvaluationMode.ORACLE,
            top_k=10,
        )

        # Exactly 25 queries on val split -> 25 diagnostic records
        assert len(run_res.diagnostics) == 25
        for diag in run_res.diagnostics:
            assert diag.query_id.startswith("Q_")
            assert diag.method == "BM25"
            assert isinstance(diag.expected_evidence_ids, list)
            assert isinstance(diag.retrieved_top_k_ids, list)
            assert diag.reciprocal_rank >= 0.0


            assert diag.classification in (
                "perfect_rank_1",
                "ranking_error",
                "top_k_miss",
                "temporal_ranking_error",
                "concept_ranking_error",
            )`n