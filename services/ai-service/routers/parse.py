"""
ai-service/routers/parse.py

POST /parse — called by health-service (background task) after a file is
stored. Internal-only: requires X-Internal-Key when configured, and may only
read files under STORAGE_LOCAL_PATH.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.shared_utils import get_logger

from ..core.config import Settings, get_settings
from ..core.internal_auth import require_internal_key, resolve_safe_storage_path
from ..core.registry import get_document_parser, get_normalizer, get_quality_checker
from ..explainer.explainer import explain

logger = get_logger(__name__)
router = APIRouter(prefix="/parse", tags=["parse"])


class ParseRequest(BaseModel):
    report_id: str
    owner_id: str
    storage_path: str
    mime_type: str
    locale: str = "en-IN"


class ParsedValueOut(BaseModel):
    test_name: str
    panel: str | None
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    reference_range_low: float | None
    reference_range_high: float | None
    reference_range_text: str | None
    status: str
    explanation_en: str
    explanation_hi: str


class ParseResponse(BaseModel):
    report_id: str
    values: list[ParsedValueOut]


@router.post("", response_model=ParseResponse)
async def parse_report(
    body: ParseRequest,
    _: Annotated[None, Depends(require_internal_key)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Any:
    """
    Reads file from disk (within storage root), runs OCR + parsing + explanations.
    """
    path = resolve_safe_storage_path(body.storage_path, settings.storage_root)
    if not path.exists() or not path.is_file():
        logger.error("Storage path not found for report_id=%s", body.report_id)
        raise HTTPException(status_code=404, detail="File not found at storage path")

    file_bytes = path.read_bytes()

    # Quality gate (default: pass-through — no behaviour change)
    quality = get_quality_checker().check(file_bytes, body.mime_type)
    if not quality.ok:
        logger.warning(
            "Quality check failed for report_id=%s score=%s reasons=%s",
            body.report_id,
            quality.score,
            quality.reasons,
        )
        return ParseResponse(report_id=body.report_id, values=[])

    # DocumentParser interface (legacy or Unlimited-OCR+fallback). API response unchanged.
    parser = get_document_parser()
    try:
        parsed_values = parser.parse_as_legacy(file_bytes, body.mime_type)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Document parse failed for report_id=%s: %s",
            body.report_id,
            type(exc).__name__,
        )
        parsed_values = []

    path_used = getattr(parser, "last_path", "legacy")
    req_log = getattr(parser, "last_request_log", {}) or {}
    logger.info(
        "Parse done report_id=%s path=%s fallback=%s backend=%s "
        "duration_ms=%s values=%s failure_reason=%s processing_completed=%s",
        body.report_id,
        path_used,
        req_log.get("fallback_triggered"),
        req_log.get("backend_selected", path_used),
        req_log.get("duration_ms"),
        len(parsed_values),
        req_log.get("failure_reason"),
        req_log.get("processing_completed", True),
    )

    # Phase 2: canonicalize test names (rule or ML). API schema unchanged.
    normalizer = get_normalizer()
    output: list[ParsedValueOut] = []
    for pv in parsed_values:
        raw_name = pv.test_name
        try:
            canonical = normalizer.normalize_test_name(raw_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Normalizer failed for %r (%s); using raw name",
                raw_name,
                type(exc).__name__,
            )
            canonical = raw_name
        if canonical != raw_name:
            logger.info(
                "Normalized test_name raw=%r → canonical=%r path=%s",
                raw_name,
                canonical,
                getattr(normalizer, "last_path", "normalizer"),
            )
        try:
            unit = normalizer.normalize_unit(canonical, pv.unit)
        except Exception:
            unit = pv.unit

        exp = explain(
            test_name=canonical,
            value_numeric=pv.value_numeric,
            value_text=pv.value_text,
            unit=unit,
            reference_range_low=pv.reference_range_low,
            reference_range_high=pv.reference_range_high,
            reference_range_text=pv.reference_range_text,
        )
        output.append(
            ParsedValueOut(
                test_name=canonical,
                panel=pv.panel,
                value_numeric=float(pv.value_numeric)
                if pv.value_numeric is not None
                else None,
                value_text=pv.value_text,
                unit=unit,
                reference_range_low=float(pv.reference_range_low)
                if pv.reference_range_low is not None
                else None,
                reference_range_high=float(pv.reference_range_high)
                if pv.reference_range_high is not None
                else None,
                reference_range_text=pv.reference_range_text,
                status=exp.status,
                explanation_en=exp.explanation_en,
                explanation_hi=exp.explanation_hi,
            )
        )

    return ParseResponse(report_id=body.report_id, values=output)
