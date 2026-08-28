"""
Dataset loaders for disease risk.

MIMIC-IV / NHANES / eICU / UCI full dumps are NOT redistributed.
Optional external paths via env:
  MIMIC_RISK_PATH, NHANES_RISK_PATH, PIMA_PATH

Shipped: synthetic educational longitudinal biomarker rows (no PHI).
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

import numpy as np

from .diseases import DISEASES, FEATURE_COLUMNS
from .preprocess import compute_impute_medians, feature_dict_to_vector


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_dir() -> Path:
    return _repo_root() / "datasets" / "risk_prediction"


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


def _sample_row(rng: random.Random, disease_bias: str | None = None) -> dict[str, Any]:
    """Generate one synthetic patient feature row + multi-label risks."""
    age = rng.uniform(22, 78)
    sex_f = rng.choice([0.0, 1.0])
    hb = rng.gauss(13.5 if sex_f < 0.5 else 12.5, 1.2)
    hba1c = rng.gauss(5.4, 0.4)
    fpg = rng.gauss(95, 12)
    rnd_gluc = rng.gauss(110, 20)
    alt = abs(rng.gauss(28, 10))
    ast = abs(rng.gauss(26, 10))
    creat = abs(rng.gauss(0.9, 0.2))
    egfr = rng.gauss(95, 15)
    urea = abs(rng.gauss(28, 8))
    tsh = abs(rng.gauss(2.2, 0.8))
    ft4 = abs(rng.gauss(1.2, 0.25))
    tc = rng.gauss(190, 30)
    hdl = rng.gauss(50, 10)
    ldl = rng.gauss(115, 25)
    tg = abs(rng.gauss(140, 40))
    plt = rng.gauss(250, 45)
    wbc = rng.gauss(7.0, 1.5)
    rbc = rng.gauss(4.7, 0.4)
    bmi = rng.gauss(25, 4)
    sbp = rng.gauss(122, 14)
    dbp = rng.gauss(78, 9)

    labels = {d["id"]: 0 for d in DISEASES}

    if disease_bias == "type2_diabetes" or rng.random() < 0.18:
        hba1c = rng.uniform(6.2, 9.5)
        fpg = rng.uniform(115, 180)
        bmi = rng.uniform(28, 40)
        labels["type2_diabetes"] = 1
    if disease_bias == "anemia" or rng.random() < 0.15:
        hb = rng.uniform(7.5, 11.5) if sex_f < 0.5 else rng.uniform(7.0, 11.0)
        rbc = rng.uniform(3.2, 4.2)
        labels["anemia"] = 1
    if disease_bias == "ckd" or rng.random() < 0.12:
        creat = rng.uniform(1.4, 3.0)
        egfr = rng.uniform(20, 58)
        urea = rng.uniform(40, 90)
        labels["ckd"] = 1
    if disease_bias == "liver_dysfunction" or rng.random() < 0.12:
        alt = rng.uniform(60, 200)
        ast = rng.uniform(55, 180)
        labels["liver_dysfunction"] = 1
    if disease_bias == "thyroid_dysfunction" or rng.random() < 0.12:
        if rng.random() < 0.5:
            tsh = rng.uniform(5.5, 20)
            ft4 = rng.uniform(0.4, 0.9)
        else:
            tsh = rng.uniform(0.01, 0.25)
            ft4 = rng.uniform(1.8, 3.5)
        labels["thyroid_dysfunction"] = 1

    feats = {
        "age": age,
        "sex_female": sex_f,
        "hemoglobin": hb,
        "hba1c": hba1c,
        "fasting_glucose": fpg,
        "random_glucose": rnd_gluc,
        "alt": alt,
        "ast": ast,
        "creatinine": creat,
        "egfr": egfr,
        "urea": urea,
        "tsh": tsh,
        "free_t4": ft4,
        "total_cholesterol": tc,
        "hdl": hdl,
        "ldl": ldl,
        "triglycerides": tg,
        "platelets": plt,
        "wbc": wbc,
        "rbc": rbc,
        "bmi": bmi,
        "systolic_bp": sbp,
        "diastolic_bp": dbp,
        "ast_alt_ratio": ast / alt if alt else None,
        "tc_hdl_ratio": tc / hdl if hdl else None,
        "non_hdl": tc - hdl if tc is not None and hdl is not None else None,
        "missing_fraction": 0.0,
    }
    # sparse missingness
    for k in list(feats.keys()):
        if k in ("age", "sex_female", "missing_fraction"):
            continue
        if rng.random() < 0.08:
            feats[k] = None

    return {"features": feats, "labels": labels, "source": "synthetic"}


def generate_synthetic_dataset(n: int = 800, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    biases = [None] + [d["id"] for d in DISEASES]
    for i in range(n):
        bias = biases[i % len(biases)]
        rows.append(_sample_row(rng, bias if rng.random() < 0.55 else None))
    return rows


def ensure_dataset_files(data_dir: Path | None = None) -> dict[str, Path]:
    d = data_dir or default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    train_p = d / "train_synthetic.jsonl"
    eval_p = d / "eval_synthetic.jsonl"
    lic = d / "LICENSING.md"
    if not train_p.exists():
        write_jsonl(train_p, generate_synthetic_dataset(900, seed=42))
    if not eval_p.exists():
        write_jsonl(eval_p, generate_synthetic_dataset(250, seed=7))
    if not lic.exists():
        lic.write_text(
            """# Risk prediction data licensing

| Resource | Redistributed? | Notes |
|----------|----------------|-------|
| Synthetic longitudinal biomarkers | Yes | Educational; no PHI |
| MIMIC-IV | **No** | Use PhysioNet license offline; set MIMIC_RISK_PATH |
| NHANES | **No** | CDC public — optional NHANES_RISK_PATH |
| Pima / UCI Heart | **No** full dump | Optional PIMA_PATH / UCI_HEART_PATH |
| eICU | **No** | PhysioNet credentialed |

Do not commit real patient extractions.
""",
            encoding="utf-8",
        )
    return {"train": train_p, "eval": eval_p, "licensing": lic}


def load_train_rows(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    rows = load_jsonl(d / "train_synthetic.jsonl")
    # optional external merges
    for env_key in ("MIMIC_RISK_PATH", "NHANES_RISK_PATH", "PIMA_PATH"):
        p = os.getenv(env_key)
        if p:
            rows.extend(load_jsonl(Path(p)))
    return rows or generate_synthetic_dataset(400)


def load_eval_rows(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    return load_jsonl(d / "eval_synthetic.jsonl") or generate_synthetic_dataset(120, seed=9)


def rows_to_matrices(
    rows: list[dict[str, Any]],
    impute: dict[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    """Return X, {disease_id: y}, impute_dict."""
    fdicts = [r["features"] for r in rows]
    imp = impute or compute_impute_medians(fdicts)
    X = np.stack([feature_dict_to_vector(fd, impute_values=imp) for fd in fdicts])
    ys: dict[str, np.ndarray] = {}
    for d in DISEASES:
        did = d["id"]
        ys[did] = np.asarray([int(r["labels"].get(did, 0)) for r in rows], dtype=int)
    return X, ys, imp


def metrics_list_from_feature_dict(fd: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert feature dict → metrics list shape used at inference."""
    name_map = {
        "hemoglobin": "Haemoglobin",
        "hba1c": "HbA1c",
        "fasting_glucose": "Fasting Glucose",
        "random_glucose": "Random Glucose",
        "alt": "Alanine Aminotransferase",
        "ast": "Aspartate Aminotransferase",
        "creatinine": "Creatinine",
        "egfr": "eGFR",
        "urea": "Urea",
        "tsh": "TSH",
        "free_t4": "Free T4",
        "total_cholesterol": "Total Cholesterol",
        "hdl": "HDL Cholesterol",
        "ldl": "LDL Cholesterol",
        "triglycerides": "Triglycerides",
        "platelets": "Platelets",
        "wbc": "WBC",
        "rbc": "RBC",
    }
    out = []
    for k, label in name_map.items():
        v = fd.get(k)
        if v is None:
            continue
        out.append({"test_name": label, "value_numeric": v})
    return out
