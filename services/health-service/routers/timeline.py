"""
health-service/routers/timeline.py

Health timeline endpoints.

GET /timeline              → summary: one entry per test_name (latest value + count)
GET /timeline/{test_name}  → full chronological history for a specific metric
GET /timeline/{test_name}/anomaly → history + AI anomaly/trend detection

owner_id always comes from the X-User-ID header set by the API gateway.
"""

import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared_utils import get_logger

from ..core.config import Settings, get_settings
from ..db.repositories.timeline_repository import TimelineRepository
from ..db.session import get_db

logger = get_logger(__name__)
router = APIRouter(prefix="/timeline", tags=["timeline"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TimelineSummaryItem(BaseModel):
    test_name: str
    unit: str | None
    latest_date: str | None
    latest_value_numeric: float | None
    latest_value_text: str | None
    data_point_count: int


class TimelineEventOut(BaseModel):
    id: str
    test_name: str
    date_of_test: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    source_report_id: str


class AnomalyAnalysisOut(BaseModel):
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
    history: list[TimelineEventOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_owner_id(x_user_id: Annotated[str | None, Header()] = None) -> uuid.UUID:
    """Extract and validate owner_id from X-User-ID header (set by API gateway)."""
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-ID header")
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-ID")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[TimelineSummaryItem])
async def get_timeline_summary(
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TimelineSummaryItem]:
    """
    Returns a summary of the user's full health timeline:
    one entry per distinct test_name with the latest value, date, and
    total number of data points recorded.

    This is the main dashboard view for the health timeline feature.
    """
    repo = TimelineRepository(db)
    summary = await repo.get_timeline_summary(owner_id)
    return [TimelineSummaryItem(**item) for item in summary]


@router.get("/{test_name}/anomaly", response_model=AnomalyAnalysisOut)
async def get_test_anomaly(
    test_name: str,
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnomalyAnalysisOut:
    """
    Full history for a metric plus AI-service trend/anomaly analysis.
    Declared before /{test_name} so FastAPI matches the static suffix.
    """
    repo = TimelineRepository(db)
    events = await repo.list_events_for_test(owner_id, test_name)
    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No timeline data found for test '{test_name}'",
        )

    history = [
        TimelineEventOut(
            id=str(e.id),
            test_name=e.test_name,
            date_of_test=e.date_of_test.isoformat(),
            value_numeric=float(e.value_numeric) if e.value_numeric is not None else None,
            value_text=e.value_text,
            unit=e.unit,
            source_report_id=str(e.source_report_id),
        )
        for e in events
    ]

    points = [
        {"date": h.date_of_test, "value": h.value_numeric}
        for h in history
        if h.value_numeric is not None
    ]
    unit = next((h.unit for h in history if h.unit), None)

    headers = {}
    if settings.internal_service_key:
        headers["X-Internal-Key"] = settings.internal_service_key

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ai_service_url.rstrip('/')}/anomaly/detect",
                json={"test_name": test_name, "unit": unit, "data_points": points},
                headers=headers,
            )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("Anomaly proxy failed for test=%s: %s", test_name, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Anomaly service unavailable") from exc

    return AnomalyAnalysisOut(
        test_name=data["test_name"],
        trend=data["trend"],
        anomaly_score=float(data["anomaly_score"]),
        is_anomaly=bool(data["is_anomaly"]),
        z_score=data.get("z_score"),
        out_of_range_streak=int(data.get("out_of_range_streak", 0)),
        method=data.get("method", "unknown"),
        data_points_used=int(data.get("data_points_used", len(points))),
        summary_en=data["summary_en"],
        summary_hi=data["summary_hi"],
        history=history,
    )


@router.get("/{test_name}", response_model=list[TimelineEventOut])
async def get_test_history(
    test_name: str,
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TimelineEventOut]:
    """
    Returns the full chronological history (oldest first) for a single
    lab metric (e.g., "Haemoglobin", "Total Cholesterol").
    """
    repo = TimelineRepository(db)
    events = await repo.list_events_for_test(owner_id, test_name)

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No timeline data found for test '{test_name}'",
        )

    return [
        TimelineEventOut(
            id=str(e.id),
            test_name=e.test_name,
            date_of_test=e.date_of_test.isoformat(),
            value_numeric=float(e.value_numeric) if e.value_numeric is not None else None,
            value_text=e.value_text,
            unit=e.unit,
            source_report_id=str(e.source_report_id),
        )
        for e in events
    ]
