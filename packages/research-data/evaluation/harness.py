"""
packages/research-data/evaluation/harness.py

Reproducible Offline Evaluation Harness for Longitudinal Evidence Retrieval (CP-06).
Runs benchmark queries over patient evidence records, computing overall and
intent-stratified IR metrics (MRR, Recall@K, Precision@K, nDCG@K).

Strict Protocol:
  - DEV: development & parameter exploration
  - VAL: model / component selection
  - TEST: final locked evaluation
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    TemporalOperator,
)
from packages.research_data.evaluation.failure_analyzer import (
    QueryDiagnosticRecord,
    RetrievalFailureRecord,
    diagnose_query,
    diagnose_query_failure,
)
from packages.research_data.evaluation.metrics import (
    EvaluationMetrics,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from packages.research_data.models import EvaluationQuery, ResearchEvidenceRecord
from packages.research_data.retrieval.contract import EvidenceRetriever
from services.ai_service.rag.query_understanding import ClinicalQueryParser

logger = logging.getLogger(__name__)


class EvaluationMode(str, Enum):
    """Evaluation protocol mode."""
    ORACLE = "oracle"          # Mode A: Oracle Structured Query -> Retrieval
    END_TO_END = "end_to_end"  # Mode B: Raw Query Text -> ClinicalQueryParser -> Retrieval


# Canonical mapping from benchmark intent strings to QueryIntent taxonomy
BENCHMARK_INTENT_MAP: dict[str, QueryIntent] = {
    "current_value": QueryIntent.CURRENT_VALUE,
    "previous_value": QueryIntent.COMPARISON,
    "last_n_observations": QueryIntent.LAST_N,
    "historical_interval": QueryIntent.HISTORICAL,
    "longitudinal_trend": QueryIntent.TREND,
    "date_comparison": QueryIntent.COMPARISON,
    "first_abnormal": QueryIntent.ABNORMALITY,
}


@dataclass
class EvaluationRunResult:
    """Complete summary of an evaluation run on a split."""
    run_id: str
    method_name: str
    split: str
    timestamp: str
    overall_metrics: EvaluationMetrics
    stratified_metrics: dict[str, EvaluationMetrics] = field(default_factory=dict)
    failures: list[RetrievalFailureRecord] = field(default_factory=list)
    diagnostics: list[QueryDiagnosticRecord] = field(default_factory=list)
    mode: EvaluationMode = EvaluationMode.ORACLE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "method_name": self.method_name,
            "split": self.split,
            "mode": self.mode.value,
            "timestamp": self.timestamp,
            "overall_metrics": self.overall_metrics.to_dict(),
            "stratified_metrics": {
                k: v.to_dict() for k, v in self.stratified_metrics.items()
            },
            "failures_count": len(self.failures),
            "failures": [f.to_dict() for f in self.failures],
            "diagnostics_count": len(self.diagnostics),
            "metadata": self.metadata,
        }


class ResearchEvaluationHarness:
    """
    Offline evaluation harness loading processed Synthea records and evaluation queries.
    """

    def __init__(
        self,
        base_dir: Path = Path("datasets/clinical/processed/synthea"),
        query_parser: ClinicalQueryParser | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.query_parser = query_parser or ClinicalQueryParser()
        self.records_file = self.base_dir / "records.jsonl"
        self.queries_file = self.base_dir / "evaluation" / "queries.jsonl"
        self.splits_file = self.base_dir / "splits.json"

        # Lazy loaded caches
        self._all_records: list[ResearchEvidenceRecord] | None = None
        self._all_queries: list[EvaluationQuery] | None = None
        self._parsed_queries: dict[str, ClinicalQuery] = {}

    def load_records(self) -> list[ResearchEvidenceRecord]:
        """Loads all processed research evidence records."""
        if self._all_records is None:
            records: list[ResearchEvidenceRecord] = []
            with open(self.records_file, mode="r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(ResearchEvidenceRecord.from_dict(json.loads(line)))
            self._all_records = records
            logger.info("Loaded %d research evidence records from %s", len(records), self.records_file)
        return self._all_records

    def load_queries(
        self, split: Literal["dev", "val", "test", "all"] = "all"
    ) -> list[EvaluationQuery]:
        """Loads benchmark queries, optionally filtered by split."""
        if self._all_queries is None:
            queries: list[EvaluationQuery] = []
            with open(self.queries_file, mode="r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        queries.append(EvaluationQuery.from_dict(json.loads(line)))
            self._all_queries = queries
            logger.info("Loaded %d benchmark queries from %s", len(queries), self.queries_file)

        if split == "all":
            return self._all_queries
        return [q for q in self._all_queries if q.split == split]

    def get_parsed_query(
        self,
        eval_query: EvaluationQuery,
        mode: EvaluationMode = EvaluationMode.ORACLE,
    ) -> ClinicalQuery:
        """
        Translates an EvaluationQuery into a parsed ClinicalQuery.
        MODE A (ORACLE): Uses ground-truth target_analyte, LOINC, and benchmark intent
                         to evaluate the retrieval engine in isolation.
        MODE B (END_TO_END): Consumes strictly raw query text via ClinicalQueryParser
                             with ZERO gold-label injection.
        """
        cache_key = f"{eval_query.query_id}_{mode.value}"
        if cache_key in self._parsed_queries:
            return self._parsed_queries[cache_key]

        if mode == EvaluationMode.END_TO_END:
            # Mode B: Strictly raw query text -> ClinicalQueryParser
            # Attach ONLY patient_id (identity context); zero benchmark labels touched
            parsed = self.query_parser.parse(eval_query.query)
            setattr(parsed, "patient_id", eval_query.patient_id)
            self._parsed_queries[cache_key] = parsed
            return parsed

        # Mode A: Oracle Structured Query (Gold labels for retrieval engine isolation)
        parsed = self.query_parser.parse(eval_query.query)
        setattr(parsed, "patient_id", eval_query.patient_id)

        # Grounding: if benchmark specifies target_analyte, ensure it aligns
        if eval_query.target_analyte:
            parsed.analyte_canonical = eval_query.target_analyte
            from packages.research_data.terminology import LOINC_TO_CANONICAL
            for l_code, data in LOINC_TO_CANONICAL.items():
                if data["canonical"].lower() == eval_query.target_analyte.lower():
                    parsed.loinc_code = l_code
                    parsed.concept_id = f"LOINC:{l_code}"
                    break

        # Align intent with benchmark expectation if parser was ambiguous
        expected_intent = BENCHMARK_INTENT_MAP.get(eval_query.intent)
        if expected_intent and parsed.intent != expected_intent:
            parsed.intent = expected_intent

        # Refine specific temporal intents
        if eval_query.intent == "previous_value":
            parsed.comparison_target = ComparisonTarget.PREVIOUS
        elif eval_query.intent == "first_abnormal":
            parsed.abnormal_only = True
        elif eval_query.intent == "current_value":
            parsed.temporal_operator = TemporalOperator.LATEST
        elif eval_query.intent == "last_n_observations":
            parsed.limit = eval_query.metadata.get("n", 3)

        self._parsed_queries[cache_key] = parsed
        return parsed

    def evaluate_retriever(
        self,
        retriever: EvidenceRetriever,
        method_name: str,
        split: Literal["dev", "val", "test"] = "val",
        mode: EvaluationMode = EvaluationMode.ORACLE,
        top_k: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationRunResult:
        """
        Runs full benchmark evaluation for a given retriever on the specified split.
        Computes overall metrics and intent-stratified breakdowns.
        """
        records = self.load_records()
        queries = self.load_queries(split=split)

        logger.info(
            "Evaluating '%s' [%s] on split '%s' (%d queries, %d total evidence records)...",
            method_name,
            mode.value.upper(),
            split,
            len(queries),
            len(records),
        )

        query_metrics: list[dict[str, float]] = []
        intent_query_metrics: dict[str, list[dict[str, float]]] = {}
        failures: list[RetrievalFailureRecord] = []
        diagnostics: list[QueryDiagnosticRecord] = []

        for q in queries:
            c_query = self.get_parsed_query(q, mode=mode)
            relevant_ids = set(q.relevant_evidence_ids)

            # Execute patient-scoped retrieval
            retrieved = retriever.retrieve(
                query=c_query,
                evidence=records,
                top_k=top_k,
                patient_id=q.patient_id,
            )

            retrieved_ids = [r.evidence_id for r in retrieved]

            # Compute IR metrics
            q_res = {
                "mrr": reciprocal_rank(retrieved_ids, relevant_ids),
                "recall_at_1": recall_at_k(retrieved_ids, relevant_ids, 1),
                "recall_at_3": recall_at_k(retrieved_ids, relevant_ids, 3),
                "recall_at_5": recall_at_k(retrieved_ids, relevant_ids, 5),
                "recall_at_10": recall_at_k(retrieved_ids, relevant_ids, 10),
                "precision_at_1": precision_at_k(retrieved_ids, relevant_ids, 1),
                "precision_at_3": precision_at_k(retrieved_ids, relevant_ids, 3),
                "precision_at_5": precision_at_k(retrieved_ids, relevant_ids, 5),
                "precision_at_10": precision_at_k(retrieved_ids, relevant_ids, 10),
                "ndcg_at_5": ndcg_at_k(retrieved_ids, relevant_ids, 5),
                "ndcg_at_10": ndcg_at_k(retrieved_ids, relevant_ids, 10),
            }


            query_metrics.append(q_res)
            intent_query_metrics.setdefault(q.intent, []).append(q_res)

            # Full diagnostic record for every query
            diag_rec = diagnose_query(q, retrieved, records, method_name=method_name, k=top_k)
            diagnostics.append(diag_rec)

            # Failure diagnosis (top-k miss)
            fail_rec = diagnose_query_failure(q, retrieved, records, k=top_k)
            if fail_rec is not None:
                failures.append(fail_rec)

        overall = EvaluationMetrics.aggregate(query_metrics)
        stratified = {
            intent: EvaluationMetrics.aggregate(metric_list)
            for intent, metric_list in intent_query_metrics.items()
        }

        run_id = f"run_{method_name.lower().replace(' ', '_').replace('+', '_')}_{mode.value}_{split}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return EvaluationRunResult(
            run_id=run_id,
            method_name=method_name,
            split=split,
            timestamp=datetime.now().isoformat(),
            overall_metrics=overall,
            stratified_metrics=stratified,
            failures=failures,
            diagnostics=diagnostics,
            mode=mode,
            metadata=metadata or {},
        )

    def save_run(
        self,
        run_result: EvaluationRunResult,
        output_dir: Path = Path("validation/retrieval"),
    ) -> Path:
        """Saves run JSON to runs/, failures to failures/, and diagnostics to diagnostics/."""
        runs_dir = output_dir / "runs"
        failures_dir = output_dir / "failures"
        diagnostics_dir = output_dir / "diagnostics"

        runs_dir.mkdir(parents=True, exist_ok=True)
        failures_dir.mkdir(parents=True, exist_ok=True)
        diagnostics_dir.mkdir(parents=True, exist_ok=True)

        run_file = runs_dir / f"{run_result.run_id}.json"
        with open(run_file, mode="w", encoding="utf-8") as f:
            json.dump(run_result.to_dict(), f, indent=2)

        if run_result.failures:
            fail_file = failures_dir / f"failures_{run_result.run_id}.jsonl"
            with open(fail_file, mode="w", encoding="utf-8") as f:
                for fail in run_result.failures:
                    f.write(json.dumps(fail.to_dict()) + "\n")

        if run_result.diagnostics:
            diag_file = diagnostics_dir / f"diagnostics_{run_result.run_id}.jsonl"
            with open(diag_file, mode="w", encoding="utf-8") as f:
                for diag in run_result.diagnostics:
                    f.write(json.dumps(diag.to_dict()) + "\n")

        logger.info("Saved evaluation run to %s", run_file)
        return run_file
