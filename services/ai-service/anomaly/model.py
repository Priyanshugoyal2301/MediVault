"""
ai-service/anomaly/model.py

Statistical personal-series monitor for short lab time series.

Replaces IsolationForest (unfit for n≈5–10, 1-D, contamination-forced outliers)
with a causal hybrid of:

  1. Leave-last-out Z-score (baseline from past only)
  2. Consecutive relative change (%Δ vs previous reading)
  3. Two-sided CUSUM on residuals from the personal baseline

Score convention (API-stable): [-1, +1] where +1 = normal, -1 = anomalous.

PRIVACY: only (date, value) pairs — no patient identifiers.
DEPENDENCY: stdlib + math only (no sklearn).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

# Causal z-score threshold (≈95% under normality assumption for past baseline)
_Z_THRESHOLD = 2.0
# Relative jump vs previous point (scale-free); 25% is conservative for Hb/LDL
_PCT_DELTA_THRESHOLD = 0.25
# CUSUM allowance / decision interval in units of baseline σ (classic QC defaults)
_CUSUM_K = 0.5
_CUSUM_H = 4.0
# Need ≥2 past points for a useful baseline variance estimate
_MIN_BASELINE = 2


@dataclass(frozen=True)
class ModelAnomalyResult:
    anomaly_score: float  # -1.0 (most anomalous) → +1.0 (most normal)
    is_anomaly: bool
    method: str  # "statistical_monitor" | "zscore_fallback"
    data_points_used: int
    # Explainability extras (ignored by older callers)
    causal_z: float | None = None
    pct_delta: float | None = None
    cusum_alarm: bool = False
    triggers: tuple[str, ...] = ()


def score_anomaly(
    data_points: list[tuple[date, float]],
    z_score: float | None = None,
) -> ModelAnomalyResult:
    """
    Score the most recent value for unusual change vs the user's past readings.

    Args:
        data_points: Chronological (date, value) pairs, oldest first.
        z_score: Pre-computed whole-series z (from zscore.py). Used only when
                 there are too few points for a causal baseline (< 3 total).
    """
    n = len(data_points)
    if n < 3:
        return _zscore_fallback(z_score, n)
    return _statistical_monitor(data_points)


def _statistical_monitor(
    data_points: list[tuple[date, float]],
) -> ModelAnomalyResult:
    values = [float(v) for _, v in data_points]
    n = len(values)
    past = values[:-1]
    latest = values[-1]
    prev = values[-2]

    mu = sum(past) / len(past)
    var = sum((v - mu) ** 2 for v in past) / len(past)
    sigma = math.sqrt(var)

    # Causal z: leave-last-out. If past is flat, treat large absolute jump via %Δ.
    if sigma > 1e-12:
        causal_z = (latest - mu) / sigma
    else:
        causal_z = 0.0

    denom = max(abs(prev), 1e-6)
    pct_delta = (latest - prev) / denom

    cusum_alarm, cusum_magnitude = _cusum_alarm(past, latest, mu, sigma)

    # Feature flags (explainability). Binary decision is narrower than the
    # feature set: ablation on synthetic Hb spikes showed OR-ing %Δ into
    # is_anomaly raised FAR without lifting recall (already ~1.0 from causal z).
    feature_triggers: list[str] = []
    if abs(causal_z) >= _Z_THRESHOLD:
        feature_triggers.append("causal_z")
    if abs(pct_delta) >= _PCT_DELTA_THRESHOLD:
        feature_triggers.append("pct_delta")
    if cusum_alarm:
        feature_triggers.append("cusum")

    # Decision: causal z (primary) OR CUSUM (slow-shift detector; 0 FAR on synth).
    # %Δ informs score + bilingual summary only.
    is_anomaly = ("causal_z" in feature_triggers) or ("cusum" in feature_triggers)

    # Continuous score in [-1, +1]: dominate by strongest signal.
    z_mag = min(abs(causal_z) / 3.0, 1.0)
    d_mag = min(abs(pct_delta) / (_PCT_DELTA_THRESHOLD * 2.0), 1.0)
    c_mag = min(cusum_magnitude / _CUSUM_H, 1.0) if sigma > 1e-12 else 0.0
    strength = max(z_mag, d_mag, c_mag)
    score = 1.0 - 2.0 * strength  # 0→+1, 1→-1

    return ModelAnomalyResult(
        anomaly_score=round(score, 4),
        is_anomaly=is_anomaly,
        method="statistical_monitor",
        data_points_used=n,
        causal_z=round(causal_z, 4),
        pct_delta=round(pct_delta, 4),
        cusum_alarm=cusum_alarm,
        triggers=tuple(feature_triggers),
    )


def _cusum_alarm(
    past: list[float],
    latest: float,
    mu: float,
    sigma: float,
) -> tuple[bool, float]:
    """
    Two-sided tabular CUSUM on residuals vs personal baseline mean.

    Uses past points to warm the statistic, then applies the latest reading.
    Returns (alarm, max(|S+|, |S-|)/σ normalised decision distance).
    """
    if sigma <= 1e-12 or len(past) < _MIN_BASELINE:
        return False, 0.0

    k = _CUSUM_K * sigma
    h = _CUSUM_H * sigma
    s_pos = 0.0
    s_neg = 0.0
    series = past + [latest]
    for x in series:
        residual = x - mu
        s_pos = max(0.0, s_pos + residual - k)
        s_neg = max(0.0, s_neg - residual - k)

    mag = max(s_pos, s_neg) / sigma
    return (s_pos > h or s_neg > h), mag


def _zscore_fallback(z_score: float | None, n: int) -> ModelAnomalyResult:
    """Insufficient history: map whole-series |z| to score (API-compatible)."""
    if z_score is None:
        return ModelAnomalyResult(
            anomaly_score=0.0,
            is_anomaly=False,
            method="zscore_fallback",
            data_points_used=n,
        )
    magnitude = min(abs(z_score), 3.0)
    score = 1.0 - (2.0 * magnitude / 3.0)
    is_anomaly = abs(z_score) >= _Z_THRESHOLD
    triggers = ("zscore_fallback",) if is_anomaly else ()
    return ModelAnomalyResult(
        anomaly_score=round(score, 4),
        is_anomaly=is_anomaly,
        method="zscore_fallback",
        data_points_used=n,
        causal_z=round(z_score, 4),
        triggers=triggers,
    )
