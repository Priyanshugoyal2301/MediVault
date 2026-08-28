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

# Magic-byte sniffing — do not trust Content-Type alone
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"RIFF", "image/webp"),  # refined below for WEBP
]


def _sniff_mime(file_bytes: bytes) -> str | None:
    if len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    for magic, mime in _MAGIC_SIGNATURES:
        if mime == "image/webp":
            continue
        if file_bytes.startswith(magic):
            return mime
    return None


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
        headers = {}
        # internal_service_key passed via closure from settings at schedule time
        from ..core.config import get_settings as _gs
        _key = (_gs().internal_service_key or "").strip()
        if _key:
            headers["X-Internal-Key"] = _key

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
                headers=headers,
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
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    sniffed = _sniff_mime(file_bytes)
    declared = file.content_type or ""
    if sniffed is None or sniffed not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported or unrecognized file type (magic-byte check failed)",
        )
    if declared and declared not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported Content-Type. Allowed: {', '.join(sorted(_ALLOWED_MIME_TYPES))}",
        )
    # Prefer sniffed type over spoofable Content-Type
    mime_type = sniffed

    storage_path = await storage.save(file_bytes, file.filename or "report", str(owner_id))

    repo = ReportRepository(db)
    report = await repo.create_report(
        owner_id=owner_id,
        original_filename=file.filename or "report",
        storage_path=storage_path,
        mime_type=mime_type,
    )

    logger.info("Report uploaded: report_id=%s owner_id=%s", report.id, owner_id)

    background_tasks.add_task(
        _trigger_parse,
        report_id=str(report.id),
        owner_id=str(owner_id),
        storage_path=storage_path,
        mime_type=mime_type,
        locale="en-IN",
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
                explanation_en=getattr(v, "explanation_en", None),
                explanation_hi=getattr(v, "explanation_hi", None),
            )
            for v in values
        ],
    )


# ---------------------------------------------------------------------------
# Demo seed — deterministic hackathon path (no OCR / Tesseract required)
# ---------------------------------------------------------------------------

_DEMO_PANELS: dict[str, list[dict]] = {
    "cbc": [
        {
            "test_name": "Haemoglobin",
            "panel": "CBC",
            "value_numeric": 10.5,
            "unit": "g/dL",
            "reference_range_low": 12.0,
            "reference_range_high": 15.5,
            "reference_range_text": "12.0 - 15.5",
            "date_of_test": "2025-02-10",
            "explanation_en": (
                "Haemoglobin carries oxygen in red blood cells. Haemoglobin is 10.5 g/dL, "
                "which is below the typical reference range (reference range: 12.0 - 15.5). "
                "A haemoglobin level below the reference range is commonly associated with anaemia, "
                "which can have several causes including iron or vitamin deficiency. "
                "This is worth discussing with your doctor."
            ),
            "explanation_hi": (
                "हीमोग्लोबिन लाल रक्त कोशिकाओं में ऑक्सीजन ले जाता है। हीमोग्लोबिन का परिणाम 10.5 g/dL है, "
                "जो सामान्य संदर्भ सीमा से कम है। कृपया अपने डॉक्टर से चर्चा करें।"
            ),
        },
        {
            "test_name": "Total Leucocyte Count (WBC)",
            "panel": "CBC",
            "value_numeric": 7200,
            "unit": "cells/µL",
            "reference_range_low": 4000,
            "reference_range_high": 11000,
            "reference_range_text": "4000 - 11000",
            "date_of_test": "2025-02-10",
            "explanation_en": (
                "White blood cells help the body respond to infection. "
                "Total Leucocyte Count (WBC) is 7200 cells/µL (reference range: 4000 - 11000). "
                "This result is within the typical reference range on the report."
            ),
            "explanation_hi": "डब्ल्यूबीसी का परिणाम संदर्भ सीमा के भीतर है।",
        },
        {
            "test_name": "Platelet Count",
            "panel": "CBC",
            "value_numeric": 240000,
            "unit": "/µL",
            "reference_range_low": 150000,
            "reference_range_high": 400000,
            "reference_range_text": "150000 - 400000",
            "date_of_test": "2025-02-10",
            "explanation_en": (
                "Platelets help blood clot. Platelet Count is 240000 /µL "
                "(reference range: 150000 - 400000), within the typical reference range."
            ),
            "explanation_hi": "प्लेटलेट काउंट सामान्य सीमा में है।",
        },
    ],
    "lipid": [
        {
            "test_name": "LDL Cholesterol",
            "panel": "Lipid",
            "value_numeric": 165,
            "unit": "mg/dL",
            "reference_range_low": 0,
            "reference_range_high": 130,
            "reference_range_text": "< 130",
            "date_of_test": "2025-01-15",
            "explanation_en": (
                "LDL Cholesterol is 165 mg/dL, which is above the typical reference range "
                "(reference range: < 130). Elevated LDL is commonly discussed with a doctor "
                "in the context of long-term heart health. This is not a diagnosis."
            ),
            "explanation_hi": "एलडीएल कोलेस्ट्रॉल संदर्भ सीमा से अधिक है। कृपया डॉक्टर से चर्चा करें।",
        },
        {
            "test_name": "HDL Cholesterol",
            "panel": "Lipid",
            "value_numeric": 45,
            "unit": "mg/dL",
            "reference_range_low": 40,
            "reference_range_high": 60,
            "reference_range_text": "40 - 60",
            "date_of_test": "2025-01-15",
            "explanation_en": "HDL Cholesterol is 45 mg/dL within the typical reference range on this report.",
            "explanation_hi": "एचडीएल कोलेस्ट्रॉल सामान्य सीमा में है।",
        },
        {
            "test_name": "Triglycerides",
            "panel": "Lipid",
            "value_numeric": 180,
            "unit": "mg/dL",
            "reference_range_low": 0,
            "reference_range_high": 150,
            "reference_range_text": "< 150",
            "date_of_test": "2025-01-15",
            "explanation_en": (
                "Triglycerides is 180 mg/dL, above the typical reference range on this report. "
                "Discuss lifestyle and clinical context with your doctor."
            ),
            "explanation_hi": "ट्राइग्लीसराइड स्तर संदर्भ सीमा से अधिक है।",
        },
    ],
}

# Extra historical LDL points so statistical monitor / z-score has a visible trend
_DEMO_LDL_HISTORY = [
    {"test_name": "LDL Cholesterol", "date_of_test": "2023-11-10", "value_numeric": 125, "unit": "mg/dL"},
    {"test_name": "LDL Cholesterol", "date_of_test": "2024-04-15", "value_numeric": 138, "unit": "mg/dL"},
    {"test_name": "LDL Cholesterol", "date_of_test": "2024-09-05", "value_numeric": 152, "unit": "mg/dL"},
    {"test_name": "LDL Cholesterol", "date_of_test": "2025-01-15", "value_numeric": 165, "unit": "mg/dL"},
]


@router.post("/demo/seed", status_code=201, response_model=ReportDetailOut)
async def seed_demo_report(
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    panel: str = "cbc",
):
    """
    Deterministic demo seed for hackathon judging — no OCR required.
    Creates a completed report + values + timeline events for the authenticated user.
    """
    from datetime import date

    panel_key = panel.lower().strip()
    if panel_key not in _DEMO_PANELS:
        raise HTTPException(status_code=400, detail="panel must be one of: cbc, lipid")

    values = _DEMO_PANELS[panel_key]
    repo = ReportRepository(db)
    timeline_repo = TimelineRepository(db)

    report = await repo.create_report(
        owner_id=owner_id,
        original_filename=f"demo_{panel_key}_panel.txt",
        storage_path=f"demo://{panel_key}/{owner_id}",
        mime_type="text/plain",
    )
    await repo.set_parsing_status(report.id, owner_id, "complete")

    await repo.save_report_values(
        owner_id=owner_id,
        report_id=report.id,
        parsed_values=values,
    )

    timeline_events = []
    for v in values:
        timeline_events.append(
            {
                "test_name": v["test_name"],
                "date_of_test": date.fromisoformat(v["date_of_test"]),
                "value_numeric": v.get("value_numeric"),
                "value_text": v.get("value_text"),
                "unit": v.get("unit"),
            }
        )
    if panel_key == "lipid":
        # Richer history for anomaly demo (avoid duplicating the latest point)
        for h in _DEMO_LDL_HISTORY[:-1]:
            timeline_events.append(
                {
                    "test_name": h["test_name"],
                    "date_of_test": date.fromisoformat(h["date_of_test"]),
                    "value_numeric": h["value_numeric"],
                    "value_text": None,
                    "unit": h["unit"],
                }
            )

    await timeline_repo.bulk_create_events(
        owner_id=owner_id,
        source_report_id=report.id,
        events=timeline_events,
    )
    await db.commit()

    stored = await repo.get_values_for_report(report.id, owner_id)
    logger.info("Demo seed created: report_id=%s panel=%s", report.id, panel_key)
    return ReportDetailOut(
        id=str(report.id),
        original_filename=report.original_filename,
        parsed_status="complete",
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
                explanation_en=getattr(v, "explanation_en", None),
                explanation_hi=getattr(v, "explanation_hi", None),
            )
            for v in stored
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
