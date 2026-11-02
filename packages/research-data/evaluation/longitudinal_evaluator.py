"""
packages/research-data/evaluation/longitudinal_evaluator.py

Longitudinal Evidence Selection Evaluation Layer (CP-08).
Evaluates evidence set selection quality, trajectory coverage, redundancy suppression,
and provenance completeness across benchmark queries.

Evaluates both:
  Mode A: Oracle Retrieval (Gold structured ClinicalQuery -> CP-06 -> CP-08 Selector)
  Mode B: End-to-End Retrieval (Raw query -> ClinicalQueryParser -> CP-06 -> CP-08 Selector)

Distinguishes:
  - Exact Target Evidence: Gold standard reference evidence IDs from benchmark.
  - Trajectory-Supporting Evidence: Clinically valid observations belonging to the patient's
    target analyte trajectory that establish longitudinal context (e.g. baseline or intermediate).
"""

from __future__ import annotations

from datetime import date
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    TemporalOperator,
)
from packages.research_data.evaluation.harness import BENCHMARK_INTENT_MAP
from packages.research_data.models import EvaluationQuery, ResearchEvidenceRecord
from packages.research_data.retrieval.contract import EvidenceRetriever, parse_date_to_timestamp
from packages.research_data.retrieval.longitudinal_selection import (
    LongitudinalEvidencePackage,
    LongitudinalEvidenceSelector,
)
from packages.research_data.retrieval.trajectory import parse_numeric_value
from services.ai_service.rag.query_understanding import ClinicalQueryParser

logger = logging.getLogger(__name__)


@dataclass
class LongitudinalSelectionMetrics:
    """Aggregated evaluation metrics for longitudinal evidence selection."""

    total_queries: int = 0
    primary_recall: float = 0.0
    primary_precision: float = 0.0
    primary_f1: float = 0.0
    supporting_precision: float | None = None
    supporting_query_count: int = 0
    supporting_obs_count: int = 0
    micro_primary_recall: float = 0.0
    micro_primary_precision: float = 0.0
    micro_primary_f1: float = 0.0
    micro_supporting_precision: float | None = None
    total_recall: float = 0.0
    exact_recall: float = 0.0
    exact_precision: float = 0.0
    exact_f1: float = 0.0
    supporting_recall: float = 0.0
    trajectory_coverage: float = 0.0
    redundant_evidence_rate: float = 0.0
    provenance_completeness: float = 0.0
    avg_selected_count: float = 0.0
    avg_primary_count: float = 0.0
    avg_supporting_count: float = 0.0
    avg_ground_truth_count: float = 0.0
    intent_stratified: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "primary_recall": round(self.primary_recall, 4),
            "primary_precision": round(self.primary_precision, 4),
            "primary_f1": round(self.primary_f1, 4),
            "supporting_precision": round(self.supporting_precision, 4) if self.supporting_precision is not None else None,
            "supporting_query_count": self.supporting_query_count,
            "supporting_obs_count": self.supporting_obs_count,
            "micro_primary_recall": round(self.micro_primary_recall, 4),
            "micro_primary_precision": round(self.micro_primary_precision, 4),
            "micro_primary_f1": round(self.micro_primary_f1, 4),
            "micro_supporting_precision": round(self.micro_supporting_precision, 4) if self.micro_supporting_precision is not None else None,
            "total_recall": round(self.total_recall, 4),
            "exact_recall": round(self.exact_recall, 4),
            "exact_precision": round(self.exact_precision, 4),
            "exact_f1": round(self.exact_f1, 4),
            "supporting_recall": round(self.supporting_recall, 4),
            "trajectory_coverage": round(self.trajectory_coverage, 4),
            "redundant_evidence_rate": round(self.redundant_evidence_rate, 4),
            "provenance_completeness": round(self.provenance_completeness, 4),
            "avg_selected_count": round(self.avg_selected_count, 2),
            "avg_primary_count": round(self.avg_primary_count, 2),
            "avg_supporting_count": round(self.avg_supporting_count, 2),
            "avg_ground_truth_count": round(self.avg_ground_truth_count, 2),
            "intent_stratified": self.intent_stratified,
        }


class LongitudinalEvidenceEvaluator:
    """
    Evaluation harness for CP-08 Longitudinal Evidence Selection.
    Evaluates evidence package coherence and selection metrics over benchmark cohorts.
    """

    def __init__(
        self,
        retriever: EvidenceRetriever,
        selector: LongitudinalEvidenceSelector | None = None,
        parser: ClinicalQueryParser | None = None,
        records: Sequence[ResearchEvidenceRecord] | None = None,
    ) -> None:
        self.retriever = retriever
        self.selector = selector or LongitudinalEvidenceSelector()
        self.parser = parser or ClinicalQueryParser()
        self.records = records

    def evaluate_item(
        self,
        item: EvaluationQuery,
        mode: str = "oracle",
    ) -> tuple[LongitudinalEvidencePackage, dict[str, float]]:
        """Evaluates a single benchmark query item under the specified mode."""
        if mode == "oracle":
            # Mode A: Oracle Structured Query with benchmark gold analyte and intent
            parsed = self.parser.parse(item.query, anchor_date=None)
            intent_enum = BENCHMARK_INTENT_MAP.get(str(item.intent).lower(), parsed.intent)
            comp_target = parsed.comparison_target if intent_enum == QueryIntent.COMPARISON else None

            start_d = parsed.start_date
            end_d = parsed.end_date
            temp_op = parsed.temporal_operator
            limit_val = parsed.limit
            is_abnormal = parsed.abnormal_only

            intent_str = str(item.intent).lower()
            if intent_str == "date_comparison":
                d_a_str = item.metadata.get("date_a")
                d_b_str = item.metadata.get("date_b")
                if d_a_str and d_b_str:
                    d_a = date.fromisoformat(d_a_str[:10])
                    d_b = date.fromisoformat(d_b_str[:10])
                    start_d = min(d_a, d_b)
                    end_d = max(d_a, d_b)
                    temp_op = TemporalOperator.BETWEEN
                    comp_target = ComparisonTarget.PERIOD
            elif intent_str == "last_n_observations":
                limit_val = item.metadata.get("n_requested", parsed.limit or 3)
                temp_op = TemporalOperator.LAST_N
            elif intent_str == "first_abnormal":
                is_abnormal = True
                temp_op = TemporalOperator.ALL_TIME
            elif intent_str == "historical_interval":
                yr = item.metadata.get("year")
                if yr:
                    start_d = date(int(yr), 1, 1)
                    end_d = date(int(yr), 12, 31)
                    temp_op = TemporalOperator.BETWEEN
            elif intent_str == "current_value":
                temp_op = TemporalOperator.LATEST
            elif intent_str == "previous_value":
                comp_target = ComparisonTarget.PREVIOUS
            elif intent_str == "longitudinal_trend":
                temp_op = TemporalOperator.ALL_TIME

            query = ClinicalQuery(
                raw_query=item.query,
                intent=intent_enum,
                analyte_mentions=[item.target_analyte] if item.target_analyte else parsed.analyte_mentions,
                analyte_canonical=item.target_analyte or parsed.analyte_canonical,
                concept_id=parsed.concept_id,
                loinc_code=parsed.loinc_code,
                temporal_operator=temp_op,
                start_date=start_d,
                end_date=end_d,
                relative_window=parsed.relative_window,
                limit=limit_val,
                comparison_target=comp_target,
                abnormal_only=is_abnormal,
                confidence=1.0,
                unresolved_terms=[],
            )
        else:
            # Mode B: End-to-End parse from raw query string with zero gold-label leakage
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

        # Attach patient ID for user-scoped retrieval
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
        pkg = self.selector.select(query, candidates, query_id=item.query_id)

        # 3. Compute Metrics
        metrics = self.compute_package_metrics(pkg, item)
        return pkg, metrics

    def compute_package_metrics(
        self,
        pkg: LongitudinalEvidencePackage,
        item: EvaluationQuery,
    ) -> dict[str, float]:
        """Computes primary, supporting, coverage, redundancy, and provenance metrics for an evidence package."""
        gold_ids = set(item.relevant_evidence_ids)
        sel_ids = set(pkg.selected_evidence_ids)
        primary_ids = set(pkg.primary_evidence_ids) if pkg.primary_evidence_ids else sel_ids

        # Primary evidence metrics (against exact gold target)
        primary_matches = len(primary_ids & gold_ids)
        primary_rec = primary_matches / len(gold_ids) if gold_ids else 1.0
        primary_prec = primary_matches / len(primary_ids) if primary_ids else 0.0
        primary_f1 = (
            2.0 * primary_prec * primary_rec / (primary_prec + primary_rec)
            if (primary_prec + primary_rec) > 0.0
            else 0.0
        )

        # Total evidence set recall
        total_matches = len(sel_ids & gold_ids)
        total_rec = total_matches / len(gold_ids) if gold_ids else 1.0

        # Trajectory-supporting evidence precision (auditable relevance criterion)
        # Evaluates ONLY observations in pkg.supporting_evidence_ids.
        # A supporting observation is relevant IF:
        # 1. It belongs to the patient's target analyte series, AND
        # 2. It has an explicit, verified supporting role in pkg.selection_rationale
        #    (e.g., 'reference_latest' for predecessor comparison context,
        #     'intermediate_milestone' / 'inflection_point' / 'trend_intermediate' for trajectory context)
        #    or is explicitly part of the gold target set.
        supp_ids = set(pkg.supporting_evidence_ids)
        if not supp_ids:
            # If no supporting evidence was selected/emitted, report None (rendered as N/A)
            supp_prec = None
            valid_supp_matches = 0
        else:
            valid_supporting_roles = {
                "reference_latest",
                "comparison_reference",
                "comparison_anchor",
                "intermediate_milestone",
                "inflection_point",
                "trend_intermediate",
                "trend_baseline",
                "baseline",
            }
            target_analyte = item.target_analyte or pkg.target_analyte
            valid_supp_matches = 0
            for sid in supp_ids:
                obs_cand = next((o for o in pkg.selected_observations if o.evidence_id == sid), None)
                if not obs_cand:
                    continue
                if obs_cand.analyte_canonical != target_analyte:
                    continue
                role = pkg.selection_rationale.get(sid, "")
                if role in valid_supporting_roles or sid in gold_ids:
                    valid_supp_matches += 1
            supp_prec = valid_supp_matches / len(supp_ids)

        # Trajectory Coverage: whether at least 1 valid TrajectoryBlock exists
        coverage = 1.0 if len(pkg.trajectory_blocks) > 0 else 0.0

        # Redundant evidence rate: pairwise adjacent points <= 14 days and <= 5% delta
        redundant_count = 0
        obs_list = pkg.selected_observations
        for i in range(len(obs_list) - 1):
            t1 = parse_date_to_timestamp(obs_list[i].observation_date)
            t2 = parse_date_to_timestamp(obs_list[i + 1].observation_date)
            span_days = abs(t2 - t1) / 86400.0
            v1 = parse_numeric_value(obs_list[i].value)
            v2 = parse_numeric_value(obs_list[i + 1].value)
            if span_days <= 14.0 and v1 is not None and v2 is not None:
                denom = max(1.0, abs(v1))
                if abs(v2 - v1) / denom <= 0.05:
                    redundant_count += 1

        redundant_rate = redundant_count / max(1, len(sel_ids))

        # Provenance completeness
        prov_ok = sum(
            1 for o in obs_list
            if o.source_provenance and (o.loinc_code or o.concept_id)
        )
        prov_completeness = prov_ok / max(1, len(obs_list))

        return {
            "primary_recall": primary_rec,
            "primary_precision": primary_prec,
            "primary_f1": primary_f1,
            "exact_recall": primary_rec,
            "exact_precision": primary_prec,
            "exact_f1": primary_f1,
            "supporting_precision": supp_prec,
            "valid_supporting_count": float(valid_supp_matches),
            "supporting_count": float(len(supp_ids)),
            "total_recall": total_rec,
            "supporting_recall": total_rec,
            "trajectory_coverage": coverage,
            "redundant_evidence_rate": redundant_rate,
            "provenance_completeness": prov_completeness,
            "selected_count": float(len(sel_ids)),
            "primary_count": float(len(primary_ids)),
            "primary_matches": float(primary_matches),
            "ground_truth_count": float(len(gold_ids)),
        }

    _compute_package_metrics = compute_package_metrics

    def evaluate_benchmark(
        self,
        benchmark_items: Sequence[EvaluationQuery],
        mode: str = "oracle",
    ) -> LongitudinalSelectionMetrics:
        """Evaluates an entire benchmark suite and computes aggregate metrics."""
        if not benchmark_items:
            return LongitudinalSelectionMetrics()

        total = len(benchmark_items)
        sums: dict[str, float] = {
            "primary_recall": 0.0,
            "primary_precision": 0.0,
            "primary_f1": 0.0,
            "exact_recall": 0.0,
            "exact_precision": 0.0,
            "exact_f1": 0.0,
            "total_recall": 0.0,
            "supporting_recall": 0.0,
            "trajectory_coverage": 0.0,
            "redundant_evidence_rate": 0.0,
            "provenance_completeness": 0.0,
            "selected_count": 0.0,
            "primary_count": 0.0,
            "supporting_count": 0.0,
            "ground_truth_count": 0.0,
        }

        supp_prec_values: list[float] = []
        valid_supp_count = 0
        total_supp_count = 0
        total_primary_matches = 0
        total_primary_count = 0
        total_gold_count = 0

        intent_groups: dict[str, list[dict[str, Any]]] = {}

        for item in benchmark_items:
            _, item_metrics = self.evaluate_item(item, mode=mode)
            for k in sums:
                sums[k] += item_metrics[k]

            if item_metrics["supporting_precision"] is not None:
                supp_prec_values.append(item_metrics["supporting_precision"])
            valid_supp_count += int(item_metrics["valid_supporting_count"])
            total_supp_count += int(item_metrics["supporting_count"])
            total_primary_matches += int(item_metrics["primary_matches"])
            total_primary_count += int(item_metrics["primary_count"])
            total_gold_count += int(item_metrics["ground_truth_count"])

            intent = item.intent or "unknown"
            if intent not in intent_groups:
                intent_groups[intent] = []
            intent_groups[intent].append(item_metrics)

        # Aggregate overall macro means
        agg = {k: v / total for k, v in sums.items()}

        macro_supp_prec = (
            sum(supp_prec_values) / len(supp_prec_values)
            if supp_prec_values
            else None
        )
        micro_supp_prec = (
            valid_supp_count / total_supp_count
            if total_supp_count > 0
            else None
        )

        micro_primary_rec = total_primary_matches / total_gold_count if total_gold_count else 1.0
        micro_primary_prec = total_primary_matches / total_primary_count if total_primary_count else 0.0
        micro_primary_f1 = (
            2.0 * micro_primary_prec * micro_primary_rec / (micro_primary_prec + micro_primary_rec)
            if (micro_primary_prec + micro_primary_rec) > 0.0
            else 0.0
        )

        # Aggregate intent-stratified
        intent_stratified: dict[str, dict[str, Any]] = {}
        for intent, m_list in intent_groups.items():
            cnt = len(m_list)
            strat_supp_vals = [
                m["supporting_precision"] for m in m_list if m["supporting_precision"] is not None
            ]
            strat_supp_prec = (
                round(sum(strat_supp_vals) / len(strat_supp_vals), 4)
                if strat_supp_vals
                else None
            )
            strat_supp_obs = sum(int(m["supporting_count"]) for m in m_list)
            intent_stratified[intent] = {
                "count": float(cnt),
                "primary_recall": round(sum(m["primary_recall"] for m in m_list) / cnt, 4),
                "primary_precision": round(sum(m["primary_precision"] for m in m_list) / cnt, 4),
                "primary_f1": round(sum(m["primary_f1"] for m in m_list) / cnt, 4),
                "exact_recall": round(sum(m["exact_recall"] for m in m_list) / cnt, 4),
                "exact_precision": round(sum(m["exact_precision"] for m in m_list) / cnt, 4),
                "exact_f1": round(sum(m["exact_f1"] for m in m_list) / cnt, 4),
                "supporting_precision": strat_supp_prec,
                "supporting_query_count": len(strat_supp_vals),
                "supporting_obs_count": strat_supp_obs,
                "total_recall": round(sum(m["total_recall"] for m in m_list) / cnt, 4),
                "redundant_evidence_rate": round(sum(m["redundant_evidence_rate"] for m in m_list) / cnt, 4),
            }

        return LongitudinalSelectionMetrics(
            total_queries=total,
            primary_recall=agg["primary_recall"],
            primary_precision=agg["primary_precision"],
            primary_f1=agg["primary_f1"],
            supporting_precision=macro_supp_prec,
            supporting_query_count=len(supp_prec_values),
            supporting_obs_count=total_supp_count,
            micro_primary_recall=micro_primary_rec,
            micro_primary_precision=micro_primary_prec,
            micro_primary_f1=micro_primary_f1,
            micro_supporting_precision=micro_supp_prec,
            total_recall=agg["total_recall"],
            exact_recall=agg["exact_recall"],
            exact_precision=agg["exact_precision"],
            exact_f1=agg["exact_f1"],
            supporting_recall=agg["supporting_recall"],
            trajectory_coverage=agg["trajectory_coverage"],
            redundant_evidence_rate=agg["redundant_evidence_rate"],
            provenance_completeness=agg["provenance_completeness"],
            avg_selected_count=agg["selected_count"],
            avg_primary_count=agg["primary_count"],
            avg_supporting_count=agg["supporting_count"],
            avg_ground_truth_count=agg["ground_truth_count"],
            intent_stratified=intent_stratified,
        )
