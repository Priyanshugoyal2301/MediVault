"""Evaluate rule-based vs ML disease risk models."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    import conftest  # noqa: F401
except Exception:
    pass


def evaluate(config_path: Path | None = None) -> dict:
    import numpy as np

    from models.risk_prediction.config_loader import load_config, resolve_path
    from models.risk_prediction.dataset import (
        load_eval_rows,
        metrics_list_from_feature_dict,
    )
    from models.risk_prediction.diseases import DISEASES, FEATURE_COLUMNS
    from models.risk_prediction.infer import DiseaseRiskEngine
    from models.risk_prediction.metrics import (
        binary_metrics,
        confusion_matrix_dict,
        expected_calibration_error,
        pr_auc,
        roc_auc,
        roc_curve_points,
    )
    from models.risk_prediction.rules import rule_based_probs

    cfg = load_config(config_path, validate=True)
    data_dir = resolve_path(cfg["paths"]["train_data"])
    rows = load_eval_rows(data_dir)
    eng = DiseaseRiskEngine(cfg, auto_train_if_missing=True)

    per_disease: dict = {}
    all_rule_auc: list[float] = []
    all_ml_auc: list[float] = []
    lat_ml: list[float] = []
    lat_rule: list[float] = []

    for d in DISEASES:
        did = d["id"]
        y_true: list[int] = []
        y_rule: list[float] = []
        y_ml: list[float] = []

        for r in rows:
            y_true.append(int(r["labels"].get(did, 0)))

            t0 = time.perf_counter()
            rule_p = rule_based_probs(r["features"])[did]
            lat_rule.append((time.perf_counter() - t0) * 1000)
            y_rule.append(rule_p)

            dem = {
                "age": r["features"].get("age"),
                "sex": "female" if r["features"].get("sex_female") == 1 else "male",
                "bmi": r["features"].get("bmi"),
            }
            metrics = metrics_list_from_feature_dict(r["features"])
            t0 = time.perf_counter()
            preds = eng.predict_conditions(metrics, demographics=dem)
            lat_ml.append((time.perf_counter() - t0) * 1000)
            prob = next(
                (c.risk_probability for c in preds if c.disease_id == did), 0.0
            )
            y_ml.append(prob)

        rule_m = binary_metrics(y_true, y_rule)
        ml_m = binary_metrics(y_true, y_ml)
        rule_m["roc_auc"] = roc_auc(y_true, y_rule)
        rule_m["pr_auc"] = pr_auc(y_true, y_rule)
        rule_m["ece"] = expected_calibration_error(y_true, y_rule)
        ml_m["roc_auc"] = roc_auc(y_true, y_ml)
        ml_m["pr_auc"] = pr_auc(y_true, y_ml)
        ml_m["ece"] = expected_calibration_error(y_true, y_ml)
        ml_m["confusion"] = confusion_matrix_dict(
            y_true, [1 if p >= 0.5 else 0 for p in y_ml]
        )
        ml_m["roc_curve"] = roc_curve_points(y_true, y_ml, n=11)
        model = eng.models.get(did)
        ml_m["feature_importance"] = (
            model.feature_importance(FEATURE_COLUMNS, top_k=8) if model else []
        )

        per_disease[did] = {"rule_based": rule_m, "ml": ml_m}
        all_rule_auc.append(rule_m["roc_auc"])
        all_ml_auc.append(ml_m["roc_auc"])

    n = max(1, len(lat_ml))
    report = {
        "model": "disease_risk_predictor",
        "backend": eng.backend_name,
        "n_eval": len(rows),
        "macro_roc_auc": {
            "rule_based": float(np.mean(all_rule_auc)),
            "ml": float(np.mean(all_ml_auc)),
        },
        "latency_ms": {
            "rule_mean": sum(lat_rule) / max(1, len(lat_rule)),
            "ml_mean": sum(lat_ml) / n,
        },
        "per_disease": per_disease,
        "safety": {
            "disclaimer_required": True,
            "diagnosis_forbidden": True,
        },
        "notes": [
            "Synthetic educational data only — not MIMIC/NHANES weights.",
            "Primary architecture XGBoost when installed; else LightGBM/sklearn_gb.",
            "Outputs are risk probabilities, never diagnoses.",
        ],
    }
    out = resolve_path(cfg["paths"]["evaluation_out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "backend": report["backend"],
        "macro_roc_auc": report["macro_roc_auc"],
        "latency_ms": report["latency_ms"],
        "n_eval": report["n_eval"],
        "written": str(out),
    }, indent=2))
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=None)
    args = p.parse_args()
    evaluate(args.config)


if __name__ == "__main__":
    main()
