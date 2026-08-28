"""High-level evaluation runner that standardises metric packing."""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, Hashable, Sequence

from .metrics import classify_metrics, ranking_metrics
from .report import EvaluationReport
from .resource import measure_model_size_bytes, timed


class EvaluationRunner:
    """
    Reusable harness: run an inference callable over a dataset function,
    collect classification metrics + runtime/resource metrics, emit report.
    """

    def __init__(
        self,
        *,
        model_name: str,
        model_version: str = "baseline",
        dataset: str = "unknown",
        model_path: str | Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.model_version = model_version
        self.dataset = dataset
        self.model_path = model_path

    def run_classification(
        self,
        *,
        y_true: Sequence[Hashable],
        predict_all: Callable[[], Sequence[Hashable]],
        positive: Hashable = True,
        latency_repeats: int = 1,
        notes: str = "",
        extras: dict[str, Any] | None = None,
    ) -> EvaluationReport:
        """
        `predict_all` must return predictions aligned with `y_true`.
        Timing + peak memory are measured around full-dataset prediction calls.
        """
        preds, mean_ms, peak_mib = self._timed_predict(predict_all, latency_repeats)
        cls = classify_metrics(y_true, preds, positive=positive)
        n = max(len(preds), 1)
        metrics = {
            **cls,
            "latency_ms": round(mean_ms, 4),
            "inference_time_ms": round(mean_ms / n, 6),
            "model_size_bytes": measure_model_size_bytes(self.model_path),
            "memory_mib": round(peak_mib, 4),
        }
        return EvaluationReport(
            model_name=self.model_name,
            model_version=self.model_version,
            dataset=self.dataset,
            metrics=metrics,
            extras=extras or {},
            notes=notes,
        )

    def run_retrieval(
        self,
        *,
        relevance_lists: Sequence[Sequence[int]],
        k: int = 5,
        retrieve_once: Callable[[], Any] | None = None,
        latency_repeats: int = 1,
        notes: str = "",
        extras: dict[str, Any] | None = None,
    ) -> EvaluationReport:
        rank = ranking_metrics(relevance_lists, k=k)
        mean_ms = 0.0
        peak_mib = 0.0
        if retrieve_once is not None:
            _, mean_ms, peak_mib = self._timed_predict(
                lambda: list(retrieve_once() or []),
                latency_repeats,
            )

        n = max(len(relevance_lists), 1)
        h = float(rank.get("hit_at_k", 0.0))
        m = float(rank.get("mrr", 0.0))
        f1 = (2 * h * m / (h + m)) if (h + m) else 0.0
        metrics = {
            "precision": h,
            "recall": m,
            "f1": round(f1, 6),
            "accuracy": h,
            "latency_ms": round(mean_ms, 4),
            "inference_time_ms": round(mean_ms / n, 6),
            "model_size_bytes": measure_model_size_bytes(self.model_path),
            "memory_mib": round(peak_mib, 4),
            "hit_at_k": h,
            "mrr": m,
        }
        return EvaluationReport(
            model_name=self.model_name,
            model_version=self.model_version,
            dataset=self.dataset,
            metrics=metrics,
            extras=extras or {},
            notes=notes,
        )

    @staticmethod
    def _timed_predict(
        fn: Callable[[], Sequence[Hashable]],
        repeats: int,
    ) -> tuple[list[Hashable], float, float]:
        if repeats < 1:
            raise ValueError("latency_repeats must be >= 1")
        times: list[float] = []
        last_preds: list[Hashable] = []
        peak_mib = 0.0
        for _ in range(repeats):
            tracemalloc.start()
            t0 = time.perf_counter()
            last_preds = list(fn())
            elapsed = (time.perf_counter() - t0) * 1000.0
            _cur, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            times.append(elapsed)
            peak_mib = max(peak_mib, peak / (1024 * 1024))
        return last_preds, sum(times) / len(times), peak_mib


__all__ = ["EvaluationRunner", "timed"]
