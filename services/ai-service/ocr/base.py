"""
ai-service/ocr/base.py

OcrBackend Protocol — the OCR engine is swappable behind this interface.
See DEV_LOG [2026-08-08]: Tesseract chosen for privacy; this abstraction
means we can swap to a cloud engine later without touching the parser.
"""

from typing import Protocol


class OcrBackend(Protocol):
    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        """
        Extract plain text from a document.
        - For application/pdf: try native text layer first, fall back to image OCR.
        - For image/* types: OCR directly.
        Returns extracted text as a single string.
        """
        ...
