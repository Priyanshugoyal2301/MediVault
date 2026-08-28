"""QualityChecker — pre-OCR image / page quality gate."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import QualityCheckResult


@runtime_checkable
class QualityChecker(Protocol):
    """
    Assess whether a document page is OCR-viable (blur, low contrast, skew).

    Default: PassThroughQualityChecker (always ok) — preserves current pipeline.
    Future: USE_IMAGE_QUALITY_MODEL=1 → model under models/quality/.
    """

    def check(self, file_bytes: bytes, mime_type: str) -> QualityCheckResult:
        ...
