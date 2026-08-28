"""
models.ocr — Unlimited-OCR document understanding package (Phase 1).

Public API:
  UnlimitedOCRParser  — DocumentParser with Medical JSON output
  load_config
  preprocess_document
  postprocess_to_medical_json
  medical_json_to_parsed_fields / medical_json_to_legacy_values
"""

from __future__ import annotations

from .infer import UnlimitedOCRParser
from .schema import LaboratoryEntry, MedicalDocumentJSON

__all__ = [
    "LaboratoryEntry",
    "MedicalDocumentJSON",
    "UnlimitedOCRParser",
]
