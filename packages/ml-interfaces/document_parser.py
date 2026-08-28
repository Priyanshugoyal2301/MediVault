"""DocumentParser — OCR + structured lab value extraction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import ParsedField


@runtime_checkable
class DocumentParser(Protocol):
    """
    Convert a medical report document (PDF/image bytes) into structured fields.

    Default implementation: TesseractOCR + regex ReportParser
    (services/ai-service adapters.regex_document_parser).
    Future: layout-aware / document IE models behind USE_UNLIMITED_OCR
    (OCR stage) and ML extractors.
    """

    def parse(self, file_bytes: bytes, mime_type: str) -> list[ParsedField]:
        """
        Full document understanding pipeline for one file.

        Returns an empty list on failure to extract (callers decide failed vs empty).
        """
        ...
