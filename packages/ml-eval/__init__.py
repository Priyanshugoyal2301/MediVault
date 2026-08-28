"""
ml-eval — reusable evaluation framework for MediVault ML components.

Every model evaluation reports:
  Precision, Recall, F1, Accuracy, Latency, Model Size, Memory Usage, Inference Time

Usage:

    from packages.ml_eval import classify_metrics, timed, resource_snapshot, EvaluationReport

    y_true, y_pred = [...], [...]
    m = classify_metrics(y_true, y_pred)
    result, ms = timed(lambda: model.predict(x))
    report = EvaluationReport(
        model_name="anomaly-statistical",
        metrics={**m, "latency_ms_mean": ms, ...},
    )
    report.write_json("datasets/evaluation/anomaly_latest.json")
"""

from .metrics import (
    accuracy,
    classify_metrics,
    f1_score,
    precision_recall_f1,
    ranking_metrics,
)
from .report import EvaluationReport
from .resource import measure_model_size_bytes, resource_snapshot
from .runner import EvaluationRunner, timed

__all__ = [
    "EvaluationReport",
    "EvaluationRunner",
    "accuracy",
    "classify_metrics",
    "f1_score",
    "measure_model_size_bytes",
    "precision_recall_f1",
    "ranking_metrics",
    "resource_snapshot",
    "timed",
]
