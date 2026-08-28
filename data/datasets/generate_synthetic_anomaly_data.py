"""
data/datasets/generate_synthetic_anomaly_data.py

Synthetic Hb series evaluation + ablation for Plan B anomaly monitor.

Usage:
    python data/datasets/generate_synthetic_anomaly_data.py
    python data/datasets/generate_synthetic_anomaly_data.py --no-devlog

Compares:
  - statistical_monitor (production Plan B)
  - causal_z_only / pct_delta_only / cusum_only ablations
  - legacy IsolationForest (eval-only, not in production path)
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import importlib.util


class _HyphenatedFinder:
    _DIRS = {"services": ROOT / "services", "packages": ROOT / "packages"}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        parts = fullname.split(".")
        ns = parts[0]
        if ns not in cls._DIRS or len(parts) < 2:
            return None
        base = cls._DIRS[ns]
        pkg_dir = base / parts[1].replace("_", "-")
        if not pkg_dir.exists():
            return None
        rest = parts[2:]
        if not rest:
            init = pkg_dir / "__init__.py"
            if init.exists():
                return importlib.util.spec_from_file_location(
                    fullname, str(init), submodule_search_locations=[str(pkg_dir)]
                )
            return importlib.util.spec_from_file_location(
                fullname, None, submodule_search_locations=[str(pkg_dir)]
            )
        tp = pkg_dir.joinpath(*rest)
        init = tp / "__init__.py"
        py = tp.with_suffix(".py")
        if tp.is_dir() and init.exists():
            return importlib.util.spec_from_file_location(
                fullname, str(init), submodule_search_locations=[str(tp)]
            )
        if py.exists():
            return importlib.util.spec_from_file_location(fullname, str(py))
        return None


if not any(type(f).__name__ == "_HyphenatedFinder" for f in sys.meta_path):
    sys.meta_path.insert(0, _HyphenatedFinder)

from services.ai_service.anomaly.model import score_anomaly  # noqa: E402

random.seed(42)

N_PATIENTS = 200
ANOMALY_FRACTION = 0.20
N_READINGS_RANGE = (6, 10)
HB_MEAN = 13.5
HB_STD = 1.2
ANOMALY_SPIKE = 3.5
TEST_NAME = "Haemoglobin"
UNIT = "g/dL"


def _gen_dates(n: int) -> list[date]:
    start = date.today() - timedelta(days=365)
    step = 365 // (n + 1)
    return [start + timedelta(days=step * (i + 1)) for i in range(n)]


def _gen_patient(inject_anomaly: bool) -> list[tuple[date, float]]:
    n = random.randint(*N_READINGS_RANGE)
    dates = _gen_dates(n)
    values = [round(random.gauss(HB_MEAN, HB_STD), 2) for _ in range(n)]
    if inject_anomaly:
        values[-1] = round(HB_MEAN - ANOMALY_SPIKE * HB_STD, 2)
    return list(zip(dates, values))


def _metrics(true_labels: list[bool], pred_labels: list[bool]) -> dict:
    tp = sum(1 for t, p in zip(true_labels, pred_labels) if t and p)
    fp = sum(1 for t, p in zip(true_labels, pred_labels) if not t and p)
    fn = sum(1 for t, p in zip(true_labels, pred_labels) if t and not p)
    tn = sum(1 for t, p in zip(true_labels, pred_labels) if not t and not p)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    far = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_alert_rate": round(far, 4),
    }


def _legacy_isolation_forest(data_points: list[tuple[date, float]]) -> bool:
    """Eval-only baseline — not used in production."""
    if len(data_points) < 5:
        return False
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return False
    values = np.array([v for _, v in data_points]).reshape(-1, 1)
    clf = IsolationForest(
        n_estimators=100, contamination=0.1, random_state=42
    )
    clf.fit(values)
    return bool(clf.predict(values[-1:].reshape(1, -1))[0] == -1)


def _ablation_predict(
    data_points: list[tuple[date, float]], mode: str
) -> bool:
    result = score_anomaly(data_points)
    if mode == "statistical_monitor":
        return result.is_anomaly
    if mode == "causal_z_only":
        return "causal_z" in result.triggers or (
            result.method == "zscore_fallback" and result.is_anomaly
        )
    if mode == "pct_delta_only":
        return "pct_delta" in result.triggers
    if mode == "cusum_only":
        return "cusum" in result.triggers
    if mode == "legacy_isolation_forest":
        return _legacy_isolation_forest(data_points)
    raise ValueError(mode)


def run_evaluation() -> dict:
    n_anomaly = int(N_PATIENTS * ANOMALY_FRACTION)
    labels_shuffled = [True] * n_anomaly + [False] * (N_PATIENTS - n_anomaly)
    random.shuffle(labels_shuffled)

    series_list = [_gen_patient(gt) for gt in labels_shuffled]
    modes = [
        "statistical_monitor",
        "causal_z_only",
        "pct_delta_only",
        "cusum_only",
        "legacy_isolation_forest",
    ]
    out: dict = {
        "n_patients": N_PATIENTS,
        "anomaly_fraction": ANOMALY_FRACTION,
        "methods": {},
    }
    for mode in modes:
        preds = [_ablation_predict(s, mode) for s in series_list]
        out["methods"][mode] = _metrics(labels_shuffled, preds)

    # Primary = production method
    primary = out["methods"]["statistical_monitor"]
    out.update(primary)
    out["model"] = "statistical_monitor"
    return out


def _append_to_dev_log(metrics: dict) -> None:
    dev_log = ROOT / "docs" / "DEV_LOG.md"
    today = date.today().isoformat()
    rows = []
    for name, m in metrics["methods"].items():
        rows.append(
            f"| {name} | {m['precision']:.4f} | {m['recall']:.4f} | "
            f"{m['f1']:.4f} | {m['false_alert_rate']:.4f} | "
            f"{m['tp']}/{m['fp']}/{m['fn']}/{m['tn']} |"
        )
    entry = f"""
---

## [{today}] Plan B Anomaly — Synthetic Evaluation + Ablation

**Dataset**: {metrics['n_patients']} synthetic patients, {int(metrics['anomaly_fraction']*100)}% with injected Hb anomalies (σ={ANOMALY_SPIKE} spike on last point). Leave-last-out / causal scoring.

| Method | Precision | Recall | F1 | FAR | TP/FP/FN/TN |
|--------|-----------|--------|----|-----|-------------|
{chr(10).join(rows)}

Production model: `statistical_monitor` (causal z + %Δ + CUSUM). IsolationForest retained only as eval baseline.
"""
    with open(dev_log, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[OK] Appended evaluation results to {dev_log}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-devlog", action="store_true")
    args = parser.parse_args()

    print("Running synthetic anomaly detection evaluation (Plan B)…\n")
    metrics = run_evaluation()
    for name, m in metrics["methods"].items():
        print(f"[{name}]")
        print(f"  Precision: {m['precision']:.4f}  Recall: {m['recall']:.4f}  "
              f"F1: {m['f1']:.4f}  FAR: {m['false_alert_rate']:.4f}  "
              f"TP/FP/FN/TN: {m['tp']}/{m['fp']}/{m['fn']}/{m['tn']}")
    if not args.no_devlog:
        _append_to_dev_log(metrics)
