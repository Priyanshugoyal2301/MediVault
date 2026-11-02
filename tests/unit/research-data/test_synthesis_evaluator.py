"""
tests/unit/research-data/test_synthesis_evaluator.py

Unit tests for Grounded Synthesis Evaluator (CP-09).
Verifies:
  1. evaluate_item produces audited GroundedEvidenceSynthesis and item metrics
  2. evaluate_benchmark aggregates claim grounding rate and evidence utilization
  3. Intent-stratified aggregation across query intents
"""

from __future__ import annotations

import pytest

from packages.ml_interfaces.query import ClinicalQuery
from packages.research_data.evaluation.synthesis_evaluator import (
    GroundedSynthesisEvaluator,
    SynthesisBenchmarkMetrics,
)
from packages.research_data.models import EvaluationQuery
from packages.research_data.retrieval.contract import RetrievalResult
from packages.research_data.synthesis.contracts import InterpretationPolicy


class MockRetriever:
    """Mock retriever returning predetermined candidates."""

    def __init__(self, candidates: list[RetrievalResult]) -> None:
        self.candidates = candidates

    def retrieve(self, query: ClinicalQuery, top_k: int = 10, **kwargs) -> list[RetrievalResult]:
        return list(self.candidates)


def make_cand(
    evidence_id: str,
    date_str: str,
    value: float = 6.0,
    patient_id: str = "p1",
    analyte: str = "HbA1c",
    flag: str = "normal",
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
        source_provenance="synthea:sample",
    )


class TestGroundedSynthesisEvaluator:
    def test_evaluate_item_metrics(self):
        c1 = make_cand("ev_1", "2022-01-01T00:00:00Z", 5.5)
        c2 = make_cand("ev_2", "2023-01-01T00:00:00Z", 7.0)

        retriever = MockRetriever([c1, c2])
        evaluator = GroundedSynthesisEvaluator(retriever=retriever)

        item = EvaluationQuery(
            query_id="Q_mock_1",
            patient_id="p1",
            query="How has my HbA1c changed?",
            intent="longitudinal_trend",
            target_analyte="HbA1c",
            relevant_evidence_ids=["ev_1", "ev_2"],
            split="test",
        )

        synthesis, metrics = evaluator.evaluate_item(item, mode="oracle")

        assert metrics["claim_grounding_rate"] == 1.0
        assert metrics["hallucination_detected"] == 0.0
        assert metrics["claims_count"] >= 2
        assert metrics["observed_facts_count"] == 2
        assert metrics["derived_facts_count"] >= 1
        assert metrics["unsupported_claims"] == 0.0
        assert synthesis.audit_report.hallucination_detected is False

    def test_evaluate_benchmark_aggregation(self):
        c1 = make_cand("ev_1", "2023-01-01T00:00:00Z", 6.0)
        c2 = make_cand("ev_2", "2024-01-01T00:00:00Z", 6.5)

        retriever = MockRetriever([c1, c2])
        evaluator = GroundedSynthesisEvaluator(retriever=retriever)

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
        assert summary.claim_grounding_rate == 1.0
        assert summary.hallucination_rate == 0.0
        assert summary.total_unsupported_claims == 0
        assert summary.fallback_queries == 0
        assert "current_value" in summary.intent_stratified
        assert "longitudinal_trend" in summary.intent_stratified
