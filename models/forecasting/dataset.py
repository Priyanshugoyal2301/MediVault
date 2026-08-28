"""
Synthetic longitudinal labs + optional external JSONL paths.

MIMIC-IV / eICU / NHANES are NOT redistributed.
Set MIMIC_FORECAST_PATH / EICU_FORECAST_PATH / NHANES_FORECAST_PATH offline.
"""

from __future__ import annotations

import json
import os
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from .biomarkers import BIOMARKERS, POINT_FEATURE_NAMES
from .feature_engineering import build_point_features, feature_vector


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_dir() -> Path:
    return _repo_root() / "datasets" / "forecasting"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# Base means/sds for synthetic generation
_BASE = {
    "hba1c": (5.6, 0.4, 0.02),
    "fasting_glucose": (98, 12, 0.5),
    "random_glucose": (120, 18, 0.4),
    "creatinine": (0.95, 0.15, 0.01),
    "egfr": (95, 12, -0.3),
    "alt": (28, 8, 0.1),
    "ast": (26, 8, 0.1),
    "total_cholesterol": (190, 25, 0.2),
    "ldl": (115, 20, 0.3),
    "hdl": (48, 8, -0.05),
    "triglycerides": (140, 35, 0.4),
    "tsh": (2.2, 0.7, 0.0),
    "hemoglobin": (13.5, 1.0, -0.01),
}


def generate_patient_series(
    rng: random.Random,
    *,
    n_visits: int = 5,
    drift: bool = True,
) -> dict[str, Any]:
    age0 = rng.uniform(28, 70)
    sex_f = rng.choice([0.0, 1.0])
    start = date(2019, 1, 1) + timedelta(days=rng.randint(0, 400))
    history: list[dict[str, Any]] = []
    levels = {k: rng.gauss(mu, sd) for k, (mu, sd, _) in _BASE.items()}
    if sex_f >= 0.5:
        levels["hemoglobin"] = rng.gauss(12.5, 0.9)

    for v in range(n_visits):
        t = start + timedelta(days=int(rng.uniform(25, 100) * (v + 1)))
        age = age0 + (t - start).days / 365.0
        for bid, (mu, sd, slope) in _BASE.items():
            if drift:
                levels[bid] = levels[bid] + slope * rng.uniform(0.5, 1.5) + rng.gauss(0, sd * 0.15)
            else:
                levels[bid] = levels[bid] + rng.gauss(0, sd * 0.08)
            # occasional missing biomarker
            if rng.random() < 0.12:
                continue
            name = next(b["name"] for b in BIOMARKERS if b["id"] == bid)
            history.append(
                {
                    "test_name": name,
                    "value_numeric": round(float(levels[bid]), 3),
                    "date_of_test": t.isoformat(),
                    "biomarker_id": bid,
                }
            )
        history.append(
            {
                "test_name": "age_marker",
                "value_numeric": age,
                "date_of_test": t.isoformat(),
            }
        )
    return {
        "patient_id": f"syn_{rng.randint(1000, 999999)}",
        "sex_female": sex_f,
        "history": history,
        "source": "synthetic",
    }


def series_to_supervised_rows(
    patients: list[dict[str, Any]],
    *,
    horizon_days: int = 180,
    min_points: int = 2,
) -> list[dict[str, Any]]:
    """
    Build supervised (X, y, bid) from each patient's per-biomarker series:
    use prefix history to predict value ~horizon later (or next-ish).
    """
    from collections import defaultdict

    rows: list[dict[str, Any]] = []
    for p in patients:
        sex_f = float(p.get("sex_female", 0.5))
        by_bid: dict[str, list[tuple[date, float]]] = defaultdict(list)
        age = 45.0
        for m in p.get("history") or []:
            if (m.get("test_name") or "") == "age_marker":
                try:
                    age = float(m["value_numeric"])
                except Exception:
                    pass
                continue
            bid = m.get("biomarker_id") or None
            if not bid:
                from .biomarkers import alias_to_id

                bid = alias_to_id(str(m.get("test_name") or ""))
            if not bid:
                continue
            try:
                val = float(m["value_numeric"])
                d = date.fromisoformat(str(m.get("date_of_test"))[:10])
            except Exception:
                continue
            by_bid[bid].append((d, val))

        for bid, series in by_bid.items():
            series = sorted(series, key=lambda x: x[0])
            if len(series) < min_points + 1:
                continue
            # for each eligible end index, train to predict next observation
            for i in range(min_points, len(series)):
                prefix = series[:i]
                target_date, target_val = series[i]
                gap = (target_date - prefix[-1][0]).days
                if gap < 1:
                    continue
                # scale features using actual gap as horizon proxy (irregular)
                feats = build_point_features(
                    prefix,
                    horizon_days=max(gap, horizon_days // 3),
                    age=age,
                    sex_female=sex_f,
                )
                # also emit a horizon=horizon_days target row using last usable
                rows.append(
                    {
                        "biomarker_id": bid,
                        "features": feats,
                        "y": float(target_val),
                        "horizon_days": int(gap),
                    }
                )
            # fixed-horizon synthetic target via linear projection for horizon_days
            if len(series) >= min_points:
                prefix = series[:-1]
                last = series[-1][1]
                # crude target: last + slope*horizon
                feats_h = build_point_features(
                    prefix if len(prefix) >= min_points else series[: min_points],
                    horizon_days=horizon_days,
                    age=age,
                    sex_female=sex_f,
                )
                slope = float(feats_h.get("slope_per_day") or 0.0)
                y_h = last + slope * horizon_days + float(
                    np.random.default_rng(abs(hash(bid + str(last))) % (2**32)).normal(0, 0.05 * abs(last) + 0.01)
                )
                rows.append(
                    {
                        "biomarker_id": bid,
                        "features": feats_h,
                        "y": float(y_h),
                        "horizon_days": horizon_days,
                    }
                )
    return rows


def ensure_dataset_files(data_dir: Path | None = None) -> dict[str, Path]:
    d = data_dir or default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    train_p = d / "train_synthetic.jsonl"
    eval_p = d / "eval_synthetic.jsonl"
    lic = d / "LICENSING.md"
    if not train_p.exists():
        rng = random.Random(42)
        pts = [generate_patient_series(rng, n_visits=rng.randint(4, 7)) for _ in range(120)]
        write_jsonl(train_p, pts)
    if not eval_p.exists():
        rng = random.Random(7)
        pts = [generate_patient_series(rng, n_visits=rng.randint(4, 6)) for _ in range(40)]
        write_jsonl(eval_p, pts)
    if not lic.exists():
        lic.write_text(
            """# Forecasting datasets

| Resource | Redistributed? |
|----------|----------------|
| Synthetic longitudinal labs | Yes (no PHI) |
| MIMIC-IV / eICU | No — MIMIC_FORECAST_PATH / EICU_FORECAST_PATH |
| NHANES | No — NHANES_FORECAST_PATH |
""",
            encoding="utf-8",
        )
    return {"train": train_p, "eval": eval_p, "licensing": lic}


def load_train_patients(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    rows = load_jsonl(d / "train_synthetic.jsonl")
    for env_key in ("MIMIC_FORECAST_PATH", "EICU_FORECAST_PATH", "NHANES_FORECAST_PATH"):
        p = os.getenv(env_key)
        if p:
            rows.extend(load_jsonl(Path(p)))
    return rows or [generate_patient_series(random.Random(1))]


def load_eval_patients(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    return load_jsonl(d / "eval_synthetic.jsonl") or [
        generate_patient_series(random.Random(2))
    ]


def supervised_from_patients(
    patients: list[dict[str, Any]], horizon_days: int = 180
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Return X[bid], y[bid] matrices."""
    rows = series_to_supervised_rows(patients, horizon_days=horizon_days)
    by_x: dict[str, list] = {}
    by_y: dict[str, list] = {}
    for r in rows:
        bid = r["biomarker_id"]
        by_x.setdefault(bid, []).append(feature_vector(r["features"]))
        by_y.setdefault(bid, []).append(float(r["y"]))
    X: dict[str, np.ndarray] = {}
    y: dict[str, np.ndarray] = {}
    for bid in by_x:
        X[bid] = np.stack(by_x[bid], axis=0)
        y[bid] = np.asarray(by_y[bid], dtype=float)
    return X, y
