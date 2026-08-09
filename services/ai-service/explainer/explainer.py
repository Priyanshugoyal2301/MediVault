"""
ai-service/explainer/explainer.py

Generates plain-language explanations for parsed report values.

Rules (non-negotiable per 01_PROJECT_CONTEXT.md §4):
  - Never output a diagnosis or definitive medical claim.
  - Frame as "commonly associated with", "may be worth discussing".
  - Always base the explanation on the reference range on file.
  - Both English and Hindi explanations are generated simultaneously.

Status determination:
  - "normal":  value_numeric is within [ref_low, ref_high] (inclusive).
  - "high":    value_numeric > ref_high.
  - "low":     value_numeric < ref_low.
  - "unknown": value_numeric is None OR reference range is missing.
    In this case the explanation acknowledges we cannot assess against a range.
"""

from dataclasses import dataclass
from decimal import Decimal

from .templates import TEST_INFO, _FALLBACK, TestInfo


@dataclass
class Explanation:
    test_name: str
    status: str          # "normal" | "high" | "low" | "unknown"
    explanation_en: str
    explanation_hi: str


def _determine_status(
    value: Decimal | None,
    ref_low: Decimal | None,
    ref_high: Decimal | None,
) -> str:
    if value is None or (ref_low is None and ref_high is None):
        return "unknown"
    if ref_high is not None and value > ref_high:
        return "high"
    if ref_low is not None and value < ref_low:
        return "low"
    return "normal"


def _format(
    test_name: str,
    value_str: str,
    unit: str | None,
    ref_text: str | None,
    status: str,
    info: TestInfo,
    locale: str,
) -> str:
    """
    Build a single explanation string in the given locale.
    Never contains "you have X" or "diagnosed with X".
    """
    unit_part = f" {unit}" if unit else ""
    ref_part = f" (reference range: {ref_text})" if ref_text else ""

    if locale == "hi-IN":
        what = info.what_it_is_hi
        if status == "normal":
            verdict = info.normal_note_hi
            verdict_prefix = f"{test_name} का परिणाम {value_str}{unit_part} है{ref_part}। "
        elif status == "high":
            verdict = info.high_note_hi
            verdict_prefix = f"{test_name} का परिणाम {value_str}{unit_part} है, जो सामान्य संदर्भ सीमा{ref_part} से अधिक है। "
        elif status == "low":
            verdict = info.low_note_hi
            verdict_prefix = f"{test_name} का परिणाम {value_str}{unit_part} है, जो सामान्य संदर्भ सीमा{ref_part} से कम है। "
        else:
            verdict_prefix = f"{test_name} का परिणाम {value_str}{unit_part} है। "
            verdict = "इस परिणाम की तुलना किसी संदर्भ सीमा से नहीं की जा सकती। कृपया अपने डॉक्टर से चर्चा करें।"
        return f"{what} {verdict_prefix}{verdict}"
    else:  # en-IN
        what = info.what_it_is_en
        if status == "normal":
            verdict = info.normal_note_en
            verdict_prefix = f"{test_name} is {value_str}{unit_part}{ref_part}. "
        elif status == "high":
            verdict = info.high_note_en
            verdict_prefix = f"{test_name} is {value_str}{unit_part}, which is above the typical reference range{ref_part}. "
        elif status == "low":
            verdict = info.low_note_en
            verdict_prefix = f"{test_name} is {value_str}{unit_part}, which is below the typical reference range{ref_part}. "
        else:
            verdict_prefix = f"{test_name} is {value_str}{unit_part}. "
            verdict = "No reference range was found in the report to assess this result against. Please discuss with your doctor."
        return f"{what} {verdict_prefix}{verdict}"


def explain(
    test_name: str,
    value_numeric: Decimal | None,
    value_text: str | None,
    unit: str | None,
    reference_range_low: Decimal | None,
    reference_range_high: Decimal | None,
    reference_range_text: str | None,
) -> Explanation:
    """
    Generate English and Hindi plain-language explanations for one parsed value.
    Returns an Explanation with both locale strings.
    """
    info = TEST_INFO.get(test_name, _FALLBACK)
    status = _determine_status(value_numeric, reference_range_low, reference_range_high)

    value_str = str(value_numeric) if value_numeric is not None else (value_text or "—")
    ref_text = reference_range_text or (
        f"{reference_range_low}–{reference_range_high}"
        if reference_range_low is not None and reference_range_high is not None
        else None
    )

    return Explanation(
        test_name=test_name,
        status=status,
        explanation_en=_format(test_name, value_str, unit, ref_text, status, info, "en-IN"),
        explanation_hi=_format(test_name, value_str, unit, ref_text, status, info, "hi-IN"),
    )
