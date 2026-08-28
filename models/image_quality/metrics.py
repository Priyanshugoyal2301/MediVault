"""Metrics for multi-label image quality classification."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def accuracy_multilabel(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if y_true.size == 0:
        return 0.0
    return float(np.mean(np.all(y_true == y_pred, axis=1)))


def f1_binary(yt: Sequence[int], yp: Sequence[int]) -> float:
    yt = np.asarray(yt, dtype=int)
    yp = np.asarray(yp, dtype=int)
    tp = float(np.sum((yt == 1) & (yp == 1)))
    fp = float(np.sum((yt == 0) & (yp == 1)))
    fn = float(np.sum((yt == 1) & (yp == 0)))
    if tp + fp + fn == 0:
        return 1.0
    prec = tp / (tp + fp + 1e-9)
    rec = tp / (tp + fn + 1e-9)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def f1_macro(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ys = [f1_binary(y_true[:, j], y_pred[:, j]) for j in range(y_true.shape[1])]
    return float(np.mean(ys)) if ys else 0.0


def precision_macro(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    vals = []
    for j in range(y_true.shape[1]):
        yt, yp = y_true[:, j], y_pred[:, j]
        tp = np.sum((yt == 1) & (yp == 1))
        fp = np.sum((yt == 0) & (yp == 1))
        vals.append(float(tp / (tp + fp + 1e-9)))
    return float(np.mean(vals))


def recall_macro(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    vals = []
    for j in range(y_true.shape[1]):
        yt, yp = y_true[:, j], y_pred[:, j]
        tp = np.sum((yt == 1) & (yp == 1))
        fn = np.sum((yt == 1) & (yp == 0))
        vals.append(float(tp / (tp + fn + 1e-9)))
    return float(np.mean(vals))


def roc_auc_binary(y_true: Sequence[int], scores: Sequence[float]) -> float | None:
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    if len(np.unique(y)) < 2:
        return None
    order = np.argsort(-s)
    y = y[order]
    P = int(y.sum())
    N = len(y) - P
    tps = np.cumsum(y)
    fps = np.cumsum(1 - y)
    tpr = tps / max(P, 1)
    fpr = fps / max(N, 1)
    return float(np.trapezoid(tpr, fpr) if hasattr(np, "trapezoid") else np.trapz(tpr, fpr))


def confusion_ready(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, int]:
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)
    return {
        "tp": int(np.sum((yt == 1) & (yp == 1))),
        "tn": int(np.sum((yt == 0) & (yp == 0))),
        "fp": int(np.sum((yt == 0) & (yp == 1))),
        "fn": int(np.sum((yt == 1) & (yp == 0))),
    }
