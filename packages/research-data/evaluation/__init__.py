"""
packages/research-data/evaluation/__init__.py

Research evaluation harness and metrics for longitudinal evidence retrieval (CP-06).
"""

from .failure_analyzer import RetrievalFailureRecord, diagnose_query_failure
from .harness import (
    BENCHMARK_INTENT_MAP,
    EvaluationRunResult,
    ResearchEvaluationHarness,
)
from .metrics import (
    EvaluationMetrics,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

__all__ = [
    "BENCHMARK_INTENT_MAP",
    "EvaluationMetrics",
    "EvaluationRunResult",
    "ResearchEvaluationHarness",
    "RetrievalFailureRecord",
    "diagnose_query_failure",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
]
