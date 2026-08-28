"""Evaluate entrypoint for models/anomaly — scaffold only.

Must report metrics required by packages.ml_eval.EvaluationReport:
  precision, recall, f1, accuracy, latency_ms, model_size_bytes,
  memory_mib, inference_time_ms
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.ml_eval import EvaluationReport  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate anomaly model (scaffold)")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument(
        "--out",
        default=str(ROOT / "datasets" / "evaluation" / "anomaly_latest.json"),
    )
    args = parser.parse_args()

    report = EvaluationReport(
        model_name="anomaly",
        model_version="scaffold",
        dataset="none",
        metrics={
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "accuracy": 0.0,
            "latency_ms": 0.0,
            "model_size_bytes": 0,
            "memory_mib": 0.0,
            "inference_time_ms": 0.0,
        },
        notes="Scaffold evaluation — no model trained yet.",
    )
    out = report.write_json(args.out)
    report.print_summary()
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
