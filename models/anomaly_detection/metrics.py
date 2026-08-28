"""Evaluation metrics for unsupervised anomaly detection."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def precision_at_k(y_true: Sequence[int], scores: Sequence[float], k: int = 20) -> float:
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    if len(y) == 0 or k <= 0:
        return 0.0
    k = min(k, len(y))
    idx = np.argsort(-s)[:k]
    return float(np.mean(y[idx]))


def recall_at_k(y_true: Sequence[int], scores: Sequence[float], k: int = 20) -> float:
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    pos = int(y.sum())
    if pos == 0 or k <= 0:
        return 0.0
    k = min(k, len(y))
    idx = np.argsort(-s)[:k]
    return float(y[idx].sum() / pos)


def roc_auc(y_true: Sequence[int], scores: Sequence[float]) -> float | None:
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    if len(np.unique(y)) < 2:
        return None
    order = np.argsort(-s)
    y = y[order]
    P = y.sum()
    N = len(y) - P
    if P == 0 or N == 0:
        return None
    tps = np.cumsum(y)
    fps = np.cumsum(1 - y)
    tpr = tps / P
    fpr = fps / N
    # trapz
    return float(np.trapz(tpr, fpr))


def pr_auc(y_true: Sequence[int], scores: Sequence[float]) -> float | None:
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    if len(np.unique(y)) < 2 or y.sum() == 0:
        return None
    order = np.argsort(-s)
    y = y[order]
    tps = np.cumsum(y)
    fps = np.cumsum(1 - y)
    prec = tps / np.maximum(tps + fps, 1)
    rec = tps / y.sum()
    return float(np.trapz(prec, rec))


def false_positive_rate(
    y_true: Sequence[int], scores: Sequence[float], thr: float
) -> float:
    y = np.asarray(y_true, dtype=int)
    pred = (np.asarray(scores, dtype=float) >= thr).astype(int)
    neg = y == 0
    if not np.any(neg):
        return 0.0
    return float(np.mean(pred[neg] == 1))
