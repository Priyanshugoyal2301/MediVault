"""Feature engineering for anomaly detection (multi-marker + series)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np

from .schema import FEATURE_COLUMNS, LAB_KEYS, TEST_ALIASES


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
        return date(2020, 1, 1) + timedelta(days=idx * 30)


def robust_z(values: list[float], last: float | None = None) -> float:
    if not values:
        return 0.0
    arr = np.asarray(values, dtype=float)
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    scale = 1.4826 * mad if mad > 1e-9 else (float(np.std(arr)) + 1e-6)
    v = float(last if last is not None else arr[-1])
    return (v - med) / scale


def series_features(data_points: list[tuple[date, float]]) -> dict[str, float]:
    if not data_points:
        return {
            "series_last": 0.0,
            "series_mean": 0.0,
            "series_std": 0.0,
            "series_slope": 0.0,
            "series_delta": 0.0,
            "series_robust_z": 0.0,
            "series_n": 0.0,
        }
    pts = sorted(data_points, key=lambda x: x[0])
    vals = [float(v) for _, v in pts]
    last = vals[-1]
    mean = float(np.mean(vals))
    std = float(np.std(vals)) if len(vals) > 1 else 0.0
    delta = vals[-1] - vals[-2] if len(vals) >= 2 else 0.0
    if len(pts) >= 2:
        t0 = pts[0][0]
        xs = np.array([(d - t0).days for d, _ in pts], dtype=float)
        ys = np.array(vals, dtype=float)
        slope = float(np.polyfit(xs, ys, 1)[0]) if np.std(xs) > 1e-9 else 0.0
    else:
        slope = 0.0
    return {
        "series_last": last,
        "series_mean": mean,
        "series_std": std,
        "series_slope": slope,
        "series_delta": delta,
        "series_robust_z": robust_z(vals, last),
        "series_n": float(len(vals)),
    }


def extract_labs_from_metrics(metrics: list[dict[str, Any]] | None) -> dict[str, float]:
    best: dict[str, tuple[str, float]] = {}
    for i, m in enumerate(metrics or []):
        feat = alias_to_feature(str(m.get("test_name") or ""))
        if not feat or feat == "age":
            continue
        try:
            v = float(m["value_numeric"])
        except (KeyError, TypeError, ValueError):
            continue
        d = str(m.get("date_of_test") or m.get("date") or f"{i:04d}")
        prev = best.get(feat)
        if prev is None or d >= prev[0]:
            best[feat] = (d, v)
    return {k: v for k, (_, v) in best.items()}


def population_medians() -> dict[str, float]:
    return {
        "age": 45.0,
        "sex_female": 0.5,
        "hba1c": 5.5,
        "fasting_glucose": 95.0,
        "creatinine": 0.95,
        "egfr": 95.0,
        "alt": 25.0,
        "ast": 24.0,
        "ldl": 110.0,
        "hdl": 50.0,
        "triglycerides": 130.0,
        "tsh": 2.0,
        "hemoglobin": 13.5,
        "total_cholesterol": 185.0,
        "ast_alt_ratio": 1.0,
        "non_hdl": 135.0,
        "missing_fraction": 0.15,
        "n_labs": 8.0,
        "series_last": 0.0,
        "series_mean": 0.0,
        "series_std": 0.0,
        "series_slope": 0.0,
        "series_delta": 0.0,
        "series_robust_z": 0.0,
        "series_n": 0.0,
        "risk_proxy": 0.25,
        "forecast_shift_proxy": 0.1,
        "health_score_proxy": 75.0,
    }


DEFAULT_IMPUTE = population_medians()


def labs_to_feature_dict(
    labs: dict[str, float],
    *,
    demographics: dict[str, Any] | None = None,
    series: dict[str, float] | None = None,
) -> dict[str, float | None]:
    out: dict[str, float | None] = {c: None for c in FEATURE_COLUMNS}
    for k, v in labs.items():
        if k in out:
            out[k] = float(v)
    demo = demographics or {}
    age = demo.get("age")
    try:
        out["age"] = float(age) if age is not None else labs.get("age")  # type: ignore
    except (TypeError, ValueError):
        out["age"] = None
    sex = demo.get("sex") or demo.get("gender")
    if sex is None:
        out["sex_female"] = 0.5
    else:
        s = str(sex).lower()
        out["sex_female"] = 1.0 if s in ("f", "female", "woman", "1") else (
            0.0 if s in ("m", "male", "man", "0") else 0.5
        )

    ast, alt = out.get("ast"), out.get("alt")
    if ast is not None and alt is not None and float(alt) > 0:
        out["ast_alt_ratio"] = float(ast) / float(alt)
    tc, hdl = out.get("total_cholesterol"), out.get("hdl")
    if tc is not None and hdl is not None:
        out["non_hdl"] = float(tc) - float(hdl)

    present = sum(1 for k in LAB_KEYS if out.get(k) is not None)
    out["n_labs"] = float(present)
    out["missing_fraction"] = float(1.0 - present / max(1, len(LAB_KEYS)))

    # Soft proxies from labs (no calls into other phase engines)
    risk = 0.0
    if out.get("hba1c") is not None:
        risk = max(risk, min(1.0, (float(out["hba1c"]) - 5.4) / 4))
    if out.get("creatinine") is not None:
        risk = max(risk, min(1.0, (float(out["creatinine"]) - 0.9) / 2))
    out["risk_proxy"] = risk
    out["forecast_shift_proxy"] = abs(float((series or {}).get("series_slope") or 0.0)) * 10.0
    out["health_score_proxy"] = float(max(20.0, 90.0 - risk * 40.0 - out["missing_fraction"] * 10))

    if series:
        for k, v in series.items():
            if k in out:
                out[k] = float(v)
    return out


def feature_dict_to_vector(
    fd: dict[str, float | None],
    impute: dict[str, float] | None = None,
    *,
    robust_scale: bool = True,
    medians: dict[str, float] | None = None,
    iqrs: dict[str, float] | None = None,
) -> np.ndarray:
    imp = impute or DEFAULT_IMPUTE
    med = medians or DEFAULT_IMPUTE
    iqr = iqrs or {k: 1.0 for k in FEATURE_COLUMNS}
    vals = []
    for c in FEATURE_COLUMNS:
        v = float(fd[c]) if fd.get(c) is not None else float(imp.get(c, 0.0))
        if robust_scale:
            scale = float(iqr.get(c, 1.0)) or 1.0
            v = (v - float(med.get(c, 0.0))) / scale
        vals.append(v)
    return np.asarray(vals, dtype=np.float64)


def series_detect_vector(
    test_name: str,
    data_points: list[tuple[date, float]],
    *,
    demographics: dict[str, Any] | None = None,
    impute: dict[str, float] | None = None,
    medians: dict[str, float] | None = None,
    iqrs: dict[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, float | None]]:
    """Feature vector for single-analyte API path."""
    series = series_features(data_points)
    labs: dict[str, float] = {}
    feat = alias_to_feature(test_name)
    if feat and data_points:
        labs[feat] = float(sorted(data_points, key=lambda x: x[0])[-1][1])
    fd = labs_to_feature_dict(labs, demographics=demographics, series=series)
    # Also put last value into series_last already done
    x = feature_dict_to_vector(fd, impute, robust_scale=True, medians=medians, iqrs=iqrs)
    return x, fd


def contribution_from_scaled(x: np.ndarray, names: list[str] = None) -> list[tuple[str, float]]:
    names = names or FEATURE_COLUMNS
    abs_x = np.abs(x)
    if abs_x.sum() < 1e-12:
        return []
    order = np.argsort(-abs_x)
    out = []
    for i in order:
        name = names[i]
        if name.startswith("series_") or name in (
            "missing_fraction",
            "n_labs",
            "age",
            "sex_female",
            "risk_proxy",
            "forecast_shift_proxy",
            "health_score_proxy",
        ):
            # still include series_robust_z for single-series
            if name not in ("series_robust_z", "series_last", "series_delta", "series_slope") and name not in LAB_KEYS:
                if name not in LAB_KEYS and not name.startswith("series"):
                    continue
        out.append((name, float(abs_x[i])))
        if len(out) >= 8:
            break
    # Prefer lab keys
    lab_hits = [(n, v) for n, v in zip(names, abs_x) if n in LAB_KEYS]
    lab_hits.sort(key=lambda t: -t[1])
    if lab_hits:
        return lab_hits[:5]
    return out[:5]
