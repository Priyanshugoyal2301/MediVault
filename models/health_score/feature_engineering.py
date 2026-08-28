"""Feature engineering for personalized health score."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np

from .schema import FEATURE_COLUMNS, TEST_ALIASES


def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().replace("_", " ").split())


def alias_to_feature(test_name: str) -> str | None:
    key = _norm(test_name)
    for feat, aliases in TEST_ALIASES.items():
        if key == feat or key in aliases:
            return feat
        for a in aliases:
            if a == key or a in key or key in a:
                return feat
    return None


def _parse_date(raw: Any, idx: int = 0) -> date:
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    try:
        return date.fromisoformat(str(raw)[:10])
    except Exception:
        return date(2020, 1, 1) + __import__("datetime").timedelta(days=idx * 30)


def _slope(series: list[tuple[date, float]]) -> float:
    if len(series) < 2:
        return 0.0
    t0 = series[0][0]
    xs = np.array([(d - t0).days for d, _ in series], dtype=float)
    ys = np.array([v for _, v in series], dtype=float)
    if np.std(xs) < 1e-9:
        return 0.0
    return float(np.polyfit(xs, ys, 1)[0])


def extract_series(metrics: list[dict[str, Any]] | None) -> dict[str, list[tuple[date, float]]]:
    buckets: dict[str, list[tuple[date, float]]] = {}
    for i, m in enumerate(metrics or []):
        feat = alias_to_feature(str(m.get("test_name") or ""))
        if not feat:
            continue
        try:
            v = float(m["value_numeric"])
        except (KeyError, TypeError, ValueError):
            continue
        d = _parse_date(m.get("date_of_test") or m.get("date"), i)
        buckets.setdefault(feat, []).append((d, v))
    for k in buckets:
        buckets[k].sort(key=lambda x: x[0])
    return buckets


def risk_proxies_from_labs(labs: dict[str, float | None]) -> dict[str, float]:
    """Lightweight non-diagnostic risk-like aggregates without loading Phase 4 models."""
    scores = []
    hba = labs.get("hba1c")
    if hba is not None:
        scores.append(min(1.0, max(0.0, (float(hba) - 5.4) / 4.0)))
    creat = labs.get("creatinine")
    if creat is not None:
        scores.append(min(1.0, max(0.0, (float(creat) - 0.9) / 2.0)))
    alt = labs.get("alt")
    if alt is not None:
        scores.append(min(1.0, max(0.0, (float(alt) - 40) / 120.0)))
    hb = labs.get("hemoglobin")
    if hb is not None:
        scores.append(min(1.0, max(0.0, (13.5 - float(hb)) / 5.0)))
    tsh = labs.get("tsh")
    if tsh is not None:
        scores.append(min(1.0, max(0.0, abs(float(tsh) - 2.0) / 8.0)))
    if not scores:
        return {"risk_mean_proxy": 0.35, "risk_max_proxy": 0.35}
    return {
        "risk_mean_proxy": float(np.mean(scores)),
        "risk_max_proxy": float(np.max(scores)),
    }


def forecast_proxy(slopes: dict[str, float]) -> dict[str, float]:
    """Trend worsening proxy (higher = more concerning upward labs)."""
    bad_up = (
        max(0.0, slopes.get("hba1c_slope", 0.0))
        + max(0.0, slopes.get("creatinine_slope", 0.0))
        + max(0.0, slopes.get("alt_slope", 0.0))
        + max(0.0, -slopes.get("hemoglobin_slope", 0.0))
    )
    return {
        "forecast_worsening_proxy": float(min(1.0, bad_up * 50.0)),
        "trend_penalty": float(min(20.0, bad_up * 200.0)),
    }


def metrics_to_feature_dict(
    metrics: list[dict[str, Any]] | None,
    *,
    demographics: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    series = extract_series(metrics)
    out: dict[str, float | None] = {c: None for c in FEATURE_COLUMNS}
    demo = demographics or {}

    for feat, pts in series.items():
        if feat in out and pts:
            out[feat] = float(pts[-1][1])

    age = demo.get("age")
    if age is None and series.get("age"):
        age = series["age"][-1][1]
    try:
        out["age"] = float(age) if age is not None else None
    except (TypeError, ValueError):
        out["age"] = None

    sex = demo.get("sex") or demo.get("gender")
    if sex is None:
        out["sex_female"] = 0.5
    else:
        s = str(sex).strip().lower()
        if s in ("f", "female", "woman", "1"):
            out["sex_female"] = 1.0
        elif s in ("m", "male", "man", "0"):
            out["sex_female"] = 0.0
        else:
            out["sex_female"] = 0.5

    for k in ("bmi", "systolic_bp", "diastolic_bp"):
        if demo.get(k) is not None:
            try:
                out[k] = float(demo[k])
            except (TypeError, ValueError):
                pass

    ast, alt = out.get("ast"), out.get("alt")
    if ast is not None and alt is not None and float(alt) > 0:
        out["ast_alt_ratio"] = float(ast) / float(alt)
    tc, hdl = out.get("total_cholesterol"), out.get("hdl")
    if tc is not None and hdl is not None and float(hdl) > 0:
        out["tc_hdl_ratio"] = float(tc) / float(hdl)
        out["non_hdl"] = float(tc) - float(hdl)

    slope_map = {
        "hba1c_slope": _slope(series.get("hba1c") or []),
        "creatinine_slope": _slope(series.get("creatinine") or []),
        "alt_slope": _slope(series.get("alt") or []),
        "hemoglobin_slope": _slope(series.get("hemoglobin") or []),
    }
    out.update(slope_map)

    core_labs = [
        "hba1c",
        "fasting_glucose",
        "creatinine",
        "egfr",
        "alt",
        "ast",
        "ldl",
        "hdl",
        "triglycerides",
        "tsh",
        "hemoglobin",
    ]
    present = sum(1 for k in core_labs if out.get(k) is not None)
    out["n_recent_labs"] = float(present)
    out["missing_fraction"] = float(1.0 - present / max(1, len(core_labs)))

    out.update(risk_proxies_from_labs(out))
    out.update(forecast_proxy(slope_map))
    return out


# Robust imputation medians for synthetic-like population
DEFAULT_IMPUTE: dict[str, float] = {
    "age": 45.0,
    "sex_female": 0.5,
    "hba1c": 5.6,
    "fasting_glucose": 95.0,
    "random_glucose": 115.0,
    "creatinine": 0.95,
    "egfr": 95.0,
    "alt": 25.0,
    "ast": 24.0,
    "total_cholesterol": 185.0,
    "ldl": 110.0,
    "hdl": 50.0,
    "triglycerides": 130.0,
    "tsh": 2.0,
    "hemoglobin": 13.5,
    "bmi": 25.0,
    "systolic_bp": 118.0,
    "diastolic_bp": 76.0,
    "ast_alt_ratio": 1.0,
    "tc_hdl_ratio": 3.7,
    "non_hdl": 135.0,
    "missing_fraction": 0.2,
    "n_recent_labs": 8.0,
    "hba1c_slope": 0.0,
    "creatinine_slope": 0.0,
    "alt_slope": 0.0,
    "hemoglobin_slope": 0.0,
    "risk_mean_proxy": 0.25,
    "risk_max_proxy": 0.35,
    "forecast_worsening_proxy": 0.1,
    "trend_penalty": 2.0,
}


def feature_dict_to_vector(
    fd: dict[str, float | None],
    impute: dict[str, float] | None = None,
) -> np.ndarray:
    imp = impute or DEFAULT_IMPUTE
    return np.asarray(
        [
            float(fd[c]) if fd.get(c) is not None else float(imp.get(c, 0.0))
            for c in FEATURE_COLUMNS
        ],
        dtype=np.float64,
    )


def heuristic_health_score(fd: dict[str, float | None]) -> float:
    """
    Rule-based target for synthetic training (0–100). Non-diagnostic.
    Higher = better orientation.
    """
    score = 88.0
    def g(k, default=None):
        v = fd.get(k)
        return float(v) if v is not None else default

    hba = g("hba1c")
    if hba is not None:
        if hba >= 6.5:
            score -= min(25, (hba - 5.7) * 8)
        elif hba >= 5.7:
            score -= (hba - 5.7) * 10
    fg = g("fasting_glucose")
    if fg is not None and fg > 100:
        score -= min(12, (fg - 100) * 0.15)
    creat = g("creatinine")
    if creat is not None and creat > 1.2:
        score -= min(18, (creat - 1.2) * 15)
    egfr = g("egfr")
    if egfr is not None and egfr < 90:
        score -= min(18, (90 - egfr) * 0.35)
    alt = g("alt")
    if alt is not None and alt > 40:
        score -= min(12, (alt - 40) * 0.15)
    ldl = g("ldl")
    if ldl is not None and ldl > 100:
        score -= min(12, (ldl - 100) * 0.08)
    hdl = g("hdl")
    if hdl is not None:
        if hdl < 40:
            score -= min(10, (40 - hdl) * 0.5)
        elif hdl >= 60:
            score += min(5, (hdl - 50) * 0.15)
    hb = g("hemoglobin")
    if hb is not None and hb < 12:
        score -= min(15, (12 - hb) * 3)
    tsh = g("tsh")
    if tsh is not None and (tsh < 0.4 or tsh > 4.5):
        score -= min(10, abs(tsh - 2.5) * 1.5)
    miss = g("missing_fraction", 0.0) or 0.0
    score -= miss * 8
    risk = g("risk_mean_proxy", 0.0) or 0.0
    score -= risk * 15
    score -= (g("forecast_worsening_proxy", 0.0) or 0.0) * 8
    score -= (g("trend_penalty", 0.0) or 0.0) * 0.3
    age = g("age")
    if age is not None and age > 60:
        score -= min(5, (age - 60) * 0.15)
    # small noise-free clip
    return float(max(5.0, min(99.0, score)))


def select_stable_features(
    X: np.ndarray, y: np.ndarray, names: list[str], max_features: int = 28
) -> list[str]:
    """Correlation / variance based simple selection (keeps all if small)."""
    if X.shape[1] <= max_features:
        return list(names)
    keep = []
    for i, n in enumerate(names):
        col = X[:, i]
        if np.std(col) < 1e-9:
            continue
        corr = abs(float(np.corrcoef(col, y)[0, 1])) if len(y) > 2 else 0.0
        keep.append((n, corr if not np.isnan(corr) else 0.0))
    keep.sort(key=lambda t: -t[1])
    return [n for n, _ in keep[:max_features]] or list(names)
