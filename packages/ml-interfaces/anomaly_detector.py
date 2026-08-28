"""AnomalyDetector — personal time-series trend + anomaly signals."""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from .types import AnomalyDetectionResult


@runtime_checkable
class AnomalyDetector(Protocol):
    """
    Detect unusual change vs a user's own short lab series.

    Default: z-score trend + statistical monitor (causal z ∨ CUSUM).
    Future: USE_OUTLIER_MODEL=1 → learned model under models/anomaly/.
    """

    def detect(
        self,
        test_name: str,
        data_points: list[tuple[date, float]],
        unit: str | None = None,
        reference_range_low: float | None = None,
        reference_range_high: float | None = None,
    ) -> AnomalyDetectionResult:
        ...
