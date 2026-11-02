"""
scripts/run_longitudinal_selection_benchmark.py

Executes the CP-08 Longitudinal Evidence Selection Evaluation across benchmark splits:
  - DEV (36 queries)
  - VAL (25 queries)
  - TEST-DIAGNOSTIC (25 queries, reclassified from CP-05.5 development iterations)
  - TEST-HELDOUT (25 queries, untouched held-out evaluation set from unsampled test series)

Evaluates:
  - Primary evidence metrics (Recall, Precision, F1)
  - Trajectory-supporting evidence metrics (Precision, with documented N/A for empty sets)
  - Trajectory coverage
  - Redundant evidence rate
  - Provenance completeness
Across both:
  - Mode A: Oracle Structured Retrieval
  - Mode B: End-to-End Raw-Text Retrieval (Zero Gold-Label Leakage)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Ensure root is on sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import scripts.bootstrap_imports  # noqa: F401
from packages.research_data.evaluation.harness import ResearchEvaluationHarness
from packages.research_data.evaluation.longitudinal_evaluator import (
    LongitudinalEvidenceEvaluator,
    LongitudinalSelectionMetrics,
)
from packages.research_data.models import EvaluationQuery, ResearchEvidenceRecord
from packages.research_data.retrieval.bm25 import EvidenceBM25Retriever
from packages.research_data.retrieval.dense import EvidenceDenseRetriever
from packages.research_data.retrieval.longitudinal_selection import LongitudinalEvidenceSelector
from packages.research_data.retrieval.pipeline import ModularEvidenceRetriever, ScoringWeights

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("longitudinal_benchmark")


def load_held_out_queries(path: Path) -> list[EvaluationQuery]:
    """Loads independent held-out evaluation queries if file exists."""
    if not path.exists():
        return []
    queries: list[EvaluationQuery] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(EvaluationQuery.from_dict(json.loads(line)))
    return queries


def run_longitudinal_benchmark(
    splits: list[str] = ["dev", "val", "test"],
    modes: list[str] = ["oracle", "end_to_end"],
) -> dict[str, dict[str, LongitudinalSelectionMetrics]]:
    harness = ResearchEvaluationHarness()
    records = harness.load_records()

    logger.info("Initializing retrievers and building index over %d records...", len(records))
    bm25 = EvidenceBM25Retriever()

    dense = EvidenceDenseRetriever()
    dense.index_evidence(records)

    # Base CP-06 Retriever: Hybrid + Temporal + Concept
    base_retriever = ModularEvidenceRetriever(
        weights=ScoringWeights.hybrid_temporal_concept(),
        method_name="Hybrid + Temporal + Concept",
        bm25_retriever=bm25,
        dense_retriever=dense,
        fusion_strategy="weighted",
        hard_temporal_filter=True,
    )

    selector = LongitudinalEvidenceSelector()
    evaluator = LongitudinalEvidenceEvaluator(retriever=base_retriever, selector=selector, records=records)

    results: dict[str, dict[str, LongitudinalSelectionMetrics]] = {}

    for split in splits:
        queries = harness.load_queries(split=split)  # type: ignore[arg-type]
        results[split] = {}
        for mode in modes:
            logger.info("Evaluating split '%s' in mode '%s' (%d queries)...", split, mode, len(queries))
            metrics = evaluator.evaluate_benchmark(queries, mode=mode)
            results[split][mode] = metrics

    # Also evaluate independent untouched held-out query set if available
    held_out_file = Path("datasets/clinical/processed/synthea/evaluation/held_out_queries.jsonl")
    held_out_queries = load_held_out_queries(held_out_file)
    if held_out_queries:
        results["held_out_test"] = {}
        for mode in modes:
            logger.info("Evaluating untouched 'held_out_test' in mode '%s' (%d queries)...", mode, len(held_out_queries))
            metrics = evaluator.evaluate_benchmark(held_out_queries, mode=mode)
            results["held_out_test"][mode] = metrics

    # Generate Markdown Summary
    summary_path = Path("validation/retrieval/summaries/longitudinal_selection_summary.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# MEDIVAULT LONGITUDINAL EVIDENCE SELECTION BENCHMARK (CP-08)",
        "",
        "> **Research Status:** Category B Functional Prototype IR / Selection Evidence",
        "> Evaluated over the controlled Synthea development cohort (60 patients, 2,790 observations).",
        "> Distinguishes exact target evidence from acceptable trajectory-supporting evidence.",
        "",
        "## 1. Overall Comparative Results Across Splits",
        "",
        "| Split | Mode | Queries | Primary Recall | Primary Prec | Primary F1 | Supp Prec | Supp Obs (Q) | Total Recall | Traj Coverage | Redundant Rate | Provenance OK | Avg Sel |",
        "|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    all_splits_to_show = list(splits)
    if "held_out_test" in results:
        all_splits_to_show.append("held_out_test")

    split_labels = {
        "dev": "DEV",
        "val": "VAL",
        "test": "TEST-DIAGNOSTIC",
        "held_out_test": "TEST-HELDOUT",
    }

    for split in all_splits_to_show:
        for mode in modes:
            m = results[split][mode]
            supp_str = f"{m.supporting_precision:.4f}" if m.supporting_precision is not None else "N/A"
            supp_counts = f"{m.supporting_obs_count} (Q={m.supporting_query_count})"
            lbl = split_labels.get(split, split.upper())
            lines.append(
                f"| **{lbl}** | `{mode}` | {m.total_queries} | "
                f"{m.primary_recall:.4f} | {m.primary_precision:.4f} | {m.primary_f1:.4f} | "
                f"{supp_str} | {supp_counts} | {m.total_recall:.4f} | {m.trajectory_coverage:.4f} | "
                f"{m.redundant_evidence_rate:.4f} | {m.provenance_completeness:.4f} | {m.avg_selected_count:.1f} |"
            )

    # 2. Intent-Stratified Breakdown for TEST-DIAGNOSTIC
    lines.extend([
        "",
        "## 2. Intent-Stratified Breakdown: TEST-DIAGNOSTIC Split (25 Queries)",
        "",
        "> **Diagnostic Classification:** This 25-query split was inspected during iterative development of CP-08",
        "> selection heuristics. Reclassified as a diagnostic development split.",
        "",
        "### Mode A: Oracle Retrieval",
        "",
        "| Query Intent | Count | Primary Recall | Primary Precision | Primary F1 | Supporting Precision | Supp Obs (Q) | Total Recall | Redundant Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])

    test_oracle = results.get("test", {}).get("oracle")
    if test_oracle:
        for intent, stats in sorted(test_oracle.intent_stratified.items()):
            total_recall = stats.get("total_recall", stats.get("exact_recall", 0.0))
            supp_p = stats.get("supporting_precision")
            supp_str = f"{supp_p:.4f}" if supp_p is not None else "N/A"
            supp_q = int(stats.get("supporting_query_count", 0))
            supp_o = int(stats.get("supporting_obs_count", 0))
            lines.append(
                f"| `{intent}` | {int(stats['count'])} | "
                f"{stats['primary_recall']:.4f} | "
                f"{stats['primary_precision']:.4f} | "
                f"{stats['primary_f1']:.4f} | "
                f"{supp_str} | {supp_o} (Q={supp_q}) | "
                f"{total_recall:.4f} | "
                f"{stats['redundant_evidence_rate']:.4f} |"
            )

    lines.extend([
        "",
        "### Mode B: End-to-End Retrieval (Zero Gold-Label Leakage)",
        "",
        "| Query Intent | Count | Primary Recall | Primary Precision | Primary F1 | Supporting Precision | Supp Obs (Q) | Total Recall | Redundant Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])

    test_e2e = results.get("test", {}).get("end_to_end")
    if test_e2e:
        for intent, stats in sorted(test_e2e.intent_stratified.items()):
            total_recall = stats.get("total_recall", stats.get("exact_recall", 0.0))
            supp_p = stats.get("supporting_precision")
            supp_str = f"{supp_p:.4f}" if supp_p is not None else "N/A"
            supp_q = int(stats.get("supporting_query_count", 0))
            supp_o = int(stats.get("supporting_obs_count", 0))
            lines.append(
                f"| `{intent}` | {int(stats['count'])} | "
                f"{stats['primary_recall']:.4f} | "
                f"{stats['primary_precision']:.4f} | "
                f"{stats['primary_f1']:.4f} | "
                f"{supp_str} | {supp_o} (Q={supp_q}) | "
                f"{total_recall:.4f} | "
                f"{stats['redundant_evidence_rate']:.4f} |"
            )

    # 3. Intent-Stratified Breakdown for TEST-HELDOUT
    if "held_out_test" in results:
        lines.extend([
            "",
            "## 3. Intent-Stratified Breakdown: Independent Untouched TEST-HELDOUT Split (25 Queries)",
            "",
            "> **Integrity Protocol:** Evaluated on an untouched held-out query set sampled from unsampled longitudinal",
            "> series of the 12 test patients, with frozen code and zero parameter tuning on this split.",
            "",
            "### Mode A: Oracle Retrieval",
            "",
            "| Query Intent | Count | Primary Recall | Primary Precision | Primary F1 | Supporting Precision | Supp Obs (Q) | Total Recall | Redundant Rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        ho_oracle = results.get("held_out_test", {}).get("oracle")
        if ho_oracle:
            for intent, stats in sorted(ho_oracle.intent_stratified.items()):
                total_recall = stats.get("total_recall", stats.get("exact_recall", 0.0))
                supp_p = stats.get("supporting_precision")
                supp_str = f"{supp_p:.4f}" if supp_p is not None else "N/A"
                supp_q = int(stats.get("supporting_query_count", 0))
                supp_o = int(stats.get("supporting_obs_count", 0))
                lines.append(
                    f"| `{intent}` | {int(stats['count'])} | "
                    f"{stats['primary_recall']:.4f} | "
                    f"{stats['primary_precision']:.4f} | "
                    f"{stats['primary_f1']:.4f} | "
                    f"{supp_str} | {supp_o} (Q={supp_q}) | "
                    f"{total_recall:.4f} | "
                    f"{stats['redundant_evidence_rate']:.4f} |"
                )

        lines.extend([
            "",
            "### Mode B: End-to-End Retrieval (Zero Gold-Label Leakage)",
            "",
            "| Query Intent | Count | Primary Recall | Primary Precision | Primary F1 | Supporting Precision | Supp Obs (Q) | Total Recall | Redundant Rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        ho_e2e = results.get("held_out_test", {}).get("end_to_end")
        if ho_e2e:
            for intent, stats in sorted(ho_e2e.intent_stratified.items()):
                total_recall = stats.get("total_recall", stats.get("exact_recall", 0.0))
                supp_p = stats.get("supporting_precision")
                supp_str = f"{supp_p:.4f}" if supp_p is not None else "N/A"
                supp_q = int(stats.get("supporting_query_count", 0))
                supp_o = int(stats.get("supporting_obs_count", 0))
                lines.append(
                    f"| `{intent}` | {int(stats['count'])} | "
                    f"{stats['primary_recall']:.4f} | "
                    f"{stats['primary_precision']:.4f} | "
                    f"{stats['primary_f1']:.4f} | "
                    f"{supp_str} | {supp_o} (Q={supp_q}) | "
                    f"{total_recall:.4f} | "
                    f"{stats['redundant_evidence_rate']:.4f} |"
                )

    lines.extend([
        "",
        "## 4. Methodological & Research Notes",
        "- **Test-Set Integrity & Reclassification:** The original 25 TEST queries in `queries.jsonl` are classified as `TEST-DIAGNOSTIC` due to repeated inspection during iterative debugging. An independent untouched evaluation split of 25 queries (`held_out_queries.jsonl`) was established across the 12 test patients with frozen selector code.",
        "- **Primary vs. Supporting Evidence Separation:** Primary evidence directly satisfies the intent-specific query target (e.g. immediate predecessor for `previous_value`, both dates for `date_comparison`, requested N points for `last_n_observations`). Supporting evidence supplies trajectory context (e.g. latest reference observation for `previous_value`, intermediate milestones / inflection points for `longitudinal_trend`).",
        "- **Supporting Precision Metric Convention:** Supporting precision is reported as `N/A` for queries or intent groups that emit zero supporting observations ($|S| = 0$). For queries emitting supporting observations, it evaluates whether every emitted point possesses a verified clinical rationale and matches the target analyte series.",
        "- **Abnormality Evaluation Policy:** Deterministic thresholds are labeled as `SYNTHETIC_COHORT_ABNORMALITY_HEURISTICS`. Precedence strictly prioritizes: (1) recorded laboratory flag -> (2) recorded laboratory reference interval -> (3) synthetic-cohort heuristic fallback.",
        "- **Macro- vs. Micro-Averaging:** Primary metrics report macro-averages (unweighted query mean) as primary table columns. For supporting precision, macro precision is calculated over queries with $|S| > 0$, while micro precision evaluates valid supporting observations over all emitted supporting observations.",
        "- **Zero Oracle Leakage in Mode B:** End-to-End mode consumes strictly raw query strings via `ClinicalQueryParser`, with zero access to benchmark gold metadata, target analytes, or relevance annotations.",
        "",
    ])

    content = "\n".join(lines) + "\n"
    summary_path.write_text(content, encoding="utf-8")
    logger.info("Summary written to %s", summary_path)
    print(content)

    return results


if __name__ == "__main__":
    run_longitudinal_benchmark()
