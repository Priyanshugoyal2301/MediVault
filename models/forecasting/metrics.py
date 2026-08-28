"""Forecast quality metrics."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if len(y) == 0:
        return 0.0
    return float(np.mean(np.abs(y - p)))


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if len(y) == 0:
        return 0.0
    return float(np.sqrt(np.mean((y - p) ** 2)))


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


def interval_coverage(
    y_true: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> float:
    y = np.asarray(y_true, dtype=float)
    lo = np.asarray(lower, dtype=float)
    hi = np.asarray(upper, dtype=float)
    if len(y) == 0:
        return 0.0
    return float(np.mean((y >= lo) & (y <= hi)))


def residual_calibration_error(
    y_true: Sequence[float], y_pred: Sequence[float], n_bins: int = 5
) -> float:
    """Mean absolute residual bias across predicted-value bins (simple)."""
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


def trend_accuracy(
    true_dir: Sequence[str], pred_dir: Sequence[str]
) -> float:
    if not true_dir:
        return 0.0
    ok = sum(1 for a, b in zip(true_dir, pred_dir) if a == b)
    return ok / len(true_dir)
