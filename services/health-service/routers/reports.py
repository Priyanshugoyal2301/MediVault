"""
health-service/routers/reports.py

Report upload, retrieval, and deletion.
owner_id always comes from the X-User-ID header set by the API gateway —
never from the request body (where a client could tamper with it).
"""

import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared_utils import get_logger

from ..core.config import Settings, get_settings
from ..db.repositories.report_repository import ReportRepository
from ..db.repositories.timeline_repository import TimelineRepository
from ..db.session import get_db
from ..storage.local_storage import LocalStorage

logger = get_logger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ReportOut(BaseModel):
    id: str
    original_filename: str
    parsed_status: str
    uploaded_at: str


class ReportValueOut(BaseModel):
    id: str
    test_name: str
    panel: str | None
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    reference_range_low: float | None
    reference_range_high: float | None
    reference_range_text: str | None
    date_of_test: str | None
    explanation_en: str | None = None
    explanation_hi: str | None = None


class ReportDetailOut(ReportOut):
    values: list[ReportValueOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_owner_id(x_user_id: Annotated[str | None, Header()] = None) -> uuid.UUID:
    """Extract and validate the owner_id injected by the API gateway."""
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-ID header")
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-ID")


def _get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> LocalStorage:
    return LocalStorage(settings.storage_local_path)


# ---------------------------------------------------------------------------
# Background task: call ai-service to parse the report
# ---------------------------------------------------------------------------

async def _trigger_parse(
    report_id: str,
    owner_id: str,
    storage_path: str,
    mime_type: str,
    locale: str,
    ai_service_url: str,
    db_url: str,
) -> None:
    """
    Calls ai-service POST /parse. Runs as a background task so the upload
    endpoint returns 202 immediately. On failure, logs and marks report as failed.

    NOTE: BackgroundTasks runs in-process after response is sent. This is MVP
    simplicity — see DEV_LOG for the decision to defer a proper job queue.
    """
    from ..db.session import get_db  # local import avoids circular at module level

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ai_service_url}/parse",
                json={
                    "report_id": report_id,
                    "owner_id": owner_id,
                    "storage_path": storage_path,
                    "mime_type": mime_type,
                    "locale": locale,
                },
            )
            response.raise_for_status()
            parse_data = response.json()
            parsed_values: list[dict] = parse_data.get("values", [])
            logger.info("Parse complete: report_id=%s values=%d", report_id, len(parsed_values))

        # Persist extracted values + populate timeline events
        from datetime import date
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine(db_url, echo=False)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            report_repo = ReportRepository(session)
            timeline_repo = TimelineRepository(session)

            # Save parsed values to report_values table
            await report_repo.save_report_values(
                owner_id=uuid.UUID(owner_id),
                report_id=uuid.UUID(report_id),
                parsed_values=parsed_values,
            )

            # Build timeline events from values that have a date_of_test
            timeline_events = []
            for v in parsed_values:
                raw_date = v.get("date_of_test")
                if raw_date is None:
                    continue
                if isinstance(raw_date, str):
                    try:
                        raw_date = date.fromisoformat(raw_date)
                    except ValueError:
                        continue
                timeline_events.append({
                    "test_name": v["test_name"],
                    "date_of_test": raw_date,
                    "value_numeric": v.get("value_numeric"),
                    "value_text": v.get("value_text"),
                    "unit": v.get("unit"),
                })

            if timeline_events:
                await timeline_repo.bulk_create_events(
                    owner_id=uuid.UUID(owner_id),
                    source_report_id=uuid.UUID(report_id),
                    events=timeline_events,
                )
                logger.info(
                    "Timeline populated: report_id=%s events=%d",
                    report_id, len(timeline_events),
                )

            await report_repo.set_parsing_status(
                uuid.UUID(report_id), uuid.UUID(owner_id), "complete"
            )
            await session.commit()
        await engine.dispose()

    except Exception as exc:  # noqa: BLE001
        logger.error("Parse failed for report_id=%s: %s", report_id, type(exc).__name__)
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine(db_url, echo=False)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            repo = ReportRepository(session)
            await repo.set_parsing_status(
                uuid.UUID(report_id), uuid.UUID(owner_id), "failed"
            )
            await session.commit()
        await engine.dispose()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=202, response_model=ReportOut)
async def upload_report(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[LocalStorage, Depends(_get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Upload a medical report (PDF or image). Returns 202 immediately;
    OCR + parsing runs as a background task.
    """
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Allowed: {', '.join(_ALLOWED_MIME_TYPES)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    storage_path = await storage.save(file_bytes, file.filename or "report", str(owner_id))

    repo = ReportRepository(db)
    report = await repo.create_report(
        owner_id=owner_id,
        original_filename=file.filename or "report",
        storage_path=storage_path,
        mime_type=file.content_type,
    )

    logger.info("Report uploaded: report_id=%s owner_id=%s", report.id, owner_id)

    background_tasks.add_task(
        _trigger_parse,
        report_id=str(report.id),
        owner_id=str(owner_id),
        storage_path=storage_path,
        mime_type=file.content_type,
        locale="en-IN",  # TODO: read from user profile in health-service
        ai_service_url=settings.ai_service_url,
        db_url=settings.async_db_url,
    )

    return ReportOut(
        id=str(report.id),
        original_filename=report.original_filename,
        parsed_status=report.parsed_status,
        uploaded_at=report.uploaded_at.isoformat(),
    )


@router.get("", response_model=list[ReportOut])
async def list_reports(
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ReportRepository(db)
    reports = await repo.list_for_owner(owner_id)
    return [
        ReportOut(
            id=str(r.id),
            original_filename=r.original_filename,
            parsed_status=r.parsed_status,
            uploaded_at=r.uploaded_at.isoformat(),
        )
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportDetailOut)
async def get_report(
    report_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ReportRepository(db)
    report = await repo.get_by_id(report_id, owner_id)
    if report is None:
        # 404 for both "not found" and "belongs to another user" — no enumeration
        raise HTTPException(status_code=404, detail="Report not found")

    values = await repo.get_values_for_report(report_id, owner_id)
    return ReportDetailOut(
        id=str(report.id),
        original_filename=report.original_filename,
        parsed_status=report.parsed_status,
        uploaded_at=report.uploaded_at.isoformat(),
        values=[
            ReportValueOut(
                id=str(v.id),
                test_name=v.test_name,
                panel=v.panel,
                value_numeric=float(v.value_numeric) if v.value_numeric is not None else None,
                value_text=v.value_text,
                unit=v.unit,
                reference_range_low=float(v.reference_range_low) if v.reference_range_low is not None else None,
                reference_range_high=float(v.reference_range_high) if v.reference_range_high is not None else None,
                reference_range_text=v.reference_range_text,
                date_of_test=v.date_of_test.isoformat() if v.date_of_test else None,
            )
            for v in values
        ],
    )


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[LocalStorage, Depends(_get_storage)],
):
    """
    Hard delete: removes report + values + timeline events (DB cascade handles
    child rows) + the stored file. Returns 404 for wrong owner (no enumeration).
    """
    repo = ReportRepository(db)
    report = await repo.get_by_id(report_id, owner_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    storage_path = report.storage_path
    deleted = await repo.delete_for_owner(report_id, owner_id)
    if deleted:
        await storage.delete(storage_path)
        logger.info("Report deleted: report_id=%s owner_id=%s", report_id, owner_id)
