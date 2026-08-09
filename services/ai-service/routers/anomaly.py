"""
ai-service/routers/anomaly.py

POST /anomaly/detect — Trend and anomaly detection for a health metric.

Accepts a time series of (date, value) pairs for a named lab test and returns:
  - trend direction (rising / falling / stable / insufficient_data)
  - anomaly score [-1, +1]
  - is_anomaly flag
  - bilingual plain-language summary (EN + HI)

This endpoint is called by the health-service when a user requests timeline
analysis for a specific metric. It is an internal service-to-service endpoint.

TONE RULES: No diagnoses, no alarming language. See anomaly/detector.py.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from packages.shared_utils import get_logger

from ..anomaly.detector import DetectionResult, detect

logger = get_logger(__name__)
router = APIRouter(prefix="/anomaly", tags=["anomaly"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class DataPoint(BaseModel):
    date: date
    value: float


class AnomalyDetectRequest(BaseModel):
    test_name: str
    unit: str | None = None
    data_points: list[DataPoint]

    @field_validator("data_points")
    @classmethod
    def at_least_one_point(cls, v: list[DataPoint]) -> list[DataPoint]:
        if len(v) == 0:
            raise ValueError("data_points must contain at least one entry")
        return v

    @field_validator("test_name")
    @classmethod
    def test_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("test_name must not be empty")
        return v.strip()


class AnomalyDetectResponse(BaseModel):
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


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/detect", response_model=AnomalyDetectResponse)
async def detect_anomaly(body: AnomalyDetectRequest) -> Any:
    """
    Run trend + anomaly detection on a health metric time series.

    - Requires at least 1 data point (returns insufficient_data for < 3).
    - Sorts data points by date (oldest first) before analysis.
    - Returns bilingual (EN + HI) non-diagnostic plain-language summaries.
    """
    # Sort by date (oldest first) to guarantee correct trend direction
    sorted_points = sorted(body.data_points, key=lambda dp: dp.date)
    pairs: list[tuple[date, float]] = [(dp.date, dp.value) for dp in sorted_points]

    try:
        result: DetectionResult = detect(
            test_name=body.test_name,
            data_points=pairs,
            unit=body.unit,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Anomaly detection failed for test=%s: %s", body.test_name, exc)
        raise HTTPException(status_code=500, detail="Anomaly detection failed") from exc

    logger.info(
        "Anomaly detect: test=%s trend=%s is_anomaly=%s points=%d",
        result.test_name,
        result.trend,
        result.is_anomaly,
        result.data_points_used,
    )

    return AnomalyDetectResponse(
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
