"""Evaluate health score model."""

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

    from models.explainability import shap_available
    from models.health_score.config_loader import load_config, resolve_path
    from models.health_score.dataset import load_eval_rows, rows_to_matrices
    from models.health_score.infer import HealthScoreEngine
    from models.health_score.metrics import (
        feature_stability,
        mae,
        mape,
        r2_score,
        residual_calibration_error,
        rmse,
    )
    from models.health_score.schema import FEATURE_COLUMNS

    cfg = load_config(config_path, validate=True)
    data_dir = resolve_path(cfg["paths"]["train_data"])
    rows = load_eval_rows(data_dir)
    eng = HealthScoreEngine(cfg, auto_train_if_missing=True)
    X, y, _ = rows_to_matrices(rows)
    assert eng.model is not None
    t0 = time.perf_counter()
    pred = eng.model.predict(X)
    batch_ms = (time.perf_counter() - t0) * 1000

    # stability: importance train vs half-split
    mid = max(1, len(X) // 2)
    imp_full = eng.model.feature_importances(len(FEATURE_COLUMNS))
    try:
        eng.model.fit(X[:mid], y[:mid])
        imp_half = eng.model.feature_importances(len(FEATURE_COLUMNS))
        # reload full model
        eng = HealthScoreEngine(cfg, auto_train_if_missing=True)
        stability = feature_stability(imp_full, imp_half)
    except Exception:
        stability = None

    # e2e score + explain
    sample = rows[0] if rows else {"history": []}
    t1 = time.perf_counter()
    out = eng.score(sample.get("history") or [], demographics=sample.get("demographics"))
    e2e_ms = (time.perf_counter() - t1) * 1000

    report = {
        "model": "personalized_health_score",
        "backend": eng.backend_name,
        "n_eval": int(len(y)),
        "mae": mae(y, pred),
        "rmse": rmse(y, pred),
        "mape": mape(y, pred),
        "r2": r2_score(y, pred),
        "calibration_error": residual_calibration_error(y, pred),
        "feature_stability": stability,
        "batch_predict_ms": batch_ms,
        "latency_ms_per_row": batch_ms / max(1, len(y)),
        "e2e_score_explain_ms": e2e_ms,
        "shap_library_available": shap_available(),
        "explanation_method_sample": out.get("explanation_method"),
        "sample_score": out.get("score"),
        "sample_band": out.get("risk_band"),
        "sample_confidence": out.get("confidence"),
        "global_importance_top": eng.global_importance[:10],
        "notes": [
            "Synthetic targets from heuristic formula + noise.",
            "Primary XGBoost; LightGBM fallback; linear baseline.",
            "SHAP TreeExplainer when installed; centered fallback otherwise.",
            "Non-diagnostic health orientation score only.",
        ],
    }
    out_path = resolve_path(cfg["paths"]["evaluation_out"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "backend": report["backend"],
                "mae": report["mae"],
                "rmse": report["rmse"],
                "r2": report["r2"],
                "e2e_score_explain_ms": report["e2e_score_explain_ms"],
                "shap_available": report["shap_library_available"],
                "written": str(out_path),
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
