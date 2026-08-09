"""
ai-service/anomaly/model.py

IsolationForest-based anomaly scorer for health metric time series.

Trains an IsolationForest on the supplied data points (or falls back to
the Z-score result if fewer than MIN_SAMPLES points are available).

PRIVACY: no patient identifiers are passed into this module; it receives
only a list of numeric values + dates.

DEPENDENCY: scikit-learn (already in requirements.txt as scikit-learn>=1.4)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np

_MIN_SAMPLES_FOR_MODEL = 5  # IsolationForest is unreliable below this

# IsolationForest hyperparameters — tuned for short health time-series.
# contamination=0.1 means we expect ~10% of readings to be anomalous.
_CONTAMINATION = 0.1
_N_ESTIMATORS = 100
_RANDOM_STATE = 42


@dataclass(frozen=True)
class ModelAnomalyResult:
    anomaly_score: float       # -1.0 (most anomalous) → +1.0 (most normal); sklearn convention inverted
    is_anomaly: bool           # True if sklearn predicts -1 (outlier)
    method: str                # "isolation_forest" | "zscore_fallback"
    data_points_used: int


def score_anomaly(
    data_points: list[tuple[date, float]],
    z_score: float | None = None,
) -> ModelAnomalyResult:
    """
    Score the most recent value for anomaly using IsolationForest when
    enough data is available, else fall back to the supplied Z-score.

    Args:
        data_points: Chronological (date, value) pairs, oldest first.
        z_score:     Pre-computed Z-score for the latest point (from zscore.py).
                     Used as fallback when n < MIN_SAMPLES_FOR_MODEL.

    Returns:
        ModelAnomalyResult with a normalised anomaly score in [-1, 1].
    """
    n = len(data_points)

    if n >= _MIN_SAMPLES_FOR_MODEL:
        return _isolation_forest_score(data_points)
    else:
        return _zscore_fallback(z_score, n)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _isolation_forest_score(
    data_points: list[tuple[date, float]],
) -> ModelAnomalyResult:
    """Fit IsolationForest on the value series and score the last point."""
    # Lazy import so the module is importable without sklearn during tests
    # that mock this function.
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is required for IsolationForest scoring. "
            "Install with: pip install scikit-learn"
        ) from exc

    values = np.array([v for _, v in data_points]).reshape(-1, 1)

    clf = IsolationForest(
        n_estimators=_N_ESTIMATORS,
        contamination=_CONTAMINATION,
        random_state=_RANDOM_STATE,
    )
    clf.fit(values)

    # score_samples returns negative anomaly score; more negative = more anomalous.
    # We normalise to [-1, +1]: +1 = very normal, -1 = very anomalous.
    raw_scores = clf.score_samples(values)
    # Normalise via min-max within the batch
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s > min_s:
        normalised = 2 * (raw_scores - min_s) / (max_s - min_s) - 1
    else:
        normalised = np.zeros_like(raw_scores)

    latest_score = float(normalised[-1])
    is_anomaly = bool(clf.predict(values[-1:].reshape(1, -1))[0] == -1)

    return ModelAnomalyResult(
        anomaly_score=round(latest_score, 4),
        is_anomaly=is_anomaly,
        method="isolation_forest",
        data_points_used=len(data_points),
    )


def _zscore_fallback(z_score: float | None, n: int) -> ModelAnomalyResult:
    """
    When insufficient data exists for IsolationForest, approximate an
    anomaly score from the Z-score magnitude.
    |z| < 1 → score ≈ +1 (normal), |z| > 3 → score ≈ -1 (anomalous).
    """
    if z_score is None:
        return ModelAnomalyResult(
            anomaly_score=0.0,
            is_anomaly=False,
            method="zscore_fallback",
            data_points_used=n,
        )
    # Map z-score magnitude to [-1, +1]: clamp |z| to [0, 3] then invert.
    magnitude = min(abs(z_score), 3.0)
    score = 1.0 - (2.0 * magnitude / 3.0)  # 0→+1, 3→-1
    is_anomaly = abs(z_score) >= 2.0

    return ModelAnomalyResult(
        anomaly_score=round(score, 4),
        is_anomaly=is_anomaly,
        method="zscore_fallback",
        data_points_used=n,
    )
