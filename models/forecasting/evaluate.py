"""Evaluate biomarker forecasting quality."""

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

    from models.forecasting.config_loader import load_config, resolve_path
    from models.forecasting.dataset import load_eval_patients, supervised_from_patients
    from models.forecasting.feature_engineering import trend_from_values
    from models.forecasting.infer import BiomarkerForecastEngine
    from models.forecasting.metrics import (
        interval_coverage,
        mae,
        mape,
        r2_score,
        residual_calibration_error,
        rmse,
        trend_accuracy,
    )

    cfg = load_config(config_path, validate=True)
    data_dir = resolve_path(cfg["paths"]["train_data"])
    patients = load_eval_patients(data_dir)
    horizon = int(cfg.get("default_horizon_days") or 180)
    eng = BiomarkerForecastEngine(cfg, auto_train_if_missing=True)

    X_map, y_map = supervised_from_patients(patients, horizon_days=horizon)
    per_bio = {}
    all_mae = []
    all_rmse = []
    lat = []

    for bid, X in X_map.items():
        y = y_map[bid]
        model = eng.models.get(bid)
        if model is None or len(y) == 0:
            continue
        t0 = time.perf_counter()
        pred = model.predict(X)
        lat.append((time.perf_counter() - t0) * 1000.0 / max(1, len(y)))
        std = eng.residual_std.get(bid, 1.0)
        z = float(cfg.get("pi_z") or 1.645)
        lo = pred - z * std
        hi = pred + z * std
        true_dirs = []
        pred_dirs = []
        for i in range(len(y)):
            # crude current = lag1 feature index in POINT_FEATURE_NAMES is 0? value is first; lag1 is position
            # use feature column 'value' index 0 as current proxy
            curr = float(X[i, 0])
            td, _ = trend_from_values(curr, float(y[i]), eps=0.01)
            pd, _ = trend_from_values(curr, float(pred[i]), eps=0.01)
            true_dirs.append(td)
            pred_dirs.append(pd)
        m = {
            "n": int(len(y)),
            "mae": mae(y, pred),
            "rmse": rmse(y, pred),
            "mape": mape(y, pred),
            "r2": r2_score(y, pred),
            "pi_coverage": interval_coverage(y, lo, hi),
            "calibration_error": residual_calibration_error(y, pred),
            "trend_accuracy": trend_accuracy(true_dirs, pred_dirs),
        }
        per_bio[bid] = m
        all_mae.append(m["mae"])
        all_rmse.append(m["rmse"])

    # End-to-end smoke latency on first patient
    if patients:
        t0 = time.perf_counter()
        eng.forecast(patients[0].get("history") or [], horizon_days=horizon)
        e2e_ms = (time.perf_counter() - t0) * 1000
    else:
        e2e_ms = 0.0

    report = {
        "model": "biomarker_forecaster",
        "backend": eng.backend_name,
        "horizon_days": horizon,
        "n_patients_eval": len(patients),
        "macro_mae": float(np.mean(all_mae)) if all_mae else None,
        "macro_rmse": float(np.mean(all_rmse)) if all_rmse else None,
        "latency_ms_per_pred_mean": float(np.mean(lat)) if lat else None,
        "e2e_forecast_ms": e2e_ms,
        "per_biomarker": per_bio,
        "notes": [
            "Synthetic longitudinal data only.",
            "Primary LightGBM; XGBoost fallback; linear baseline; LSTM/Transformer stubbed.",
            "Forecasts are non-diagnostic.",
        ],
    }
    out = resolve_path(cfg["paths"]["evaluation_out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "backend": report["backend"],
                "macro_mae": report["macro_mae"],
                "macro_rmse": report["macro_rmse"],
                "e2e_forecast_ms": report["e2e_forecast_ms"],
                "biomarkers": list(per_bio.keys()),
                "written": str(out),
            },
            indent=2,
        )
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=None)
    args = p.parse_args()
    evaluate(args.config)


if __name__ == "__main__":
    main()
