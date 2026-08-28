"""Evaluation report writer — JSON + human-readable summary."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_METRIC_KEYS = (
    "precision",
    "recall",
    "f1",
    "accuracy",
    "latency_ms",
    "model_size_bytes",
    "memory_mib",
    "inference_time_ms",
)


@dataclass
class EvaluationReport:
    """
    Canonical evaluation artifact for every models/*/evaluate.py script.

    Required metrics (fill unknowns with 0.0 / null-safe defaults):
      precision, recall, f1, accuracy,
      latency_ms, model_size_bytes, memory_mib, inference_time_ms
    """

    model_name: str
    model_version: str = "baseline"
    dataset: str = "unknown"
    metrics: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def ensure_required(self) -> None:
        """Fill any missing required metric keys with 0.0 (explicit gaps)."""
        for key in REQUIRED_METRIC_KEYS:
            self.metrics.setdefault(key, 0.0)

    def to_dict(self) -> dict[str, Any]:
        self.ensure_required()
        return asdict(self)

    def write_json(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return out

    def summary_lines(self) -> list[str]:
        self.ensure_required()
        m = self.metrics
        return [
            f"model={self.model_name} version={self.model_version} dataset={self.dataset}",
            f"  precision={m.get('precision')} recall={m.get('recall')} "
            f"f1={m.get('f1')} accuracy={m.get('accuracy')}",
            f"  latency_ms={m.get('latency_ms')} inference_time_ms={m.get('inference_time_ms')}",
            f"  model_size_bytes={m.get('model_size_bytes')} memory_mib={m.get('memory_mib')}",
            f"  created_at={self.created_at}",
        ]

    def print_summary(self) -> None:
        print("\n".join(self.summary_lines()))
