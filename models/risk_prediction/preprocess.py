"""Preprocess patient metric dicts → dense feature row."""

from __future__ import annotations

from typing import Any

import numpy as np

from .diseases import FEATURE_COLUMNS, TEST_NAME_SYNONYMS


def _norm_name(name: str) -> str:
    return " ".join((name or "").strip().lower().replace("_", " ").split())


def _lookup_feature_key(test_name: str) -> str | None:
    key = _norm_name(test_name)
    for feat, aliases in TEST_NAME_SYNONYMS.items():
        if key == feat or key in aliases:
            return feat
        for a in aliases:
            if a in key or key in a:
                return feat
    return None


def extract_latest_lab_map(metrics: list[dict[str, Any]]) -> dict[str, float]:
    """
    Collapse longitudinal metrics to latest numeric value per feature key.
    metrics entries: test_name, value_numeric, date_of_test optional.
    """
    best: dict[str, tuple[str, float]] = {}  # feat -> (date, value)
    for m in metrics or []:
        try:
            val = m.get("value_numeric")
            if val is None:
                continue
            v = float(val)
        except (TypeError, ValueError):
            continue
        feat = _lookup_feature_key(str(m.get("test_name") or ""))
        if not feat:
            continue
        date = str(m.get("date_of_test") or m.get("date") or "")
        prev = best.get(feat)
        if prev is None or date >= prev[0]:
            best[feat] = (date, v)
    return {k: v for k, (_, v) in best.items()}


def metrics_to_feature_dict(
    metrics: list[dict[str, Any]],
    *,
    demographics: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    labs = extract_latest_lab_map(metrics)
    demo = demographics or {}
    # demographics may also appear as metric-like keys in first dict
    out: dict[str, float | None] = {c: None for c in FEATURE_COLUMNS}

    for k, v in labs.items():
        if k in out:
            out[k] = float(v)

    age = demo.get("age")
    if age is None:
        age = labs.get("age")  # type: ignore[assignment]
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

    # Derived biomarkers
    ast, alt = out.get("ast"), out.get("alt")
    if ast is not None and alt is not None and float(alt) > 0:
        out["ast_alt_ratio"] = float(ast) / float(alt)
    tc, hdl = out.get("total_cholesterol"), out.get("hdl")
    if tc is not None and hdl is not None and float(hdl) > 0:
        out["tc_hdl_ratio"] = float(tc) / float(hdl)
        out["non_hdl"] = float(tc) - float(hdl)

    present = sum(1 for c in FEATURE_COLUMNS if out.get(c) is not None)
    out["missing_fraction"] = 1.0 - (present / max(1, len(FEATURE_COLUMNS)))
    return out


def feature_dict_to_vector(
    fdict: dict[str, float | None],
    *,
    impute_values: dict[str, float] | None = None,
) -> np.ndarray:
    imp = impute_values or {}
    row = []
    for c in FEATURE_COLUMNS:
        v = fdict.get(c)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            row.append(float(imp.get(c, 0.0)))
        else:
            row.append(float(v))
    return np.asarray(row, dtype=np.float64)


def compute_impute_medians(rows: list[dict[str, float | None]]) -> dict[str, float]:
    med: dict[str, float] = {}
    for c in FEATURE_COLUMNS:
        vals = [float(r[c]) for r in rows if r.get(c) is not None]
        med[c] = float(np.median(vals)) if vals else 0.0
    return med
