"""
tests/unit/research-data/test_longitudinal_evaluator.py

Unit test suite for Longitudinal Evidence Selection Evaluator (CP-08).
Verifies:
  1. Exact target evidence metrics (Recall, Precision, F1)
  2. Trajectory-supporting evidence metrics
  3. Trajectory coverage calculation
  4. Redundant evidence rate calculation
  5. Provenance completeness calculation
  6. Aggregate benchmark evaluation and intent stratification
  7. Mode A (Oracle) vs Mode B (End-to-End) separation
  8. Empty / edge-case query handling
"""

from __future__ import annotations

import pytest

from packages.ml_interfaces.query import ClinicalQuery, QueryIntent
from packages.research_data.evaluation.longitudinal_evaluator import (
    LongitudinalEvidenceEvaluator,
    LongitudinalSelectionMetrics,
)
from packages.research_data.models import EvaluationQuery
from packages.research_data.retrieval.contract import EvidenceRetriever, RetrievalResult
from packages.research_data.retrieval.longitudinal_selection import (
    LongitudinalEvidencePackage,
    LongitudinalEvidenceSelector,
)


class MockRetriever:
    """Mock retriever returning predetermined candidates."""

    def __init__(self, candidates: list[RetrievalResult]) -> None:
        self.candidates = candidates

    def retrieve(self, query: ClinicalQuery, top_k: int = 10) -> list[RetrievalResult]:
        return list(self.candidates)


def make_cand(
    evidence_id: str,
    date_str: str,
    value: float = 6.0,
    patient_id: str = "p1",
    analyte: str = "HbA1c",
    flag: str = "",
    provenance: str = "synthea:sample",
) -> RetrievalResult:
    return RetrievalResult(
        evidence_id=evidence_id,
        patient_id=patient_id,
        score=0.9,
        rank=0,
        retrieval_method="mock",
        analyte_canonical=analyte,
        concept_id="LOINC:4548-4",
        loinc_code="4548-4",
        observation_date=date_str,
        value=value,
        unit="%",
        flag=flag,
        source_provenance=provenance,
    )


class TestLongitudinalEvaluator:
    def test_evaluate_item_exact_and_supporting_metrics(self):
        c1 = make_cand("ev_1", "2021-01-01T00:00:00Z", 5.5)
        c2 = make_cand("ev_2", "2022-06-01T00:00:00Z", 7.0)
        c3 = make_cand("ev_3", "2023-12-01T00:00:00Z", 6.2)

        retriever = MockRetriever([c1, c2, c3])
        evaluator = LongitudinalEvidenceEvaluator(retriever=retriever)

        # Benchmark item expects ev_1 and ev_3 as exact target
        item = EvaluationQuery(
            query_id="Q_mock_1",
            patient_id="p1",
            query="How has my HbA1c changed over time?",
            intent="longitudinal_trend",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_1", "ev_3"],
            split="test",
        )

        pkg, metrics = evaluator.evaluate_item(item, mode="oracle")

        # Selector selected all 3: ev_1 (baseline), ev_2 (inflection), ev_3 (endpoint)
        assert set(pkg.selected_evidence_ids) == {"ev_1", "ev_2", "ev_3"}

        # Exact metrics:
        # Ground truth: {ev_1, ev_3}
        # Selected: {ev_1, ev_2, ev_3}
        # Exact Recall: 2/2 = 1.0
        # Exact Precision: 2/3 = 0.6667
        assert metrics["exact_recall"] == 1.0
        assert round(metrics["exact_precision"], 4) == round(2 / 3, 4)

        # Supporting metrics:
        # For a 3-point minimal sufficient trajectory, all 3 points (baseline, inflection, endpoint) are primary anchors.
        # With zero supporting observations emitted, supporting_precision is None (N/A, not vacuous 1.0).
        assert metrics["supporting_precision"] is None
        assert metrics["trajectory_coverage"] == 1.0
        assert metrics["provenance_completeness"] == 1.0

    def test_evaluate_benchmark_aggregation(self):
        c1 = make_cand("ev_1", "2023-01-01T00:00:00Z", 6.0)
        c2 = make_cand("ev_2", "2024-01-01T00:00:00Z", 6.5)

        retriever = MockRetriever([c1, c2])
        evaluator = LongitudinalEvidenceEvaluator(retriever=retriever)

        items = [
            EvaluationQuery(
                query_id="Q_1",
                patient_id="p1",
                query="What is my most recent HbA1c?",
                intent="current_value",
                target_analyte="HbA1c",
                relevant_evidence_ids=["ev_2"],
                split="test",
            ),
            EvaluationQuery(
                query_id="Q_2",
                patient_id="p1",
                query="How has my HbA1c changed?",
                intent="longitudinal_trend",
                target_analyte="HbA1c",
                relevant_evidence_ids=["ev_1", "ev_2"],
                split="test",
            ),
        ]

        summary = evaluator.evaluate_benchmark(items, mode="oracle")

        assert summary.total_queries == 2
        assert summary.exact_recall == 1.0
        assert summary.exact_precision == 1.0
        assert summary.trajectory_coverage == 1.0
        assert summary.provenance_completeness == 1.0
        assert "current_value" in summary.intent_stratified
        assert "longitudinal_trend" in summary.intent_stratified

    def test_date_comparison_both_anchors_assigned_to_primary(self):
        c1 = make_cand("ev_d1", "2022-02-10T00:00:00Z", 6.0)
        c2 = make_cand("ev_d2", "2024-03-30T00:00:00Z", 6.8)
        retriever = MockRetriever([c1, c2])
        evaluator = LongitudinalEvidenceEvaluator(retriever=retriever)

        item = EvaluationQuery(
            query_id="Q_comp",
            patient_id="p1",
            query="Compare my HbA1c from 2022-02-10 with 2024-03-30.",
            intent="date_comparison",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_d1", "ev_d2"],
            split="test",
            metadata={"date_a": "2022-02-10", "date_b": "2024-03-30"},
        )

        pkg_ora, m_ora = evaluator.evaluate_item(item, mode="oracle")
        assert set(pkg_ora.primary_evidence_ids) == {"ev_d1", "ev_d2"}
        assert m_ora["primary_recall"] == 1.0
        assert m_ora["primary_precision"] == 1.0
        assert m_ora["total_recall"] == 1.0

        pkg_e2e, m_e2e = evaluator.evaluate_item(item, mode="end_to_end")
        assert set(pkg_e2e.primary_evidence_ids) == {"ev_d1", "ev_d2"}
        assert m_e2e["primary_recall"] == 1.0
        assert m_e2e["primary_precision"] == 1.0
        assert m_e2e["total_recall"] == 1.0

    def test_last_n_observations_all_n_assigned_to_primary(self):
        c1 = make_cand("ev_1", "2021-01-01T00:00:00Z", 5.5)
        c2 = make_cand("ev_2", "2022-01-01T00:00:00Z", 5.8)
        c3 = make_cand("ev_3", "2023-01-01T00:00:00Z", 6.2)
        c4 = make_cand("ev_4", "2024-01-01T00:00:00Z", 6.5)
        retriever = MockRetriever([c1, c2, c3, c4])
        evaluator = LongitudinalEvidenceEvaluator(retriever=retriever)

        item = EvaluationQuery(
            query_id="Q_last3",
            patient_id="p1",
            query="Show my last 3 HbA1c results.",
            intent="last_n_observations",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_2", "ev_3", "ev_4"],
            split="test",
            metadata={"n_requested": 3},
        )

        pkg_ora, m_ora = evaluator.evaluate_item(item, mode="oracle")
        assert set(pkg_ora.primary_evidence_ids) == {"ev_2", "ev_3", "ev_4"}
        assert m_ora["primary_recall"] == 1.0
        assert m_ora["primary_precision"] == 1.0

        pkg_e2e, m_e2e = evaluator.evaluate_item(item, mode="end_to_end")
        assert set(pkg_e2e.primary_evidence_ids) == {"ev_2", "ev_3", "ev_4"}
        assert m_e2e["primary_recall"] == 1.0
        assert m_e2e["primary_precision"] == 1.0

    def test_first_abnormal_clinical_thresholding_and_earliest_primary(self):
        # In Synthea, flags are null; clinical thresholds must identify abnormality
        c1 = make_cand("ev_norm", "2021-01-01T00:00:00Z", 175.0, analyte="Total Cholesterol")
        c2 = make_cand("ev_abn1", "2022-01-01T00:00:00Z", 215.0, analyte="Total Cholesterol")  # >= 200 is abnormal
        c3 = make_cand("ev_abn2", "2023-01-01T00:00:00Z", 230.0, analyte="Total Cholesterol")
        retriever = MockRetriever([c1, c2, c3])
        evaluator = LongitudinalEvidenceEvaluator(retriever=retriever)

        item = EvaluationQuery(
            query_id="Q_abn",
            patient_id="p1",
            query="When was my Total Cholesterol first flagged as elevated or abnormal?",
            intent="first_abnormal",
            target_analyte="Total Cholesterol",
            relevant_evidence_ids=["ev_abn1"],
            split="test",
        )

        pkg_ora, m_ora = evaluator.evaluate_item(item, mode="oracle")
        assert pkg_ora.primary_evidence_ids == ["ev_abn1"]
        assert m_ora["primary_recall"] == 1.0

        pkg_e2e, m_e2e = evaluator.evaluate_item(item, mode="end_to_end")
        assert pkg_e2e.primary_evidence_ids == ["ev_abn1"]
        assert m_e2e["primary_recall"] == 1.0

    def test_longitudinal_trend_primary_anchors_and_supporting_milestones(self):
        c1 = make_cand("ev_1", "2021-01-01T00:00:00Z", 5.5)  # baseline
        c2 = make_cand("ev_2", "2022-01-01T00:00:00Z", 7.5)  # milestone
        c3 = make_cand("ev_3", "2023-01-01T00:00:00Z", 9.0)  # inflection
        c4 = make_cand("ev_4", "2024-01-01T00:00:00Z", 6.0)  # endpoint
        retriever = MockRetriever([c1, c2, c3, c4])
        evaluator = LongitudinalEvidenceEvaluator(retriever=retriever)

        item = EvaluationQuery(
            query_id="Q_trend",
            patient_id="p1",
            query="How has my HbA1c changed over time?",
            intent="longitudinal_trend",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_1", "ev_2", "ev_3", "ev_4"],
            split="test",
        )

        pkg, metrics = evaluator.evaluate_item(item, mode="oracle")
        # 3 anchors (baseline, endpoint, inflection) must be primary
        assert set(pkg.primary_evidence_ids) == {"ev_1", "ev_3", "ev_4"}
        # Intermediate milestone must be supporting
        assert set(pkg.supporting_evidence_ids) == {"ev_2"}
        # Total recall must capture all 4 points
        assert metrics["total_recall"] == 1.0
        # Primary recall is 3 anchors out of 4 gold points
        assert metrics["primary_recall"] == 0.75
        assert metrics["primary_precision"] == 1.0
        assert metrics["supporting_precision"] == 1.0

    def test_supporting_precision_strict_relevance_verification(self):
        # Verify that supporting observations without valid clinical roles are penalized
        evaluator = LongitudinalEvidenceEvaluator(retriever=MockRetriever([]))
        
        # Valid package: supporting observation has role 'reference_latest'
        c_prim = make_cand("ev_p", "2022-01-01T00:00:00Z", 6.0)
        c_supp = make_cand("ev_s", "2023-01-01T00:00:00Z", 6.5)
        pkg_valid = LongitudinalEvidencePackage(
            patient_id="p1",
            query_id="Q_test",
            raw_query="What was my previous HbA1c?",
            query_intent="previous_value",
            target_analyte="HbA1c",
            selected_evidence_ids=["ev_p", "ev_s"],
            primary_evidence_ids=["ev_p"],
            supporting_evidence_ids=["ev_s"],
            selected_observations=[c_prim, c_supp],
            trajectory_blocks=[],
            feature_summaries={},
            selection_rationale={"ev_p": "predecessor", "ev_s": "reference_latest"},
            provenance_references=[],
        )
        item = EvaluationQuery(
            query_id="Q_test",
            patient_id="p1",
            query="What was my previous HbA1c?",
            intent="previous_value",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_p"],
            split="test",
        )
        m_valid = evaluator._compute_package_metrics(pkg_valid, item)
        assert m_valid["supporting_precision"] == 1.0

        # Invalid package: supporting observation has arbitrary unverified role
        pkg_invalid = LongitudinalEvidencePackage(
            patient_id="p1",
            query_id="Q_test",
            raw_query="What was my previous HbA1c?",
            query_intent="previous_value",
            target_analyte="HbA1c",
            selected_evidence_ids=["ev_p", "ev_s"],
            primary_evidence_ids=["ev_p"],
            supporting_evidence_ids=["ev_s"],
            selected_observations=[c_prim, c_supp],
            trajectory_blocks=[],
            feature_summaries={},
            selection_rationale={"ev_p": "predecessor", "ev_s": "unrelated_noise"},
            provenance_references=[],
        )
        m_invalid = evaluator._compute_package_metrics(pkg_invalid, item)
        assert m_invalid["supporting_precision"] == 0.0

    def test_empty_supporting_set_yields_none_precision(self):
        evaluator = LongitudinalEvidenceEvaluator(retriever=MockRetriever([]))
        c_prim = make_cand("ev_p", "2023-01-01T00:00:00Z", 6.0)
        pkg_empty_supp = LongitudinalEvidencePackage(
            patient_id="p1",
            query_id="Q_curr",
            raw_query="What is my latest HbA1c?",
            query_intent="current_value",
            target_analyte="HbA1c",
            selected_evidence_ids=["ev_p"],
            primary_evidence_ids=["ev_p"],
            supporting_evidence_ids=[],
            selected_observations=[c_prim],
            trajectory_blocks=[],
            feature_summaries={},
            selection_rationale={"ev_p": "latest_observation"},
            provenance_references=[],
        )
        item = EvaluationQuery(
            query_id="Q_curr",
            patient_id="p1",
            query="What is my latest HbA1c?",
            intent="current_value",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_p"],
            split="test",
        )
        m = evaluator._compute_package_metrics(pkg_empty_supp, item)
        # Empty supporting set must yield None (N/A), not vacuous 1.0
        assert m["supporting_precision"] is None
        assert m["supporting_count"] == 0.0

    def test_macro_and_micro_supporting_precision_aggregation(self):
        c1 = make_cand("ev_1", "2022-01-01T00:00:00Z", 5.5)
        c2 = make_cand("ev_2", "2023-01-01T00:00:00Z", 6.5)
        c3 = make_cand("ev_3", "2024-01-01T00:00:00Z", 7.0)
        retriever = MockRetriever([c1, c2, c3])
        evaluator = LongitudinalEvidenceEvaluator(retriever=retriever)

        # Item 1: current_value -> empty supporting set
        item1 = EvaluationQuery(
            query_id="Q_1",
            patient_id="p1",
            query="What is my latest HbA1c?",
            intent="current_value",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_3"],
            split="test",
        )
        # Item 2: previous_value -> emits 1 supporting observation (the latest anchor)
        item2 = EvaluationQuery(
            query_id="Q_2",
            patient_id="p1",
            query="What was my previous HbA1c reading before the latest one?",
            intent="previous_value",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_2"],
            split="test",
        )

        metrics = evaluator.evaluate_benchmark([item1, item2], mode="oracle")
        assert metrics.total_queries == 2
        assert metrics.supporting_query_count == 1
        assert metrics.supporting_obs_count == 1
        # Macro and micro supporting precision are 1.0 (over the single query that emitted supporting observations)
        assert metrics.supporting_precision == 1.0
        assert metrics.micro_supporting_precision == 1.0
        # Intent-stratified: current_value has None supporting precision; previous_value has 1.0
        assert metrics.intent_stratified["current_value"]["supporting_precision"] is None
        assert metrics.intent_stratified["previous_value"]["supporting_precision"] == 1.0


