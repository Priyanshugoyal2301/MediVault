"""
Compatibility lab values for /parse API — duck-types ReportParser.ParsedValue.

Phase 1A: avoid importing services.ai_service from models package (layering).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .schema import MedicalDocumentJSON


@dataclass
class CompatibilityLabValue:
    test_name: str
    panel: str
    value_numeric: Decimal | None
    value_text: str | None
    unit: str | None
    reference_range_low: Decimal | None
    reference_range_high: Decimal | None
    reference_range_text: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_name": self.test_name,
            "panel": self.panel,
            "value_numeric": self.value_numeric,
            "value_text": self.value_text,
            "unit": self.unit,
            "reference_range_low": self.reference_range_low,
            "reference_range_high": self.reference_range_high,
            "reference_range_text": self.reference_range_text,
        }


def medical_json_to_compatibility_values(
    doc: MedicalDocumentJSON,
) -> list[CompatibilityLabValue]:
    out: list[CompatibilityLabValue] = []
    for e in doc.laboratory:
        val_num = None
        val_text = None
        if isinstance(e.value, (int, float)):
            val_num = Decimal(str(e.value))
        elif e.value is not None:
            s = str(e.value).replace(",", ".")
            try:
                val_num = Decimal(s)
            except InvalidOperation:
                val_text = str(e.value)

        ref_low = ref_high = None
        ref_text = e.reference_range
        if e.reference_range:
            parts = re.split(r"[-–to]+", e.reference_range, maxsplit=1)
            if len(parts) == 2:
                try:
                    ref_low = Decimal(parts[0].strip().replace(",", "."))
                    ref_high = Decimal(parts[1].strip().replace(",", "."))
                except InvalidOperation:
                    pass

        out.append(
            CompatibilityLabValue(
                test_name=e.test_name,
                panel=e.panel or "Unknown",
                value_numeric=val_num,
                value_text=val_text,
                unit=e.unit,
                reference_range_low=ref_low,
                reference_range_high=ref_high,
                reference_range_text=ref_text,
            )
        )
    return out
