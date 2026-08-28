"""
Classification and ranking metrics (stdlib only).

Binary and multi-class support via simple counters — no sklearn dependency so
this package can run inside lightweight CI / demo preflight environments.
"""

from __future__ import annotations

from collections import Counter
from typing import Hashable, Iterable, Sequence


def _as_list(y: Iterable[Hashable]) -> list[Hashable]:
    return list(y)


def accuracy(y_true: Sequence[Hashable], y_pred: Sequence[Hashable]) -> float:
    yt, yp = _as_list(y_true), _as_list(y_pred)
    if not yt:
        return 0.0
    if len(yt) != len(yp):
        raise ValueError("y_true and y_pred length mismatch")
    correct = sum(1 for a, b in zip(yt, yp) if a == b)
    return correct / len(yt)


def precision_recall_f1(
    y_true: Sequence[Hashable],
    y_pred: Sequence[Hashable],
    *,
    positive: Hashable = True,
) -> tuple[float, float, float]:
    """Binary precision / recall / F1 for a chosen positive label."""
    yt, yp = _as_list(y_true), _as_list(y_pred)
    if len(yt) != len(yp):
        raise ValueError("y_true and y_pred length mismatch")

    tp = fp = fn = 0
    for t, p in zip(yt, yp):
        if p == positive and t == positive:
            tp += 1
        elif p == positive and t != positive:
            fp += 1
        elif p != positive and t == positive:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def f1_score(
    y_true: Sequence[Hashable],
    y_pred: Sequence[Hashable],
    *,
    positive: Hashable = True,
) -> float:
    return precision_recall_f1(y_true, y_pred, positive=positive)[2]


def classify_metrics(
    y_true: Sequence[Hashable],
    y_pred: Sequence[Hashable],
    *,
    positive: Hashable = True,
) -> dict[str, float]:
    """
    Standard classification packet used by every MediVault model evaluate.py.

    Returns keys: precision, recall, f1, accuracy
    """
    p, r, f1 = precision_recall_f1(y_true, y_pred, positive=positive)
    return {
        "precision": round(p, 6),
        "recall": round(r, 6),
        "f1": round(f1, 6),
        "accuracy": round(accuracy(y_true, y_pred), 6),
    }


def macro_f1(y_true: Sequence[Hashable], y_pred: Sequence[Hashable]) -> float:
    """Unweighted mean of per-class F1 scores."""
    labels = sorted(set(_as_list(y_true)) | set(_as_list(y_pred)), key=str)
    if not labels:
        return 0.0
    scores = [
        precision_recall_f1(y_true, y_pred, positive=lab)[2] for lab in labels
    ]
    return sum(scores) / len(scores)


def ranking_metrics(
    relevance: Sequence[Sequence[int]],
    *,
    k: int = 5,
) -> dict[str, float]:
    """
    Retrieval metrics over a list of ranked binary-relevance lists (1 = relevant).

    Computes Hit@k and MRR (standard IR) — complementary to classify_metrics.
    """
    if not relevance:
        return {"hit_at_k": 0.0, "mrr": 0.0, "k": float(k)}

    hits = 0
    rr_sum = 0.0
    for ranked in relevance:
        top = list(ranked)[:k]
        hit = any(r > 0 for r in top)
        if hit:
            hits += 1
        for i, r in enumerate(ranked, start=1):
            if r > 0:
                rr_sum += 1.0 / i
                break
    n = len(relevance)
    return {
        "hit_at_k": round(hits / n, 6),
        "mrr": round(rr_sum / n, 6),
        "k": float(k),
    }


def confusion_counts(
    y_true: Sequence[Hashable],
    y_pred: Sequence[Hashable],
) -> Counter:
    return Counter((t, p) for t, p in zip(_as_list(y_true), _as_list(y_pred)))
