"""
Shared result DTOs for ml-interfaces.

These are *contract* types for training / evaluation harnesses and future
adapters. Live routers may continue to use service-local dataclasses that
mirror this shape (zero API change during Phase 0 infrastructure).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass
class ParsedField:
    """One structured lab value extracted from a document."""

    test_name: str
    panel: str | None = None
    value_numeric: Decimal | float | None = None
    value_text: str | None = None
    unit: str | None = None
    reference_range_low: Decimal | float | None = None
    reference_range_high: Decimal | float | None = None
    reference_range_text: str | None = None
    confidence: float | None = None
    raw_span: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_name": self.test_name,
            "panel": self.panel,
            "value_numeric": self.value_numeric,
            "value_text": self.value_text,
            "unit": self.unit,
            "reference_range_low": self.reference_range_low,
            "reference_range_high": self.reference_range_high,
            "reference_range_text": self.reference_range_text,
            "confidence": self.confidence,
            "raw_span": self.raw_span,
        }


@dataclass(frozen=True)
class AnomalyDetectionResult:
    """Personal-series anomaly / trend detection result."""

    test_name: str
    trend: str
    anomaly_score: float
    is_anomaly: bool
    z_score: float | None
    out_of_range_streak: int
    method: str
    data_points_used: int
    summary_en: str
    summary_hi: str
    # Phase 7 optional (defaults keep API/response BC when unused)
    anomaly_probability: float | None = None
    anomaly_category: str = ""
    confidence: float | None = None
    top_contributors: tuple[str, ...] = ()
    disclaimer_en: str = (
        "Anomalous laboratory pattern detection only. "
        "This is not a medical diagnosis."
    )


@dataclass(frozen=True)
class RetrievedDocument:
    """A single knowledge or user-data chunk from retrieval."""

    text: str
    source: str
    source_url: str | None = None
    score: float = 0.0
    is_user_data: bool = False


@dataclass(frozen=True)
class QualityCheckResult:
    """Image / PDF quality assessment before OCR."""

    ok: bool
    score: float
    reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskPredictionResult:
    """Non-diagnostic population-style risk signal."""

    risk_score: float | None
    risk_band: str  # "unavailable" | "low" | "moderate" | "high" | "elevated" | ...
    drivers: tuple[str, ...] = ()
    summary_en: str = ""
    summary_hi: str = ""
    method: str = "unavailable"
    # Phase 4 optional multi-condition details (default empty — BC for callers)
    conditions: tuple[dict[str, Any], ...] = ()
    disclaimer_en: str = (
        "Risk estimate only. This is not a medical diagnosis. "
        "For informational purposes only."
    )


@dataclass(frozen=True)
class HealthScoreResult:
    """Aggregate health orientation score over recent metrics (non-diagnostic)."""

    score: float | None
    level: str  # unavailable | excellent | good | fair | watch | elevated
    components: dict[str, float] = field(default_factory=dict)
    summary_en: str = ""
    summary_hi: str = ""
    method: str = "unavailable"
    confidence: float | None = None
    risk_band: str = ""  # human label e.g. Good
    positive_contributors: tuple[str, ...] = ()
    negative_contributors: tuple[str, ...] = ()
    top_features: tuple[dict[str, Any], ...] = ()
    global_importance: tuple[dict[str, Any], ...] = ()
    explanation_method: str = "unavailable"
    disclaimer_en: str = (
        "Health score estimate only. This is not a medical diagnosis or "
        "treatment recommendation. For informational purposes only."
    )


@dataclass(frozen=True)
class BiomarkerForecast:
    """Single biomarker future prediction (non-diagnostic)."""

    biomarker: str
    current_value: float | None
    predicted_value: float | None
    lower_bound: float | None
    upper_bound: float | None
    confidence: float
    trend_direction: str  # increasing | decreasing | stable | unknown
    expected_trend: str
    horizon_days: int
    unit: str | None = None
    method: str = "unavailable"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BiomarkerForecastBatch:
    """Batch of biomarker forecasts for one patient history."""

    forecasts: tuple[BiomarkerForecast, ...] = ()
    horizon_days: int = 180
    method: str = "unavailable"
    disclaimer_en: str = (
        "Forecast estimate only. This is not a medical diagnosis or "
        "treatment recommendation. For informational purposes only."
    )
    summary_en: str = ""
    summary_hi: str = ""


# Convenience alias used by anomaly / risk training data schemas
SeriesPoint = tuple[date, float]
