"""AnomalyDetector adapters — statistical default; ML Isolation Forest path."""

from __future__ import annotations

from datetime import date
from typing import Any

from packages.ml_interfaces.types import AnomalyDetectionResult
from packages.shared_utils import get_logger

from ..anomaly.detector import detect

logger = get_logger(__name__)


class StatisticalAnomalyDetector:
    """Production default for AnomalyDetector. Zero behaviour change."""

    def detect(
        self,
        test_name: str,
        data_points: list[tuple[date, float]],
        unit: str | None = None,
        reference_range_low: float | None = None,
        reference_range_high: float | None = None,
    ) -> AnomalyDetectionResult:
        result = detect(
            test_name=test_name,
            data_points=data_points,
            unit=unit,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
        )
        return AnomalyDetectionResult(
            test_name=result.test_name,
            trend=result.trend,
            anomaly_score=result.anomaly_score,
            is_anomaly=result.is_anomaly,
            z_score=result.z_score,
            out_of_range_streak=result.out_of_range_streak,
            method=result.method,
            data_points_used=result.data_points_used,
            summary_en=result.summary_en,
            summary_hi=result.summary_hi,
        )


class MLAnomalyDetector:
    """Phase 7 unsupervised Isolation Forest path (single-series API)."""

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from models.anomaly_detection.infer import LabAnomalyEngine

            engine = LabAnomalyEngine()
        self._engine = engine

    def detect(
        self,
        test_name: str,
        data_points: list[tuple[date, float]],
        unit: str | None = None,
        reference_range_low: float | None = None,
        reference_range_high: float | None = None,
    ) -> AnomalyDetectionResult:
        raw = self._engine.detect_series(
            test_name,
            data_points,
            unit=unit,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
        )
        return AnomalyDetectionResult(
            test_name=str(raw["test_name"]),
            trend=str(raw["trend"]),
            anomaly_score=float(raw["anomaly_score"]),
            is_anomaly=bool(raw["is_anomaly"]),
            z_score=raw.get("z_score"),
            out_of_range_streak=int(raw.get("out_of_range_streak") or 0),
            method=str(raw.get("method") or "ml_anomaly"),
            data_points_used=int(raw.get("data_points_used") or 0),
            summary_en=str(raw.get("summary_en") or ""),
            summary_hi=str(raw.get("summary_hi") or ""),
            anomaly_probability=raw.get("anomaly_probability"),
            anomaly_category=str(raw.get("anomaly_category") or ""),
            confidence=raw.get("confidence"),
            top_contributors=tuple(raw.get("top_contributors") or ()),
            disclaimer_en=str(raw.get("disclaimer_en") or ""),
        )


class FallbackAnomalyDetector:
    """ML primary → statistical on failure (never hard-fail)."""

    def __init__(
        self,
        primary: Any,
        fallback: StatisticalAnomalyDetector | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or StatisticalAnomalyDetector()
        self.last_path = "unset"

    def detect(
        self,
        test_name: str,
        data_points: list[tuple[date, float]],
        unit: str | None = None,
        reference_range_low: float | None = None,
        reference_range_high: float | None = None,
    ) -> AnomalyDetectionResult:
        try:
            r = self.primary.detect(
                test_name,
                data_points,
                unit=unit,
                reference_range_low=reference_range_low,
                reference_range_high=reference_range_high,
            )
            self.last_path = "ml"
            return r
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ML anomaly detector failed (%s); falling back to statistical",
                type(exc).__name__,
            )
            self.last_path = "fallback"
            return self.fallback.detect(
                test_name,
                data_points,
                unit=unit,
                reference_range_low=reference_range_low,
                reference_range_high=reference_range_high,
            )
