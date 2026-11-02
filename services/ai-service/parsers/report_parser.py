"""
ai-service/parsers/report_parser.py

Orchestrates OCR → text → structured value extraction.
Returns a list of ParsedValue dicts that health-service stores in report_values.

Deduplication: if the same test name matches multiple times (e.g. because the
report repeats header rows), we keep the first match — which is typically the
actual result row, not a column header.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from packages.shared_utils import get_logger

from ..ocr.base import OcrBackend
from .dates import (
    DateCandidate,
    extract_document_date,
    extract_line_observation_date,
)
from .patterns import ALL_PATTERNS

logger = get_logger(__name__)


@dataclass
class ParsedValue:
    test_name: str
    panel: str
    value_numeric: Decimal | None
    value_text: str | None
    unit: str | None
    reference_range_low: Decimal | None
    reference_range_high: Decimal | None
    reference_range_text: str | None
    date_of_test: str | None = None
    date_type: str | None = None
    date_confidence: float | None = None

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
            "date_of_test": self.date_of_test,
            "date_type": self.date_type,
            "date_confidence": self.date_confidence,
        }


def _to_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    # Normalise comma-as-decimal-separator (common in some Indian reports)
    normalised = raw.replace(",", ".")
    try:
        return Decimal(normalised)
    except InvalidOperation:
        return None


class ReportParser:
    def __init__(self, ocr: OcrBackend) -> None:
        self._ocr = ocr
        self.last_document_date: DateCandidate | None = None

    def parse(self, file_bytes: bytes, mime_type: str) -> list[ParsedValue]:
        """
        Full pipeline: OCR → clean text → extract document date → extract values.
        Returns a (possibly empty) list of ParsedValue.
        """
        raw_text = self._ocr.extract_text(file_bytes, mime_type)
        cleaned = self._clean_text(raw_text)
        doc_date = extract_document_date(cleaned)
        self.last_document_date = doc_date
        values = self._extract_values(cleaned, doc_date=doc_date)
        logger.info(
            "Parser extracted %d values from report",
            len(values),
        )
        return values

    def _clean_text(self, text: str) -> str:
        # Normalise whitespace runs and remove zero-width chars
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text

    def _extract_values(
        self, text: str, doc_date: DateCandidate | None = None
    ) -> list[ParsedValue]:
        if doc_date is None:
            doc_date = extract_document_date(text)

        seen: set[str] = set()
        results: list[ParsedValue] = []

        for pp in ALL_PATTERNS:
            match = pp.pattern.search(text)
            if match is None:
                continue

            canonical = pp.test_name
            if canonical in seen:
                continue  # keep first match only
            seen.add(canonical)

            groups = match.groups()
            # Group layout from _build():
            # groups[0] = value_numeric string
            # groups[1] = unit string (optional → None)
            # groups[2] = ref_low string (optional → None)
            # groups[3] = ref_high string (optional → None)
            val_str = groups[0] if len(groups) > 0 else None
            unit_str = groups[1] if len(groups) > 1 else None
            ref_low_str = groups[2] if len(groups) > 2 else None
            ref_high_str = groups[3] if len(groups) > 3 else None

            val_numeric = _to_decimal(val_str)

            ref_text: str | None = None
            if ref_low_str and ref_high_str:
                ref_text = f"{ref_low_str}–{ref_high_str}"

            # Representation B: observation-specific date overrides document date
            match_start = match.start()
            line_start = text.rfind("\n", 0, match_start)
            line_start = 0 if line_start == -1 else line_start + 1
            line_end = text.find("\n", match.end())
            line_end = len(text) if line_end == -1 else line_end
            line_text = text[line_start:line_end]

            obs_date = extract_line_observation_date(line_text)
            chosen_date = obs_date or doc_date

            date_iso = chosen_date.date_iso if chosen_date else None
            date_type = (
                chosen_date.date_type.value
                if chosen_date and hasattr(chosen_date.date_type, "value")
                else str(chosen_date.date_type) if chosen_date else None
            )
            date_conf = chosen_date.confidence if chosen_date else None

            results.append(
                ParsedValue(
                    test_name=canonical,
                    panel=pp.panel,
                    value_numeric=val_numeric,
                    value_text=val_str if val_numeric is None else None,
                    unit=unit_str,
                    reference_range_low=_to_decimal(ref_low_str),
                    reference_range_high=_to_decimal(ref_high_str),
                    reference_range_text=ref_text,
                    date_of_test=date_iso,
                    date_type=date_type,
                    date_confidence=date_conf,
                )
            )

        return results
