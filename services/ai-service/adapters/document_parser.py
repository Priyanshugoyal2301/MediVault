"""
Document parsers with Unlimited-OCR primary path + mandatory legacy fallback.

Phase 1A: empty / invalid Unlimited results trigger fallback (O-07).
Structured logging for production debugging.
"""

from __future__ import annotations

import time
from typing import Any

from packages.shared_utils import get_logger

logger = get_logger(__name__)


class RegexDocumentParser:
    """Production default / legacy path — Tesseract/pdfplumber + regex ReportParser."""

    def __init__(self, ocr: Any | None = None) -> None:
        self._ocr = ocr
        self._parser: Any | None = None

    def _get_parser(self) -> Any:
        if self._parser is None:
            from ..parsers.report_parser import ReportParser

            ocr = self._ocr
            if ocr is None:
                from ..ocr.tesseract_backend import TesseractBackend

                ocr = TesseractBackend()
            self._parser = ReportParser(ocr=ocr)
        return self._parser

    def parse(self, file_bytes: bytes, mime_type: str):
        from packages.ml_interfaces.types import ParsedField

        values = self._get_parser().parse(file_bytes, mime_type)
        return [
            ParsedField(
                test_name=pv.test_name,
                panel=pv.panel,
                value_numeric=pv.value_numeric,
                value_text=pv.value_text,
                unit=pv.unit,
                reference_range_low=pv.reference_range_low,
                reference_range_high=pv.reference_range_high,
                reference_range_text=pv.reference_range_text,
                confidence=None,
                raw_span=None,
            )
            for pv in values
        ]

    def parse_as_legacy(self, file_bytes: bytes, mime_type: str):
        return self._get_parser().parse(file_bytes, mime_type)


class UnlimitedOCRDocumentParser:
    """Wraps models.ocr.UnlimitedOCRParser. Raises on failure → FallbackDocumentParser."""

    def __init__(self, config: dict | None = None) -> None:
        from models.ocr.infer import UnlimitedOCRParser

        self._parser = UnlimitedOCRParser(config=config)

    @property
    def last_medical_json(self):
        return self._parser.last_medical_json

    @property
    def last_log(self):
        return getattr(self._parser, "last_log", {})

    def parse(self, file_bytes: bytes, mime_type: str):
        return self._parser.parse(file_bytes, mime_type)

    def parse_as_legacy(self, file_bytes: bytes, mime_type: str):
        return self._parser.parse_as_legacy(file_bytes, mime_type)

    def parse_document(self, file_bytes: bytes, mime_type: str):
        return self._parser.parse_document(file_bytes, mime_type)


def _is_empty_result(result: Any) -> bool:
    if result is None:
        return True
    if isinstance(result, list) and len(result) == 0:
        return True
    return False


class FallbackDocumentParser:
    """
    Try primary (Unlimited-OCR); on ANY failure or empty structured result, use legacy.

    Failure must never stop report processing.

    Fallback scenarios (Phase 1A):
      - crash / exception
      - timeout (HTTP)
      - malformed / invalid OCR output
      - empty OCR text
      - empty structured laboratory list
      - None returns
      - backend unavailable / misconfiguration
    """

    def __init__(
        self,
        primary: Any,
        fallback: Any | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback or RegexDocumentParser()
        self.last_path: str = "unset"
        self.last_error: str | None = None
        self._last_medical_json = None
        self.last_request_log: dict[str, Any] = {}

    @property
    def last_medical_json(self):
        return self._last_medical_json

    def parse(self, file_bytes: bytes, mime_type: str):
        return self._run(file_bytes, mime_type, legacy=False)

    def parse_as_legacy(self, file_bytes: bytes, mime_type: str):
        return self._run(file_bytes, mime_type, legacy=True)

    def _run(self, file_bytes: bytes, mime_type: str, *, legacy: bool):
        t0 = time.perf_counter()
        try:
            if legacy:
                result = self._primary.parse_as_legacy(file_bytes, mime_type)
            else:
                result = self._primary.parse(file_bytes, mime_type)

            if _is_empty_result(result):
                raise RuntimeError("Unlimited-OCR returned empty structured result")

            self.last_path = "unlimited_ocr"
            self.last_error = None
            self._last_medical_json = getattr(self._primary, "last_medical_json", None)
            elapsed = (time.perf_counter() - t0) * 1000.0
            conf = None
            mj = self._last_medical_json
            if mj is not None and getattr(mj, "confidence", None):
                conf = mj.confidence
            self.last_request_log = {
                "backend_selected": "unlimited_ocr",
                "fallback_triggered": False,
                "duration_ms": round(elapsed, 3),
                "confidence_available": bool(conf),
                "values_count": len(result) if isinstance(result, list) else None,
                "failure_reason": None,
                "processing_completed": True,
            }
            logger.info(
                "parse path=unlimited_ocr fallback=false duration_ms=%s values=%s conf=%s",
                round(elapsed, 3),
                len(result) if isinstance(result, list) else "?",
                bool(conf),
            )
            return result
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "Unlimited-OCR failed; falling back to legacy parser reason=%s",
                type(exc).__name__,
            )
            self.last_path = "legacy_fallback"
            self._last_medical_json = None
            t1 = time.perf_counter()
            if legacy:
                out = self._fallback.parse_as_legacy(file_bytes, mime_type)
            else:
                out = self._fallback.parse(file_bytes, mime_type)
            elapsed = (time.perf_counter() - t0) * 1000.0
            recovery_ms = (time.perf_counter() - t1) * 1000.0
            self.last_request_log = {
                "backend_selected": "legacy_fallback",
                "fallback_triggered": True,
                "duration_ms": round(elapsed, 3),
                "recovery_ms": round(recovery_ms, 3),
                "confidence_available": False,
                "values_count": len(out) if isinstance(out, list) else None,
                "failure_reason": self.last_error,
                "processing_completed": True,
            }
            logger.info(
                "parse path=legacy_fallback fallback=true duration_ms=%s "
                "recovery_ms=%s values=%s reason=%s",
                round(elapsed, 3),
                round(recovery_ms, 3),
                len(out) if isinstance(out, list) else "?",
                type(exc).__name__,
            )
            return out
