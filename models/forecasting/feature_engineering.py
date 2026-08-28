"""Temporal feature engineering for irregular lab series."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np

from .biomarkers import POINT_FEATURE_NAMES, alias_to_id


def _parse_date(raw: Any, fallback: date | None = None) -> date:
    if raw is None:
        return fallback or date(2020, 1, 1)
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    s = str(raw).strip()[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        return fallback or date(2020, 1, 1)


def history_to_series(
    history: list[dict[str, Any]] | None,
) -> dict[str, list[tuple[date, float]]]:
    """Group metrics into biomarker_id -> sorted (date, value) series."""
    buckets: dict[str, list[tuple[date, float]]] = {}
    base = date(2020, 1, 1)
    for i, m in enumerate(history or []):
        bid = alias_to_id(str(m.get("test_name") or ""))
        if not bid:
            continue
        try:
            val = float(m.get("value_numeric"))
        except (TypeError, ValueError):
            continue
        d = _parse_date(m.get("date_of_test") or m.get("date"), base + timedelta(days=i * 30))
        buckets.setdefault(bid, []).append((d, val))
    for bid in buckets:
        buckets[bid].sort(key=lambda x: x[0])
    return buckets


def _slope(series: list[tuple[date, float]]) -> float:
    if len(series) < 2:
        return 0.0
    t0 = series[0][0]
    xs = np.array([(s[0] - t0).days for s in series], dtype=float)
    ys = np.array([s[1] for s in series], dtype=float)
    if np.std(xs) < 1e-9:
        return 0.0
    return float(np.polyfit(xs, ys, 1)[0])


def build_point_features(
    series: list[tuple[date, float]],
    *,
    horizon_days: int,
    age: float | None,
    sex_female: float,
    as_of: date | None = None,
) -> dict[str, float]:
    """Feature vector for forecasting after last observation."""
    if not series:
        return {k: 0.0 for k in POINT_FEATURE_NAMES}

    as_of = as_of or series[-1][0]
    vals = [v for _, v in series]
    n = len(vals)
    lag1 = vals[-1]
    lag2 = vals[-2] if n >= 2 else lag1
    lag3 = vals[-3] if n >= 3 else lag2
    last3 = vals[-3:] if n >= 3 else vals
    roll_mean_3 = float(np.mean(last3))
    roll_std_3 = float(np.std(last3)) if len(last3) > 1 else 0.0
    roll_mean_all = float(np.mean(vals))
    delta_last = lag1 - lag2
    span = max(1, (series[-1][0] - series[0][0]).days)
    days_since = max(0, (as_of - series[-1][0]).days)
    slope = _slope(series)

    return {
        "value": float(lag1),
        "age": float(age) if age is not None else 45.0,
        "sex_female": float(sex_female),
        "horizon_days": float(horizon_days),
        "n_obs": float(n),
        "days_span": float(span),
        "days_since_last": float(days_since),
        "lag1": float(lag1),
        "lag2": float(lag2),
        "lag3": float(lag3),
        "roll_mean_3": roll_mean_3,
        "roll_std_3": roll_std_3,
        "roll_mean_all": roll_mean_all,
        "delta_last": float(delta_last),
        "slope_per_day": float(slope),
        "missing_frac": 0.0,
    }


def feature_vector(fdict: dict[str, float]) -> np.ndarray:
    return np.asarray([float(fdict.get(k, 0.0)) for k in POINT_FEATURE_NAMES], dtype=np.float64)


def trend_from_values(current: float | None, predicted: float | None, eps: float = 0.02) -> tuple[str, str]:
    if current is None or predicted is None:
        return "unknown", "Insufficient history to determine a clear trend."
    delta = predicted - current
    rel = abs(delta) / max(abs(current), 1e-6)
    if rel < eps and abs(delta) < max(0.05 * max(abs(current), 1.0), 0.05):
        return "stable", "Predicted value is similar to the current reading over the horizon."
    if delta > 0:
        return "increasing", "Predicted value is higher than the current reading (statistical forecast)."
    return "decreasing", "Predicted value is lower than the current reading (statistical forecast)."
