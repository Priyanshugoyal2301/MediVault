"""Synthetic + optional external datasets for health score."""

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
    heuristic_health_score,
    metrics_to_feature_dict,
)
from .schema import FEATURE_COLUMNS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_dir() -> Path:
    return _repo_root() / "datasets" / "health_score"


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


def generate_patient(rng: random.Random, *, n_visits: int = 3) -> dict[str, Any]:
    age = rng.uniform(25, 75)
    sex_f = rng.choice([0.0, 1.0])
    profile = rng.choice(["healthy", "mixed", "elevated"])
    base = {
        "HbA1c": 5.4 if profile == "healthy" else (6.2 if profile == "mixed" else 7.4),
        "Fasting Glucose": 92 if profile == "healthy" else 115,
        "Creatinine": 0.9 if profile != "elevated" else 1.5,
        "eGFR": 100 if profile != "elevated" else 62,
        "ALT": 22 if profile != "elevated" else 70,
        "AST": 20 if profile != "elevated" else 55,
        "LDL": 95 if profile == "healthy" else 145,
        "HDL": 58 if profile == "healthy" else 38,
        "Triglycerides": 120 if profile != "elevated" else 220,
        "Total Cholesterol": 180 if profile != "elevated" else 240,
        "TSH": 2.0,
        "Hemoglobin": 13.8 if sex_f < 0.5 else 12.8,
    }
    if profile == "elevated":
        base["Hemoglobin"] = 10.5 if sex_f >= 0.5 else 11.2
        base["TSH"] = rng.choice([0.2, 7.5])

    start = date(2022, 1, 1) + timedelta(days=rng.randint(0, 200))
    history = []
    for v in range(n_visits):
        t = start + timedelta(days=int(rng.uniform(30, 90) * (v + 1)))
        drift = 0.05 * v if profile != "healthy" else -0.02 * v
        for name, val in base.items():
            noise = rng.gauss(0, abs(val) * 0.03 + 0.05)
            if rng.random() < 0.08:
                continue
            history.append(
                {
                    "test_name": name,
                    "value_numeric": round(float(val + noise + drift), 3),
                    "date_of_test": t.isoformat(),
                }
            )
        history.append(
            {
                "test_name": "age",
                "value_numeric": age + v * 0.15,
                "date_of_test": t.isoformat(),
            }
        )
    demo = {
        "age": age,
        "sex": "female" if sex_f >= 0.5 else "male",
        "bmi": rng.gauss(24 if profile == "healthy" else 29, 2),
    }
    fd = metrics_to_feature_dict(history, demographics=demo)
    y = heuristic_health_score(fd)
    y = float(max(5, min(99, y + rng.gauss(0, 2.5))))
    return {
        "patient_id": f"hs_{rng.randint(1000, 999999)}",
        "history": history,
        "demographics": demo,
        "health_score": y,
        "source": "synthetic",
        "profile": profile,
    }


def ensure_dataset_files(data_dir: Path | None = None) -> dict[str, Path]:
    d = data_dir or default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    train_p = d / "train_synthetic.jsonl"
    eval_p = d / "eval_synthetic.jsonl"
    lic = d / "LICENSING.md"
    if not train_p.exists():
        rng = random.Random(42)
        write_jsonl(train_p, [generate_patient(rng) for _ in range(200)])
    if not eval_p.exists():
        rng = random.Random(7)
        write_jsonl(eval_p, [generate_patient(rng) for _ in range(50)])
    if not lic.exists():
        lic.write_text(
            """# Health score datasets

| Resource | Redistributed? |
|----------|----------------|
| Synthetic longitudinal labs | Yes (no PHI) |
| NHANES | No — NHANES_HEALTH_SCORE_PATH |
| MIMIC-IV | No — MIMIC_HEALTH_SCORE_PATH |
""",
            encoding="utf-8",
        )
    return {"train": train_p, "eval": eval_p, "licensing": lic}


def load_train_rows(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    rows = load_jsonl(d / "train_synthetic.jsonl")
    for env_key in ("NHANES_HEALTH_SCORE_PATH", "MIMIC_HEALTH_SCORE_PATH"):
        p = os.getenv(env_key)
        if p:
            rows.extend(load_jsonl(Path(p)))
    return rows or [generate_patient(random.Random(1))]


def load_eval_rows(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    return load_jsonl(d / "eval_synthetic.jsonl") or [
        generate_patient(random.Random(2))
    ]


def rows_to_matrices(
    rows: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    X_list = []
    y_list = []
    for r in rows:
        fd = metrics_to_feature_dict(r.get("history") or [], demographics=r.get("demographics"))
        X_list.append(feature_dict_to_vector(fd, DEFAULT_IMPUTE))
        y = r.get("health_score")
        if y is None:
            y = heuristic_health_score(fd)
        y_list.append(float(y))
    X = np.stack(X_list, axis=0) if X_list else np.zeros((0, len(FEATURE_COLUMNS)))
    y = np.asarray(y_list, dtype=float)
    # empirical impute from train
    impute = dict(DEFAULT_IMPUTE)
    if len(X):
        for i, c in enumerate(FEATURE_COLUMNS):
            col = X[:, i]
            impute[c] = float(np.median(col))
    return X, y, impute
