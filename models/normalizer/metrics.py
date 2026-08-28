"""Evaluation metrics for medical test normalization."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence


def top1_accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    if not y_true:
        return 0.0
    ok = sum(1 for t, p in zip(y_true, y_pred) if (t or "").lower() == (p or "").lower())
    return ok / len(y_true)


def topk_accuracy(
    y_true: Sequence[str],
    y_topk: Sequence[Sequence[str]],
    k: int = 3,
) -> float:
    if not y_true:
        return 0.0
    hits = 0
    for t, preds in zip(y_true, y_topk):
        cands = [(p or "").lower() for p in list(preds)[:k]]
        if (t or "").lower() in cands:
            hits += 1
    return hits / len(y_true)


def precision_recall_f1(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    known_only: bool = False,
    unknown_label: str = "__UNKNOWN__",
) -> dict[str, float]:
    """
    Micro-style exact-match over known classes.
    When known_only, skip pairs where gold is unknown_label.
    """
    pairs = list(zip(y_true, y_pred))
    if known_only:
        pairs = [(t, p) for t, p in pairs if (t or "") != unknown_label]
    if not pairs:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}

    # Treat each unique gold canon as a class; micro F1 = accuracy for multi-class exact match
    tp = sum(1 for t, p in pairs if (t or "").lower() == (p or "").lower())
    acc = tp / len(pairs)
    return {"precision": acc, "recall": acc, "f1": acc, "support": len(pairs)}


def unknown_term_accuracy(
    gold_unknown: Sequence[bool],
    pred_unknown: Sequence[bool],
) -> float:
    if not gold_unknown:
        return 0.0
    ok = sum(1 for g, p in zip(gold_unknown, pred_unknown) if bool(g) == bool(p))
    return ok / len(gold_unknown)


def loinc_accuracy(
    gold_loinc: Sequence[str | None],
    pred_loinc: Sequence[str | None],
) -> float:
    pairs = [(g, p) for g, p in zip(gold_loinc, pred_loinc) if g]
    if not pairs:
        return 0.0
    ok = sum(1 for g, p in pairs if (g or "").strip() == (p or "").strip())
    return ok / len(pairs)


def confusion_matrix(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    top_n: int = 15,
) -> dict[str, Any]:
    """Compact confusion as list of ((true, pred), count) sorted by count."""
    c = Counter((t, p) for t, p in zip(y_true, y_pred) if (t or "").lower() != (p or "").lower())
    most = c.most_common(top_n)
    return {
        "errors": [{"true": a, "pred": b, "count": n} for (a, b), n in most],
        "total_mismatches": sum(c.values()),
    }


def summarize_latency(latencies_ms: Sequence[float]) -> dict[str, float]:
    if not latencies_ms:
        return {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    xs = sorted(float(x) for x in latencies_ms)
    n = len(xs)

    def pct(p: float) -> float:
        idx = min(n - 1, max(0, int(round(p * (n - 1)))))
        return xs[idx]

    return {
        "mean_ms": sum(xs) / n,
        "p50_ms": pct(0.50),
        "p95_ms": pct(0.95),
        "max_ms": xs[-1],
    }
