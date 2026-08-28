"""Synthetic anomaly datasets + optional external paths."""

from __future__ import annotations

import json
import os
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from .feature_engineering import (
    DEFAULT_IMPUTE,
    feature_dict_to_vector,
    labs_to_feature_dict,
    series_features,
)
from .schema import FEATURE_COLUMNS, LAB_KEYS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_dir() -> Path:
    return _repo_root() / "datasets" / "anomaly_detection"


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
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _normal_labs(rng: random.Random) -> dict[str, float]:
    return {
        "hba1c": rng.gauss(5.5, 0.25),
        "fasting_glucose": rng.gauss(95, 8),
        "creatinine": rng.gauss(0.95, 0.1),
        "egfr": rng.gauss(95, 8),
        "alt": rng.gauss(24, 6),
        "ast": rng.gauss(22, 6),
        "ldl": rng.gauss(110, 15),
        "hdl": rng.gauss(52, 8),
        "triglycerides": rng.gauss(130, 20),
        "tsh": rng.gauss(2.0, 0.4),
        "hemoglobin": rng.gauss(13.5, 0.8),
        "total_cholesterol": rng.gauss(185, 18),
    }


def _anomalous_labs(rng: random.Random) -> dict[str, float]:
    labs = _normal_labs(rng)
    mode = rng.choice(["kidney", "liver", "metabolic", "combo", "rare_combo"])
    if mode == "kidney":
        labs["creatinine"] = rng.gauss(2.4, 0.3)
        labs["egfr"] = rng.gauss(35, 8)
        labs["hemoglobin"] = rng.gauss(10.0, 0.5)
    elif mode == "liver":
        labs["alt"] = rng.gauss(180, 40)
        labs["ast"] = rng.gauss(150, 30)
    elif mode == "metabolic":
        labs["hba1c"] = rng.gauss(9.5, 0.8)
        labs["fasting_glucose"] = rng.gauss(210, 25)
        labs["triglycerides"] = rng.gauss(350, 40)
    elif mode == "combo":
        labs["creatinine"] = rng.gauss(1.9, 0.2)
        labs["alt"] = rng.gauss(90, 15)
        labs["hemoglobin"] = rng.gauss(9.5, 0.4)
    else:
        # rare combination: very high HDL with very high creat — atypical joint
        labs["hdl"] = rng.gauss(95, 5)
        labs["creatinine"] = rng.gauss(2.8, 0.2)
        labs["tsh"] = rng.gauss(12.0, 1.0)
    return labs


def generate_row(rng: random.Random, *, is_anomaly: bool) -> dict[str, Any]:
    age = rng.uniform(25, 75)
    sex_f = rng.choice([0.0, 1.0])
    labs = _anomalous_labs(rng) if is_anomaly else _normal_labs(rng)
    # occasional missing
    for k in list(labs.keys()):
        if rng.random() < 0.05:
            del labs[k]
    # series for one random analyte
    key = rng.choice(list(labs.keys()))
    n = rng.randint(3, 6)
    start = date(2022, 1, 1) + timedelta(days=rng.randint(0, 200))
    series_pts = []
    base = labs[key]
    for i in range(n):
        drift = (0.15 * i) if is_anomaly else (0.01 * i)
        series_pts.append(
            {
                "date": (start + timedelta(days=30 * i)).isoformat(),
                "value": round(base * (1 + drift * 0.05) + rng.gauss(0, abs(base) * 0.02), 3),
            }
        )
    history = [
        {
            "test_name": k,
            "value_numeric": round(v, 3),
            "date_of_test": series_pts[-1]["date"],
        }
        for k, v in labs.items()
    ]
    return {
        "patient_id": f"an_{rng.randint(1000, 999999)}",
        "is_anomaly": int(is_anomaly),
        "labs": labs,
        "history": history,
        "series_test": key,
        "series_points": series_pts,
        "demographics": {
            "age": age,
            "sex": "female" if sex_f >= 0.5 else "male",
        },
        "source": "synthetic",
    }


def ensure_dataset_files(data_dir: Path | None = None) -> dict[str, Path]:
    d = data_dir or default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    train_p = d / "train_synthetic.jsonl"
    eval_p = d / "eval_synthetic.jsonl"
    lic = d / "LICENSING.md"
    if not train_p.exists():
        rng = random.Random(42)
        rows = [generate_row(rng, is_anomaly=False) for _ in range(280)]
        rows += [generate_row(rng, is_anomaly=True) for _ in range(40)]
        rng.shuffle(rows)
        write_jsonl(train_p, rows)
    if not eval_p.exists():
        rng = random.Random(7)
        rows = [generate_row(rng, is_anomaly=False) for _ in range(80)]
        rows += [generate_row(rng, is_anomaly=True) for _ in range(20)]
        rng.shuffle(rows)
        write_jsonl(eval_p, rows)
    if not lic.exists():
        lic.write_text(
            """# Anomaly detection datasets

| Resource | Redistributed? |
|----------|----------------|
| Synthetic labs + injected anomalies | Yes |
| NHANES | No — NHANES_ANOMALY_PATH |
| MIMIC-IV | No — MIMIC_ANOMALY_PATH |
""",
            encoding="utf-8",
        )
    return {"train": train_p, "eval": eval_p, "licensing": lic}


def load_train_rows(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    rows = load_jsonl(d / "train_synthetic.jsonl")
    for env_key in ("NHANES_ANOMALY_PATH", "MIMIC_ANOMALY_PATH"):
        p = os.getenv(env_key)
        if p:
            rows.extend(load_jsonl(Path(p)))
    return rows or [generate_row(random.Random(1), is_anomaly=False)]


def load_eval_rows(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    return load_jsonl(d / "eval_synthetic.jsonl") or [
        generate_row(random.Random(2), is_anomaly=True)
    ]


def row_to_vector(
    row: dict[str, Any],
    *,
    medians: dict[str, float] | None = None,
    iqrs: dict[str, float] | None = None,
    impute: dict[str, float] | None = None,
) -> np.ndarray:
    from datetime import date as date_cls

    labs = row.get("labs") or {}
    series = None
    if row.get("series_points"):
        pts = []
        for p in row["series_points"]:
            pts.append((date_cls.fromisoformat(str(p["date"])[:10]), float(p["value"])))
        series = series_features(pts)
    fd = labs_to_feature_dict(
        {k: float(v) for k, v in labs.items()},
        demographics=row.get("demographics"),
        series=series,
    )
    return feature_dict_to_vector(fd, impute or DEFAULT_IMPUTE, medians=medians, iqrs=iqrs)


def rows_to_matrix(
    rows: list[dict[str, Any]],
    *,
    medians: dict[str, float] | None = None,
    iqrs: dict[str, float] | None = None,
    impute: dict[str, float] | None = None,
    fit_stats_from: list[dict[str, Any]] | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, float], dict[str, float], dict[str, float]]:
    """Returns X, y, impute, medians, iqrs."""
    base_rows = fit_stats_from
    if base_rows is None:
        normals = [r for r in rows if not int(r.get("is_anomaly") or 0)]
        base_rows = normals or rows
    if medians is None or iqrs is None:
        raw = []
        for r in base_rows:
            labs = r.get("labs") or {}
            fd = labs_to_feature_dict(
                {k: float(v) for k, v in labs.items()},
                demographics=r.get("demographics"),
            )
            raw.append(
                [
                    float(fd[c]) if fd.get(c) is not None else DEFAULT_IMPUTE[c]
                    for c in FEATURE_COLUMNS
                ]
            )
        raw_m = np.asarray(raw, dtype=float)
        medians = {c: float(np.median(raw_m[:, i])) for i, c in enumerate(FEATURE_COLUMNS)}
        iqrs = {}
        for i, c in enumerate(FEATURE_COLUMNS):
            q75, q25 = np.percentile(raw_m[:, i], [75, 25])
            iqrs[c] = float(max(q75 - q25, 1e-3))
    impute = impute or dict(medians)

    X = np.stack(
        [row_to_vector(r, medians=medians, iqrs=iqrs, impute=impute) for r in rows]
    )
    y = np.asarray([int(r.get("is_anomaly") or 0) for r in rows], dtype=int)
    return X, y, impute, medians, iqrs
