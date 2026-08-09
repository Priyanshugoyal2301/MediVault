"""
health-service/routers/timeline.py

Health timeline endpoints.

GET /timeline              → summary: one entry per test_name (latest value + count)
GET /timeline/{test_name}  → full chronological history for a specific metric

owner_id always comes from the X-User-ID header set by the API gateway.
All queries are owner-scoped via TimelineRepository (subclass of ScopedRepository).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared_utils import get_logger

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


@router.get("/{test_name}", response_model=list[TimelineEventOut])
async def get_test_history(
    test_name: str,
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TimelineEventOut]:
    """
    Returns the full chronological history (oldest first) for a single
    lab metric (e.g., "Haemoglobin", "Total Cholesterol").

    Returns 404 if no events found for that test_name (could be wrong name
    or belongs to a different owner — no enumeration).
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
