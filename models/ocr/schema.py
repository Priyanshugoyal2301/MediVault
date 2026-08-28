"""
Medical document JSON schema (Phase 1 internal representation).

Maps to production ParsedValue / ParseResponse for API compatibility —
this schema is for OCR evaluation and structured storage of intermediate
understanding, not for changing the public /parse contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BoundingBox:
    """Normalized or absolute page coordinates when the VLM provides them."""

    x0: float | None = None
    y0: float | None = None
    x1: float | None = None
    y1: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LaboratoryEntry:
    """
    Single laboratory result extracted from a report page.

    Field names are deliberately generic — no hardcoded clinical ranges.
    """

    test_name: str
    value: str | float | None = None
    unit: str | None = None
    reference_range: str | None = None
    flag: str | None = None  # e.g. high | low | normal | unknown (from report text only)
    page_number: int | None = None
    bounding_box: BoundingBox | None = None
    ocr_confidence: float | None = None
    extraction_confidence: float | None = None
    panel: str | None = None  # only if present on document header; not invented

    def to_dict(self) -> dict[str, Any]:
        d = {
            "test_name": self.test_name,
            "value": self.value,
            "unit": self.unit,
            "reference_range": self.reference_range,
            "flag": self.flag,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "ocr_confidence": self.ocr_confidence,
            "extraction_confidence": self.extraction_confidence,
            "panel": self.panel,
        }
        return d


@dataclass
class MedicalDocumentJSON:
    """
    Canonical Medical JSON produced by Unlimited-OCR post-processing.

    Example shape:
      {
        "patient": {},
        "laboratory": [...],
        "metadata": {},
        "confidence": {}
      }
    """

    patient: dict[str, Any] = field(default_factory=dict)
    laboratory: list[LaboratoryEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient": dict(self.patient),
            "laboratory": [e.to_dict() for e in self.laboratory],
            "metadata": dict(self.metadata),
            "confidence": dict(self.confidence),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MedicalDocumentJSON:
        labs: list[LaboratoryEntry] = []
        for raw in data.get("laboratory") or []:
            bb = raw.get("bounding_box")
            box = BoundingBox(**bb) if isinstance(bb, dict) else None
            labs.append(
                LaboratoryEntry(
                    test_name=str(raw.get("test_name") or ""),
                    value=raw.get("value"),
                    unit=raw.get("unit"),
                    reference_range=raw.get("reference_range"),
                    flag=raw.get("flag"),
                    page_number=raw.get("page_number"),
                    bounding_box=box,
                    ocr_confidence=raw.get("ocr_confidence"),
                    extraction_confidence=raw.get("extraction_confidence"),
                    panel=raw.get("panel"),
                )
            )
        return cls(
            patient=dict(data.get("patient") or {}),
            laboratory=labs,
            metadata=dict(data.get("metadata") or {}),
            confidence=dict(data.get("confidence") or {}),
        )
