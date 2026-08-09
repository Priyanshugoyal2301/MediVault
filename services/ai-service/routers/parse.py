"""
ai-service/routers/parse.py

POST /parse — called by health-service (background task) after a file is
stored. Reads the file from the storage path, OCRs it, parses it, generates
explanations, and returns structured values to health-service for DB storage.

This endpoint is internal (service-to-service only). In production it should
be behind the internal network and not exposed through the API gateway.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.shared_utils import get_logger

from ..explainer.explainer import explain
from ..ocr.tesseract_backend import TesseractBackend
from ..parsers.report_parser import ReportParser

logger = get_logger(__name__)
router = APIRouter(prefix="/parse", tags=["parse"])

_ocr = TesseractBackend()
_parser = ReportParser(ocr=_ocr)


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
async def parse_report(body: ParseRequest) -> Any:
    """
    Reads file from disk, runs OCR + parsing + explanation generation.
    Returns structured values with both English and Hindi explanations.
    Called internally by health-service background task.
    """
    path = Path(body.storage_path)
    if not path.exists():
        logger.error("Storage path not found for report_id=%s", body.report_id)
        raise HTTPException(status_code=404, detail="File not found at storage path")

    file_bytes = path.read_bytes()
    parsed_values = _parser.parse(file_bytes, body.mime_type)

    output: list[ParsedValueOut] = []
    for pv in parsed_values:
        exp = explain(
            test_name=pv.test_name,
            value_numeric=pv.value_numeric,
            value_text=pv.value_text,
            unit=pv.unit,
            reference_range_low=pv.reference_range_low,
            reference_range_high=pv.reference_range_high,
            reference_range_text=pv.reference_range_text,
        )
        output.append(
            ParsedValueOut(
                test_name=pv.test_name,
                panel=pv.panel,
                value_numeric=float(pv.value_numeric) if pv.value_numeric is not None else None,
                value_text=pv.value_text,
                unit=pv.unit,
                reference_range_low=float(pv.reference_range_low) if pv.reference_range_low is not None else None,
                reference_range_high=float(pv.reference_range_high) if pv.reference_range_high is not None else None,
                reference_range_text=pv.reference_range_text,
                status=exp.status,
                explanation_en=exp.explanation_en,
                explanation_hi=exp.explanation_hi,
            )
        )

    logger.info("Parse done: report_id=%s values_count=%d", body.report_id, len(output))
    return ParseResponse(report_id=body.report_id, values=output)
