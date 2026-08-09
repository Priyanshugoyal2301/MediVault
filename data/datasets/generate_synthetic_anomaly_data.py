"""
data/datasets/generate_synthetic_anomaly_data.py

Generates a synthetic health-metric dataset, runs the anomaly detector,
and evaluates Precision, Recall, F1, and False-Alert Rate.

Usage:
    python data/datasets/generate_synthetic_anomaly_data.py

Results are printed to stdout AND appended to docs/DEV_LOG.md.

Dataset design:
  - 200 synthetic patients, each with 6-10 CBC readings over 12 months.
  - 20% of patients have a deliberately injected anomalous spike/dip.
  - Ground truth: is_anomaly=True if the final reading was injected.
  - Model is evaluated at the patient level (one prediction per patient).
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure the project root is on sys.path so we can import from services/
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Install the same HyphenatedModuleFinder used in conftest.py so that
# `services.ai_service` resolves to `services/ai-service/` at runtime.
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

from services.ai_service.anomaly.detector import detect  # noqa: E402  # type: ignore[import]

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
random.seed(42)

# ---------------------------------------------------------------------------
# Dataset generation parameters
# ---------------------------------------------------------------------------
N_PATIENTS = 200
ANOMALY_FRACTION = 0.20          # 20% of patients have an injected anomaly
N_READINGS_RANGE = (6, 10)

# Haemoglobin reference: mean=13.5 g/dL, std=1.2
HB_MEAN = 13.5
HB_STD = 1.2
ANOMALY_SPIKE = 3.5              # sigma units above/below normal for injected anomaly

TEST_NAME = "Haemoglobin"
UNIT = "g/dL"


def _gen_dates(n: int) -> list[date]:
    """Generate n evenly-ish spaced dates over the past 12 months."""
    start = date.today() - timedelta(days=365)
    step = 365 // (n + 1)
    return [start + timedelta(days=step * (i + 1)) for i in range(n)]


def _gen_patient(inject_anomaly: bool) -> list[tuple[date, float]]:
    n = random.randint(*N_READINGS_RANGE)
    dates = _gen_dates(n)
    values = [round(random.gauss(HB_MEAN, HB_STD), 2) for _ in range(n)]
    if inject_anomaly:
        # Make the last reading a large spike downward (anaemia direction)
        direction = -1  # drop
        values[-1] = round(HB_MEAN + direction * ANOMALY_SPIKE * HB_STD, 2)
    return list(zip(dates, values))


# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------

def run_evaluation() -> dict:
    true_labels: list[bool] = []
    pred_labels: list[bool] = []

    n_anomaly = int(N_PATIENTS * ANOMALY_FRACTION)
    labels_shuffled = [True] * n_anomaly + [False] * (N_PATIENTS - n_anomaly)
    random.shuffle(labels_shuffled)

    for gt in labels_shuffled:
        data_points = _gen_patient(inject_anomaly=gt)
        result = detect(test_name=TEST_NAME, data_points=data_points, unit=UNIT)
        true_labels.append(gt)
        pred_labels.append(result.is_anomaly)

    # Metrics
    tp = sum(1 for t, p in zip(true_labels, pred_labels) if t and p)
    fp = sum(1 for t, p in zip(true_labels, pred_labels) if not t and p)
    fn = sum(1 for t, p in zip(true_labels, pred_labels) if t and not p)
    tn = sum(1 for t, p in zip(true_labels, pred_labels) if not t and not p)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    false_alert_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "n_patients": N_PATIENTS,
        "anomaly_fraction": ANOMALY_FRACTION,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_alert_rate": round(false_alert_rate, 4),
    }


def _append_to_dev_log(metrics: dict) -> None:
    dev_log = ROOT / "docs" / "DEV_LOG.md"
    today = date.today().isoformat()
    entry = f"""
---

## [{today}] Feature 2 Anomaly Detection — Synthetic Evaluation

**Dataset**: {metrics['n_patients']} synthetic patients, {int(metrics['anomaly_fraction']*100)}% with injected anomalies (Haemoglobin, σ={ANOMALY_SPIKE} spike).

| Metric            | Value   |
|-------------------|---------|
| Precision         | {metrics['precision']:.4f} |
| Recall            | {metrics['recall']:.4f} |
| F1 Score          | {metrics['f1']:.4f} |
| False-Alert Rate  | {metrics['false_alert_rate']:.4f} |
| TP / FP / FN / TN | {metrics['tp']} / {metrics['fp']} / {metrics['fn']} / {metrics['tn']} |

Model: Z-score baseline (|z|>2 → anomaly) + IsolationForest (contamination=0.1) with zscore fallback for <5 data points.
"""
    with open(dev_log, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[OK] Appended evaluation results to {dev_log}")


if __name__ == "__main__":
    print("Running synthetic anomaly detection evaluation…\n")
    metrics = run_evaluation()
    print(f"  Patients: {metrics['n_patients']}")
    print(f"  Anomaly fraction: {int(metrics['anomaly_fraction']*100)}%")
    print(f"  Precision:        {metrics['precision']:.4f}")
    print(f"  Recall:           {metrics['recall']:.4f}")
    print(f"  F1:               {metrics['f1']:.4f}")
    print(f"  False-Alert Rate: {metrics['false_alert_rate']:.4f}")
    print(f"  TP/FP/FN/TN:      {metrics['tp']}/{metrics['fp']}/{metrics['fn']}/{metrics['tn']}")
    _append_to_dev_log(metrics)
