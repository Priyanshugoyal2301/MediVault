"""Feature engineering helpers (selection, correlation, scaling stats)."""

from __future__ import annotations

from typing import Any

import numpy as np

from .diseases import FEATURE_COLUMNS


def correlation_matrix(X: np.ndarray, columns: list[str] | None = None) -> dict[str, Any]:
    cols = columns or FEATURE_COLUMNS
    if X.size == 0 or X.shape[0] < 2:
        return {"columns": cols, "matrix": []}
    c = np.corrcoef(X, rowvar=False)
    # replace nan
    c = np.nan_to_num(c, nan=0.0)
    return {
        "columns": cols,
        "matrix": c.round(3).tolist(),
    }


def feature_importance_from_coef(
    coef: np.ndarray,
    columns: list[str] | None = None,
    top_k: int = 5,
) -> list[tuple[str, float]]:
    cols = columns or FEATURE_COLUMNS
    coef = np.asarray(coef).ravel()
    if coef.size != len(cols):
        # multi-class or truncated — zip min
        n = min(len(cols), coef.size)
        cols, coef = cols[:n], coef[:n]
    pairs = sorted(
        zip(cols, np.abs(coef).astype(float)),
        key=lambda x: x[1],
        reverse=True,
    )
    return [(n, float(v)) for n, v in pairs[:top_k]]


def select_non_constant_features(
    X: np.ndarray, columns: list[str] | None = None
) -> list[int]:
    cols = columns or FEATURE_COLUMNS
    keep = []
    for i, _c in enumerate(cols):
        if i >= X.shape[1]:
            break
        if np.nanstd(X[:, i]) > 1e-9:
            keep.append(i)
    return keep or list(range(min(X.shape[1], len(cols))))
