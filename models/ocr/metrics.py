"""
Field-level evaluation metrics for Phase 1 OCR / IE bake-off.

Compares predicted lab fields against gold labels.
"""

from __future__ import annotations

import time
import tracemalloc
from typing import Any, Hashable, Iterable, Sequence


def field_precision_recall_f1(
    gold: set[str] | dict[str, float],
    pred: set[str] | dict[str, float],
    *,
    value_tolerance: float = 0.051,
) -> dict[str, float]:
    """
    Field-level metrics.
    If gold/pred are dicts of name→value, values must match within tolerance.
    If sets of names, name-only match.
    """
    if isinstance(gold, dict) and isinstance(pred, dict):
        g_names = set(gold)
        p_names = set(pred)
        tp = 0
        for name in g_names & p_names:
            if abs(float(gold[name]) - float(pred[name])) <= value_tolerance:
                tp += 1
        fp = len(p_names - g_names)
        # preds in intersection but wrong values count as FN for that field + FP
        wrong = 0
        for name in g_names & p_names:
            if abs(float(gold[name]) - float(pred[name])) > value_tolerance:
                wrong += 1
        fn = len(g_names - p_names) + wrong
        fp += wrong
    else:
        g_names = set(gold)  # type: ignore[arg-type]
        p_names = set(pred)  # type: ignore[arg-type]
        tp = len(g_names & p_names)
        fp = len(p_names - g_names)
        fn = len(g_names - p_names)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "field_precision": round(precision, 6),
        "field_recall": round(recall, 6),
        "field_f1": round(f1, 6),
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
    }


def exact_match_rate(
    gold_docs: Sequence[dict[str, float]],
    pred_docs: Sequence[dict[str, float]],
    *,
    value_tolerance: float = 0.051,
) -> float:
    """Document-level exact match: all gold fields present and correct; no extras."""
    if not gold_docs:
        return 0.0
    hits = 0
    for g, p in zip(gold_docs, pred_docs):
        if set(g) != set(p):
            continue
        if all(abs(float(g[k]) - float(p[k])) <= value_tolerance for k in g):
            hits += 1
    return hits / len(gold_docs)


def missing_field_rate(gold: dict[str, Any], pred: dict[str, Any]) -> float:
    if not gold:
        return 0.0
    missing = sum(1 for k in gold if k not in pred)
    return missing / len(gold)


def false_positive_rate(gold: dict[str, Any], pred: dict[str, Any]) -> float:
    if not pred:
        return 0.0
    fp = sum(1 for k in pred if k not in gold)
    return fp / len(pred)


def ocr_token_accuracy(reference: str, hypothesis: str) -> float:
    """Simple word-level accuracy proxy (1 - WER clipped)."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref:
        return 1.0 if not hyp else 0.0
    # Levenshtein on tokens
    d = _levenshtein(ref, hyp)
    wer = d / len(ref)
    return max(0.0, 1.0 - wer)


def table_row_accuracy(
    gold_rows: Sequence[tuple[str, float]],
    pred_rows: Sequence[tuple[str, float]],
    *,
    value_tolerance: float = 0.051,
) -> float:
    if not gold_rows:
        return 0.0
    pred_map = {n.lower(): v for n, v in pred_rows}
    hits = 0
    for name, val in gold_rows:
        pv = pred_map.get(name.lower())
        if pv is not None and abs(float(pv) - float(val)) <= value_tolerance:
            hits += 1
    return hits / len(gold_rows)


def measure_runtime(fn) -> tuple[Any, dict[str, float]]:
    """Run callable once; return result + resource metrics."""
    tracemalloc.start()
    t0 = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    cpu = 0.0
    try:
        import os
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        cpu = float(usage.ru_utime + usage.ru_stime)
    except Exception:  # noqa: BLE001
        cpu = 0.0

    gpu_mib = 0.0
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            gpu_mib = torch.cuda.max_memory_allocated() / (1024 * 1024)
    except Exception:  # noqa: BLE001
        gpu_mib = 0.0

    return result, {
        "latency_ms": round(elapsed_ms, 4),
        "avg_processing_time_ms": round(elapsed_ms, 4),
        "memory_mib": round(peak / (1024 * 1024), 4),
        "cpu_seconds": round(cpu, 4),
        "gpu_memory_mib": round(gpu_mib, 4),
    }


def _levenshtein(a: Sequence[Hashable], b: Sequence[Hashable]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def aggregate_ie_report(
    per_doc: list[dict[str, float]],
    runtime: dict[str, float] | None = None,
) -> dict[str, Any]:
    if not per_doc:
        base = {
            "field_precision": 0.0,
            "field_recall": 0.0,
            "field_f1": 0.0,
            "exact_match": 0.0,
            "missing_field_rate": 0.0,
            "false_positive_rate": 0.0,
            "ocr_accuracy": 0.0,
            "table_accuracy": 0.0,
        }
    else:
        keys = [
            "field_precision",
            "field_recall",
            "field_f1",
            "exact_match",
            "missing_field_rate",
            "false_positive_rate",
            "ocr_accuracy",
            "table_accuracy",
        ]
        base = {
            k: round(sum(d.get(k, 0.0) for d in per_doc) / len(per_doc), 6)
            for k in keys
        }
    if runtime:
        base.update(runtime)
    # Compatibility with packages.ml_eval required keys
    base.setdefault("precision", base.get("field_precision", 0.0))
    base.setdefault("recall", base.get("field_recall", 0.0))
    base.setdefault("f1", base.get("field_f1", 0.0))
    base.setdefault("accuracy", base.get("exact_match", 0.0))
    base.setdefault("latency_ms", base.get("latency_ms", 0.0))
    base.setdefault("model_size_bytes", 0)
    base.setdefault("memory_mib", base.get("memory_mib", 0.0))
    base.setdefault("inference_time_ms", base.get("avg_processing_time_ms", 0.0))
    return base
