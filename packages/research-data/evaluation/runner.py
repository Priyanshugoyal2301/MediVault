"""
packages/research-data/evaluation/runner.py

Experiment Runner for Longitudinal Evidence Retrieval (CP-06).
Executes the primary experimental progression across splits:
  1. BM25
  2. Dense
  3. Hybrid
  4. Hybrid + Temporal
  5. Hybrid + Temporal + Concept
  6. Full Scoring Pipeline

Produces machine-readable JSON runs and human-readable Markdown evaluation summaries.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

from packages.research_data.evaluation.harness import (
    EvaluationRunResult,
    ResearchEvaluationHarness,
)
from packages.research_data.retrieval.bm25 import EvidenceBM25Retriever
from packages.research_data.retrieval.dense import EvidenceDenseRetriever
from packages.research_data.retrieval.hybrid import HybridEvidenceRetriever
from packages.research_data.retrieval.pipeline import (
    ModularEvidenceRetriever,
    ScoringWeights,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_experiment_retrievers(
    dense_retriever: EvidenceDenseRetriever,
) -> dict[str, EvidenceRetriever]:
    """
    Constructs the experimental progression retrievers, sharing the indexed dense retriever:
      A. BM25 Baseline
      B. Dense Semantic Baseline
      C. Weighted Hybrid (Lexical + Dense)
      D. RRF (Reciprocal Rank Fusion)
      E. Weighted Hybrid + Temporal
      F. RRF + Temporal
      G. Hybrid + Temporal + Concept (CP-06 Full Pipeline Baseline)
      H. Hybrid + Temporal + Concept + Trajectory (CP-07 Trajectory-Aware Re-ranking)
    """
    from packages.research_data.retrieval.trajectory_reranker import (
        TrajectoryAwareRetriever,
        TrajectoryReranker,
    )

    bm25 = EvidenceBM25Retriever()
    weighted_hybrid = HybridEvidenceRetriever(
        bm25_retriever=bm25, dense_retriever=dense_retriever, alpha_lexical=0.5, alpha_dense=0.5
    )

    full_cp06 = ModularEvidenceRetriever(
        weights=ScoringWeights.hybrid_temporal_concept(),
        method_name="Hybrid + Temporal + Concept",
        bm25_retriever=bm25,
        dense_retriever=dense_retriever,
        fusion_strategy="weighted",
        hard_temporal_filter=True,
    )

    trajectory_cp07 = TrajectoryAwareRetriever(
        base_retriever=full_cp06,
        reranker=TrajectoryReranker(trajectory_weight=0.25),
        method_name="Hybrid + Temporal + Concept + Trajectory",
    )

    return {
        "BM25": bm25,
        "Dense": dense_retriever,
        "Weighted Hybrid": weighted_hybrid,
        "RRF": ModularEvidenceRetriever(
            weights=ScoringWeights.rrf(),
            method_name="RRF",
            bm25_retriever=bm25,
            dense_retriever=dense_retriever,
            fusion_strategy="rrf",
            hard_temporal_filter=False,
        ),
        "Weighted Hybrid + Temporal": ModularEvidenceRetriever(
            weights=ScoringWeights.hybrid_temporal(),
            method_name="Weighted Hybrid + Temporal",
            bm25_retriever=bm25,
            dense_retriever=dense_retriever,
            fusion_strategy="weighted",
            hard_temporal_filter=True,
        ),
        "RRF + Temporal": ModularEvidenceRetriever(
            weights=ScoringWeights.rrf_temporal(),
            method_name="RRF + Temporal",
            bm25_retriever=bm25,
            dense_retriever=dense_retriever,
            fusion_strategy="rrf",
            hard_temporal_filter=True,
        ),
        "Hybrid + Temporal + Concept": full_cp06,
        "Hybrid + Temporal + Concept + Trajectory": trajectory_cp07,
    }


def generate_markdown_summary(
    split: str,
    results: dict[str, EvaluationRunResult],
    output_path: Path,
    mode: str = "oracle",
) -> str:
    """
    Formats comparative evaluation results as a research markdown report.
    """
    mode_title = (
        "MODE A — ORACLE RETRIEVAL (Gold Structured ClinicalQuery -> Retrieval Isolation)"
        if mode == "oracle"
        else "MODE B — END-TO-END RETRIEVAL (Raw Query -> ClinicalQueryParser -> Retrieval)"
    )

    lines: list[str] = [
        f"# MEDIVAULT EVIDENCE RETRIEVAL BENCHMARK — {split.upper()} SPLIT",
        "",
        f"**Evaluation Mode:** `{mode_title}`",
        f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- **Dataset:** Controlled Synthea Sample (60 patients, 2,790 observations)",
        f"- **Split:** {split}",
        "- **Evaluation Unit:** Atomic Evidence Observation (`ResearchEvidenceRecord`)",
        "",
        "## 1. Overall Comparative Results",
        "",
        "| Retrieval Method | MRR | Recall@5 | Recall@10 | Precision@5 | Precision@10 | nDCG@5 | nDCG@10 | Failures |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for name, res in results.items():
        m = res.overall_metrics
        lines.append(
            f"| **{name}** | {m.mrr:.4f} | {m.recall_at_5:.4f} | {m.recall_at_10:.4f} | "
            f"{m.precision_at_5:.4f} | {m.precision_at_10:.4f} | {m.ndcg_at_5:.4f} | {m.ndcg_at_10:.4f} | {len(res.failures)} |"
        )

    lines.extend([
        "",
        "## 2. Intent-Stratified Performance (MRR by Method)",
        "",
    ])


    # Collect all intents across results
    all_intents = sorted(list(next(iter(results.values())).stratified_metrics.keys()))
    header = "| Query Intent | " + " | ".join(f"**{name}**" for name in results) + " |"
    sep = "|---|" + "|".join(":---:" for _ in results) + "|"
    lines.append(header)
    lines.append(sep)

    for intent in all_intents:
        row = [f"`{intent}`"]
        for name, res in results.items():
            intent_m = res.stratified_metrics.get(intent)
            if intent_m:
                row.append(f"{intent_m.mrr:.4f} (R@5: {intent_m.recall_at_5:.2f})")
            else:
                row.append("N/A")
        lines.append("| " + " | ".join(row) + " |")

    lines.extend([
        "",
        "## 3. Methodological Progression Notes",
        "- **BM25 Baseline:** Robertson-Sparck Jones BM25 lexical matching over enriched observation tokens.",
        "- **Dense Semantic:** Local SentenceTransformer (`all-MiniLM-L6-v2`) cosine similarity.",
        "- **Weighted Hybrid:** Convex linear combination (50% lexical + 50% dense semantic).",
        "- **RRF (Reciprocal Rank Fusion):** Rank-based fusion: `RRF(d) = 1/(k + rank_bm25) + 1/(k + rank_dense)` with k=60.",
        "- **Weighted Hybrid + Temporal:** Linear hybrid + ClinicalQuery temporal reranking and hard date gating.",
        "- **RRF + Temporal:** RRF score fused with ClinicalQuery temporal reranking and hard date gating.",
        "- **Hybrid + Temporal + Concept:** Comprehensive pipeline integrating concept matching with temporal and hybrid signals (CP-06).",
        "- **Hybrid + Temporal + Concept + Trajectory:** Trajectory-aware post-retrieval re-ranking prioritizing baseline anchors, inflection points, and endpoint states for longitudinal/trend queries while strictly preserving hard temporal bounds (CP-07).",
        "",

        "## 4. Reproducibility & Research Invariants",
        "- 100% Patient-Scoped: Zero cross-patient candidate evaluation.",
        "- Deterministic Tie-Breaking: Strict score -> timestamp -> evidence_id ordering.",
        "- No Test-Set Tuning: Locked parameter weights across evaluation sets.",
        f"- Gold Label Boundary: Mode {'A (Oracle)' if mode == 'oracle' else 'B (End-to-End, Zero Gold Leakage)'}.",
        "",
    ])

    report_text = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    return report_text


def run_benchmark_suite(
    splits: list[Literal["dev", "val", "test"]] = ["val", "test"],
    modes: list[str] = ["oracle", "end_to_end"],
    output_dir: Path = Path("validation/retrieval"),
) -> dict[str, dict[str, dict[str, EvaluationRunResult]]]:
    """
    Executes the full benchmark evaluation suite across specified splits and modes.
    Returns: {mode: {split: {method_name: EvaluationRunResult}}}
    """
    from packages.research_data.evaluation.harness import EvaluationMode

    harness = ResearchEvaluationHarness()
    records = harness.load_records()

    # Pre-index dense embeddings once
    dense_retriever = EvidenceDenseRetriever()
    dense_retriever.index_evidence(records)

    retrievers = build_experiment_retrievers(dense_retriever)
    all_results: dict[str, dict[str, dict[str, EvaluationRunResult]]] = {}

    for mode_str in modes:
        eval_mode = EvaluationMode.ORACLE if mode_str == "oracle" else EvaluationMode.END_TO_END
        logger.info("==================================================")
        logger.info("=== Running Benchmark in Mode: %s ===", eval_mode.value.upper())
        logger.info("==================================================")
        mode_results: dict[str, dict[str, EvaluationRunResult]] = {}

        for split in splits:
            logger.info("--- Evaluating Split: %s [%s] ---", split.upper(), eval_mode.value)
            split_results: dict[str, EvaluationRunResult] = {}
            for method_name, retriever in retrievers.items():
                run_res = harness.evaluate_retriever(
                    retriever=retriever,
                    method_name=method_name,
                    split=split,
                    mode=eval_mode,
                    top_k=10,
                )
                harness.save_run(run_res, output_dir=output_dir)
                split_results[method_name] = run_res

            # Write markdown summary for this split and mode
            summary_path = output_dir / "summaries" / f"retrieval_benchmark_{split}_{mode_str}.md"
            generate_markdown_summary(split, split_results, summary_path, mode=mode_str)
            mode_results[split] = split_results

        all_results[mode_str] = mode_results

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MediVault CP-06 Evidence Retrieval Benchmark")
    parser.add_argument("--splits", nargs="+", default=["dev", "val", "test"], choices=["dev", "val", "test"])
    parser.add_argument("--mode", default="both", choices=["oracle", "end_to_end", "both"], help="Evaluation mode")
    args = parser.parse_args()

    mode_list = ["oracle", "end_to_end"] if args.mode == "both" else [args.mode]
    results = run_benchmark_suite(splits=args.splits, modes=mode_list)
    print("\nBenchmark Suite Execution Complete.")
