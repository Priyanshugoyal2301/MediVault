"""Metrics for disease risk evaluation."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np


def binary_metrics(y_true: Sequence[int], y_prob: Sequence[float], threshold: float = 0.5) -> dict[str, float]:
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(y_prob, dtype=float)
    pred = (p >= threshold).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    sens = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = sens
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / max(1, len(y))
    return {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "sensitivity": sens,
        "specificity": spec,
        "f1": f1,
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
    }


def roc_auc(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(y_prob, dtype=float)
    if len(np.unique(y)) < 2:
        return 0.5
    # Mann-Whitney form
    order = np.argsort(p)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(p) + 1)
    n_pos = float((y == 1).sum())
    n_neg = float((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    sum_ranks_pos = ranks[y == 1].sum()
    return float((sum_ranks_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def pr_auc(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(y_prob, dtype=float)
    if len(np.unique(y)) < 2:
        return float(y.mean()) if len(y) else 0.0
    order = np.argsort(-p)
    y_sorted = y[order]
    tp = 0
    fp = 0
    n_pos = max(1, int((y == 1).sum()))
    precs = []
    recs = []
    for label in y_sorted:
        if label == 1:
            tp += 1
        else:
            fp += 1
        precs.append(tp / (tp + fp))
        recs.append(tp / n_pos)
    # trapz
    area = 0.0
    for i in range(1, len(recs)):
        area += (recs[i] - recs[i - 1]) * (precs[i] + precs[i - 1]) / 2
    return float(max(0.0, area))


def expected_calibration_error(
    y_true: Sequence[int], y_prob: Sequence[float], n_bins: int = 10
) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_prob, dtype=float)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = max(1, len(y))
    for i in range(n_bins):
        m = (p >= bins[i]) & (p < bins[i + 1] if i < n_bins - 1 else p <= bins[i + 1])
        if not np.any(m):
            continue
        conf = p[m].mean()
        acc = y[m].mean()
        ece += (m.sum() / n) * abs(acc - conf)
    return float(ece)


def confusion_matrix_dict(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, int]:
    y = np.asarray(y_true, dtype=int)
    pred = np.asarray(y_pred, dtype=int)
    return {
        "tp": int(((pred == 1) & (y == 1)).sum()),
        "tn": int(((pred == 0) & (y == 0)).sum()),
        "fp": int(((pred == 1) & (y == 0)).sum()),
        "fn": int(((pred == 0) & (y == 1)).sum()),
    }


def roc_curve_points(
    y_true: Sequence[int], y_prob: Sequence[float], n: int = 20
) -> list[dict[str, float]]:
    thresholds = np.linspace(0, 1, n)
    points = []
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(y_prob, dtype=float)
    for t in thresholds:
        pred = (p >= t).astype(int)
        tp = ((pred == 1) & (y == 1)).sum()
        fp = ((pred == 1) & (y == 0)).sum()
        tn = ((pred == 0) & (y == 0)).sum()
        fn = ((pred == 0) & (y == 1)).sum()
        tpr = tp / (tp + fn) if (tp + fn) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        points.append({"threshold": float(t), "tpr": float(tpr), "fpr": float(fpr)})
    return points
