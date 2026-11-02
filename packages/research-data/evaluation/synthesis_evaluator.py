"""
packages/research-data/evaluation/synthesis_evaluator.py

Evaluation Harness for Grounded Clinical Evidence Synthesis (CP-09).
Evaluates claim-level grounding rate, hallucination detection rate,
evidence utilization rate, and fact extraction correctness across benchmark splits.

Evaluates both:
  Mode A: Oracle Retrieval (Gold structured ClinicalQuery -> CP-06 -> CP-08 -> CP-09)
  Mode B: End-to-End Retrieval (Raw Query -> Parser -> CP-06 -> CP-08 -> CP-09)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

from packages.ml_interfaces.query import ClinicalQuery, QueryIntent
from packages.research_data.evaluation.harness import BENCHMARK_INTENT_MAP
from packages.research_data.models import EvaluationQuery, ResearchEvidenceRecord
from packages.research_data.retrieval.contract import EvidenceRetriever
from packages.research_data.retrieval.longitudinal_selection import (
    LongitudinalEvidenceSelector,
)
from packages.research_data.synthesis.contracts import (
    GroundedEvidenceSynthesis,
    InterpretationPolicy,
)
from packages.research_data.synthesis.synthesizer import GroundedEvidenceSynthesizer
from services.ai_service.rag.query_understanding import ClinicalQueryParser

logger = logging.getLogger(__name__)


@dataclass
class SynthesisBenchmarkMetrics:
    """Aggregated evaluation metrics for grounded clinical synthesis."""

    total_queries: int = 0
    claim_grounding_rate: float = 0.0
    evidence_utilization_rate: float = 0.0
    hallucination_rate: float = 0.0
    avg_claims_per_query: float = 0.0
    avg_observed_facts_per_query: float = 0.0
    avg_derived_facts_per_query: float = 0.0
    total_unsupported_claims: int = 0
    fallback_queries: int = 0
    intent_stratified: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "claim_grounding_rate": round(self.claim_grounding_rate, 4),
            "evidence_utilization_rate": round(self.evidence_utilization_rate, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "avg_claims_per_query": round(self.avg_claims_per_query, 2),
            "avg_observed_facts_per_query": round(self.avg_observed_facts_per_query, 2),
            "avg_derived_facts_per_query": round(self.avg_derived_facts_per_query, 2),
            "total_unsupported_claims": self.total_unsupported_claims,
            "fallback_queries": self.fallback_queries,
            "intent_stratified": self.intent_stratified,
        }


class GroundedSynthesisEvaluator:
    """
    Evaluator for Grounded Evidence Synthesis across benchmark cohorts.
    Audits claim grounding and provenance completeness for research evaluation.
    """

    def __init__(
        self,
        retriever: EvidenceRetriever,
        selector: LongitudinalEvidenceSelector | None = None,
        synthesizer: GroundedEvidenceSynthesizer | None = None,
        parser: ClinicalQueryParser | None = None,
        records: Sequence[ResearchEvidenceRecord] | None = None,
        interpretation_policy: InterpretationPolicy = InterpretationPolicy.DISABLED,
    ) -> None:
        self.retriever = retriever
        self.selector = selector or LongitudinalEvidenceSelector()
        self.synthesizer = synthesizer or GroundedEvidenceSynthesizer(
            interpretation_policy=interpretation_policy
        )
        self.parser = parser or ClinicalQueryParser()
        self.records = records
        self.interpretation_policy = interpretation_policy

    def evaluate_item(
        self,
        item: EvaluationQuery,
        mode: str = "oracle",
    ) -> tuple[GroundedEvidenceSynthesis, dict[str, Any]]:
        """Evaluates synthesis for a single benchmark query."""
        if mode == "oracle":
            parsed = self.parser.parse(item.query, anchor_date=None)
            intent_enum = BENCHMARK_INTENT_MAP.get(str(item.intent).lower(), parsed.intent)
            comp_target = parsed.comparison_target if intent_enum == QueryIntent.COMPARISON else None
            query = ClinicalQuery(
                raw_query=item.query,
                intent=intent_enum,
                analyte_mentions=[item.target_analyte] if item.target_analyte else parsed.analyte_mentions,
                analyte_canonical=item.target_analyte or parsed.analyte_canonical,
                concept_id=parsed.concept_id,
                loinc_code=parsed.loinc_code,
                temporal_operator=parsed.temporal_operator,
                start_date=parsed.start_date,
                end_date=parsed.end_date,
                relative_window=parsed.relative_window,
                limit=parsed.limit,
                comparison_target=comp_target,
                abnormal_only=parsed.abnormal_only,
                confidence=1.0,
                unresolved_terms=[],
            )
        else:
            parsed = self.parser.parse(item.query, anchor_date=None)
            query = ClinicalQuery(
                raw_query=item.query,
                intent=parsed.intent,
                analyte_mentions=parsed.analyte_mentions,
                analyte_canonical=parsed.analyte_canonical,
                concept_id=parsed.concept_id,
                loinc_code=parsed.loinc_code,
                temporal_operator=parsed.temporal_operator,
                start_date=parsed.start_date,
                end_date=parsed.end_date,
                relative_window=parsed.relative_window,
                limit=parsed.limit,
                comparison_target=parsed.comparison_target,
                abnormal_only=parsed.abnormal_only,
                confidence=parsed.confidence,
                unresolved_terms=parsed.unresolved_terms,
            )

        setattr(query, "patient_id", item.patient_id)

        # 1. Candidate Retrieval (CP-06)
        kwargs: dict[str, Any] = {"top_k": 20, "patient_id": item.patient_id}
        if self.records is not None:
            kwargs["evidence"] = self.records

        try:
            candidates = self.retriever.retrieve(query, **kwargs)
        except TypeError:
            candidates = self.retriever.retrieve(query, top_k=20)

        # 2. Evidence Selection (CP-08)
        package = self.selector.select(query, candidates, query_id=item.query_id)

        # 3. Grounded Synthesis (CP-09)
        synthesis = self.synthesizer.synthesize(
            package=package,
            interpretation_policy=self.interpretation_policy,
        )

        item_metrics = {
            "claim_grounding_rate": synthesis.audit_report.claim_grounding_rate,
            "evidence_utilization_rate": synthesis.audit_report.evidence_utilization_rate,
            "hallucination_detected": 1.0 if synthesis.audit_report.hallucination_detected else 0.0,
            "claims_count": float(len(synthesis.claims)),
            "observed_facts_count": float(len(synthesis.observed_facts)),
            "derived_facts_count": float(len(synthesis.derived_facts)),
            "unsupported_claims": float(synthesis.audit_report.unsupported_claims),
            "is_fallback": 1.0 if not synthesis.claims else 0.0,
        }

        return synthesis, item_metrics

    def evaluate_benchmark(
        self,
        benchmark_items: Sequence[EvaluationQuery],
        mode: str = "oracle",
    ) -> SynthesisBenchmarkMetrics:
        """Evaluates an entire benchmark suite and aggregates synthesis metrics."""
        if not benchmark_items:
            return SynthesisBenchmarkMetrics()

        total = len(benchmark_items)
        sums: dict[str, float] = {
            "claim_grounding_rate": 0.0,
            "evidence_utilization_rate": 0.0,
            "hallucination_detected": 0.0,
            "claims_count": 0.0,
            "observed_facts_count": 0.0,
            "derived_facts_count": 0.0,
            "unsupported_claims": 0.0,
            "is_fallback": 0.0,
        }

        intent_groups: dict[str, list[dict[str, float]]] = {}

        for item in benchmark_items:
            _, item_metrics = self.evaluate_item(item, mode=mode)
            for k in sums:
                sums[k] += item_metrics[k]

            intent = item.intent or "unknown"
            if intent not in intent_groups:
                intent_groups[intent] = []
            intent_groups[intent].append(item_metrics)

        agg = {k: v / total for k, v in sums.items()}

        intent_stratified: dict[str, dict[str, float]] = {}
        for intent, m_list in intent_groups.items():
            cnt = len(m_list)
            intent_stratified[intent] = {
                "count": float(cnt),
                "claim_grounding_rate": round(sum(m["claim_grounding_rate"] for m in m_list) / cnt, 4),
                "evidence_utilization_rate": round(sum(m["evidence_utilization_rate"] for m in m_list) / cnt, 4),
                "hallucination_rate": round(sum(m["hallucination_detected"] for m in m_list) / cnt, 4),
                "avg_claims": round(sum(m["claims_count"] for m in m_list) / cnt, 2),
            }

        return SynthesisBenchmarkMetrics(
            total_queries=total,
            claim_grounding_rate=agg["claim_grounding_rate"],
            evidence_utilization_rate=agg["evidence_utilization_rate"],
            hallucination_rate=agg["hallucination_detected"],
            avg_claims_per_query=agg["claims_count"],
            avg_observed_facts_per_query=agg["observed_facts_count"],
            avg_derived_facts_per_query=agg["derived_facts_count"],
            total_unsupported_claims=int(sums["unsupported_claims"]),
            fallback_queries=int(sums["is_fallback"]),
            intent_stratified=intent_stratified,
        )
