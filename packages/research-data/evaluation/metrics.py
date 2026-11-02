"""
packages/research-data/evaluation/metrics.py

Deterministic Information Retrieval metrics for CP-06 evaluation harness:
  - Mean Reciprocal Rank (MRR)
  - Recall@K (K=1, 3, 5, 10)
  - Precision@K (K=1, 3, 5, 10)
  - Normalized Discounted Cumulative Gain (nDCG@K)
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence


def reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: set[str]) -> float:
    """
    Computes reciprocal rank for a single query.
    1 / rank of first relevant item in retrieved list (1-indexed).
    Returns 0.0 if no relevant items are retrieved.
    """
    if not relevant_ids:
        return 0.0
    for idx, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / idx
    return 0.0


def recall_at_k(
    retrieved_ids: Sequence[str], relevant_ids: set[str], k: int
) -> float:
    """
    Fraction of relevant documents retrieved in top-k.
    """
    if not relevant_ids:
        return 1.0
    if k <= 0:
        return 0.0
    top_k_set = set(retrieved_ids[:k])
    hits = len(top_k_set & relevant_ids)
    return hits / len(relevant_ids)


def precision_at_k(
    retrieved_ids: Sequence[str], relevant_ids: set[str], k: int
) -> float:
    """
    Fraction of top-k retrieved documents that are relevant.
    """
    if k <= 0:
        return 0.0
    top_k_set = set(retrieved_ids[:k])
    hits = len(top_k_set & relevant_ids)
    return hits / k


def ndcg_at_k(
    retrieved_ids: Sequence[str], relevant_ids: set[str], k: int
) -> float:
    """
    Normalized Discounted Cumulative Gain at rank k with binary relevance.
    """
    if not relevant_ids or k <= 0:
        return 0.0

    # DCG
    dcg = 0.0
    for idx, doc_id in enumerate(retrieved_ids[:k], start=1):
        if doc_id in relevant_ids:
            dcg += 1.0 / math.log2(idx + 1)

    # IDCG (ideal ranking where all relevant items appear first)
    idcg = 0.0
    ideal_hits = min(k, len(relevant_ids))
    for idx in range(1, ideal_hits + 1):
        idcg += 1.0 / math.log2(idx + 1)

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


@dataclass
class EvaluationMetrics:
    """Aggregated evaluation metrics over a query set."""
    mrr: float = 0.0
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    query_count: int = 0

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)

    @classmethod
    def aggregate(cls, query_metric_list: list[dict[str, float]]) -> EvaluationMetrics:
        """Computes mean across a list of per-query metric dicts."""
        n = len(query_metric_list)
        if n == 0:
            return cls(query_count=0)

        keys = [
            "mrr",
            "recall_at_1",
            "recall_at_3",
            "recall_at_5",
            "recall_at_10",
            "precision_at_1",
            "precision_at_3",
            "precision_at_5",
            "precision_at_10",
            "ndcg_at_5",
            "ndcg_at_10",
        ]
        means = {k: sum(m.get(k, 0.0) for m in query_metric_list) / n for k in keys}
        return cls(
            mrr=round(means["mrr"], 4),
            recall_at_1=round(means["recall_at_1"], 4),
            recall_at_3=round(means["recall_at_3"], 4),
            recall_at_5=round(means["recall_at_5"], 4),
            recall_at_10=round(means["recall_at_10"], 4),
            precision_at_1=round(means["precision_at_1"], 4),
            precision_at_3=round(means["precision_at_3"], 4),
            precision_at_5=round(means["precision_at_5"], 4),
            precision_at_10=round(means["precision_at_10"], 4),
            ndcg_at_5=round(means["ndcg_at_5"], 4),
            ndcg_at_10=round(means["ndcg_at_10"], 4),
            query_count=n,
        )`n