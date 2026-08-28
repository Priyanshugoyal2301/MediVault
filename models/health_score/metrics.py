"""Health score metrics."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y - p))) if len(y) else 0.0


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y - p) ** 2))) if len(y) else 0.0


def mape(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    mask = np.abs(y) > 1e-6
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y[mask] - p[mask]) / y[mask])) * 100.0)


def r2_score(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if len(y) < 2:
        return 0.0
    ss_res = np.sum((y - p) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    if ss_tot < 1e-12:
        return 0.0
    return float(1.0 - ss_res / ss_tot)


def residual_calibration_error(
    y_true: Sequence[float], y_pred: Sequence[float], n_bins: int = 5
) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if len(y) == 0:
        return 0.0
    order = np.argsort(p)
    y, p = y[order], p[order]
    bins = np.array_split(np.arange(len(y)), n_bins)
    errs = []
    for idx in bins:
        if len(idx) == 0:
            continue
        errs.append(abs(float(np.mean(y[idx] - p[idx]))))
    return float(np.mean(errs)) if errs else 0.0


def feature_stability(
    importances_a: Sequence[float], importances_b: Sequence[float]
) -> float:
    """Spearman-like rank correlation of two importance vectors (0–1)."""
    a = np.asarray(importances_a, dtype=float)
    b = np.asarray(importances_b, dtype=float)
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    ra = a.argsort().argsort().astype(float)
    rb = b.argsort().argsort().astype(float)
    if np.std(ra) < 1e-9 or np.std(rb) < 1e-9:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])
