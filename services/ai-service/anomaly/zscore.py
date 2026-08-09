"""
ai-service/anomaly/zscore.py

Baseline Z-score trend detector for health metric time series.

Takes a list of (date, value) data points and computes:
  - Mean and standard deviation of the series
  - Z-score for the most recent value
  - Trend direction: rising / falling / stable
  - Out-of-range persistence: how many consecutive recent readings are abnormal

Requires >= 3 data points. Below that, returns INSUFFICIENT_DATA.

No diagnoses are made here. Output is plain statistical classification only;
plain-language messaging is handled by detector.py / explainer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from enum import Enum


class TrendDirection(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class ZScoreResult:
    trend: TrendDirection
    z_score: float | None          # None when insufficient data
    mean: float | None
    std_dev: float | None
    out_of_range_streak: int       # consecutive recent points with |z| > threshold
    data_points_used: int


_ZSCORE_ANOMALY_THRESHOLD = 2.0   # |z| > 2.0 flagged as out-of-range
_RISING_SLOPE_THRESHOLD = 0.25    # normalised slope to call a trend "rising/falling"
_MIN_DATA_POINTS = 3


def _linear_slope(values: list[float]) -> float:
    """
    Least-squares slope of (index, value) pairs, normalised by std_dev.
    Returns 0.0 when std_dev is 0 (flat series).
    """
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0

    slope = numerator / denominator
    std_dev = math.sqrt(sum((v - y_mean) ** 2 for v in values) / n)
    # Normalise slope by std_dev so the threshold is scale-independent
    return slope / std_dev if std_dev > 0 else 0.0


def _out_of_range_streak(z_scores: list[float], threshold: float) -> int:
    """Count consecutive trailing readings with |z| > threshold."""
    streak = 0
    for z in reversed(z_scores):
        if abs(z) > threshold:
            streak += 1
        else:
            break
    return streak


def compute_zscore(
    data_points: list[tuple[date, float]],
) -> ZScoreResult:
    """
    Analyse a chronologically-ordered list of (date, value) pairs.

    Args:
        data_points: List of (date, numeric_value) tuples, oldest first.

    Returns:
        ZScoreResult with trend, z-score for the latest value, and streak.
    """
    if len(data_points) < _MIN_DATA_POINTS:
        return ZScoreResult(
            trend=TrendDirection.INSUFFICIENT_DATA,
            z_score=None,
            mean=None,
            std_dev=None,
            out_of_range_streak=0,
            data_points_used=len(data_points),
        )

    values = [v for _, v in data_points]
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std_dev = math.sqrt(variance)

    # Z-score for every point
    if std_dev > 0:
        z_scores = [(v - mean) / std_dev for v in values]
    else:
        z_scores = [0.0] * n

    latest_z = z_scores[-1]
    streak = _out_of_range_streak(z_scores, _ZSCORE_ANOMALY_THRESHOLD)

    norm_slope = _linear_slope(values)
    if norm_slope > _RISING_SLOPE_THRESHOLD:
        trend = TrendDirection.RISING
    elif norm_slope < -_RISING_SLOPE_THRESHOLD:
        trend = TrendDirection.FALLING
    else:
        trend = TrendDirection.STABLE

    return ZScoreResult(
        trend=trend,
        z_score=round(latest_z, 3),
        mean=round(mean, 4),
        std_dev=round(std_dev, 4),
        out_of_range_streak=streak,
        data_points_used=n,
    )
