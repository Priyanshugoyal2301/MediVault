"""Evaluate Isolation Forest vs LOF vs Robust Z."""

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
    from models.anomaly_detection.backends import create_backend
    from models.anomaly_detection.config_loader import load_config, resolve_path
    from models.anomaly_detection.dataset import load_eval_rows, load_train_rows, rows_to_matrix
    from models.anomaly_detection.infer import LabAnomalyEngine
    from models.anomaly_detection.metrics import (
        false_positive_rate,
        pr_auc,
        precision_at_k,
        recall_at_k,
        roc_auc,
    )

    cfg = load_config(config_path, validate=True)
    data_dir = resolve_path(cfg["paths"]["train_data"])
    train_rows = load_train_rows(data_dir)
    eval_rows = load_eval_rows(data_dir)
    normal_train = [r for r in train_rows if not int(r.get("is_anomaly") or 0)] or train_rows
    Xn, _, impute, medians, iqrs = rows_to_matrix(normal_train)
    Xe, ye, _, _, _ = rows_to_matrix(
        eval_rows, medians=medians, iqrs=iqrs, impute=impute
    )

    thr = float(cfg.get("score_threshold") or 0.55)
    comparison = {}
    for kind in ("isolation_forest", "lof", "robust_z"):
        m = create_backend(kind, seed=int(cfg.get("seed") or 42), contamination=float(cfg.get("contamination") or 0.08))
        t0 = time.perf_counter()
        m.fit(Xn)
        fit_ms = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        scores = m.score_samples(Xe)
        inf_ms = (time.perf_counter() - t1) * 1000
        comparison[kind] = {
            "precision_at_20": precision_at_k(ye, scores, k=20),
            "recall_at_20": recall_at_k(ye, scores, k=20),
            "roc_auc": roc_auc(ye, scores),
            "pr_auc": pr_auc(ye, scores),
            "fpr_at_threshold": false_positive_rate(ye, scores, thr),
            "fit_ms": fit_ms,
            "infer_batch_ms": inf_ms,
            "latency_ms_per_row": inf_ms / max(1, len(ye)),
        }

    eng = LabAnomalyEngine(cfg, auto_train_if_missing=True)
    # e2e series detect
    from datetime import date, timedelta

    pts = [(date(2023, 1, 1) + timedelta(days=30 * i), 1.0 + 0.4 * i) for i in range(5)]
    t2 = time.perf_counter()
    out = eng.detect_series("Creatinine", pts)
    e2e_ms = (time.perf_counter() - t2) * 1000

    report = {
        "model": "lab_anomaly_detector",
        "active_backend": eng.backend_name,
        "n_eval": int(len(ye)),
        "n_pos": int(ye.sum()),
        "comparison": comparison,
        "e2e_series_detect_ms": e2e_ms,
        "sample_series": {
            "is_anomaly": out.get("is_anomaly"),
            "anomaly_probability": out.get("anomaly_probability"),
            "category": out.get("anomaly_category"),
            "method": out.get("method"),
        },
        "notes": [
            "Synthetic labels for ROC/PR only.",
            "Primary Isolation Forest; LOF fallback; Robust Z baseline.",
            "Non-diagnostic: 'Anomalous laboratory pattern' language only.",
        ],
    }
    out_path = resolve_path(cfg["paths"]["evaluation_out"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "active": report["active_backend"],
                "if_prauc": comparison["isolation_forest"].get("pr_auc"),
                "lof_prauc": comparison["lof"].get("pr_auc"),
                "z_prauc": comparison["robust_z"].get("pr_auc"),
                "e2e_ms": e2e_ms,
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
