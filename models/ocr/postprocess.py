"""
Post-process Unlimited-OCR raw text into Canonical Medical JSON.

Does NOT:
  - invent reference ranges or clinical flags
  - map to disease labels
  - normalize test aliases (later phase)

Does:
  - unwrap <|ref|> / <|det|> tokens from Unlimited-OCR output
  - extract table / key-value laboratory lines generically
  - attach page numbers and confidences when available
"""

from __future__ import annotations

import re
from typing import Any

from .schema import BoundingBox, LaboratoryEntry, MedicalDocumentJSON

# Unlimited-OCR grounding token patterns (from model card / vLLM recipe)
_REF_RE = re.compile(r"<\|ref\|>(.*?)<\|/ref\|>", re.DOTALL)
_DET_RE = re.compile(r"<\|det\|>(.*?)<\|/det\|>", re.DOTALL)

# Generic lab row: name, value, optional unit, optional ref range/flag.
# No hardcoded clinical numbers — only structural capture groups.
_NUM = r"([-+]?\d+(?:[.,]\d+)?)"
_LAB_LINE = re.compile(
    rf"""
    ^\s*
    (?P<name>[A-Za-z][A-Za-z0-9()/%\.\-+\t ]{{1,60}}?)
    \s*[:|=\t]\s*
    (?P<value>{_NUM})
    (?:\s*(?P<unit>[A-Za-zµμ/%²³\^0-9\.\-]+(?:/[A-Za-zµμ0-9\.]+)?))?
    (?:
        \s*[\(\[]?\s*
        (?P<ref_low>{_NUM})\s*[-–to]+\s*(?P<ref_high>{_NUM})
        \s*[\)\]]?
    )?
    (?:\s*(?P<flag>\bH\b|\bL\b|\bHIGH\b|\bLOW\b|\b\*\b))?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)

_TABLE_PIPE = re.compile(
    rf"""
    ^\s*
    (?P<name>[^|]+?)
    \s*\|\s*
    (?P<value>{_NUM})
    \s*(?:\|\s*(?P<unit>[^|]+?))?
    \s*(?:\|\s*(?P<ref>[^|]+?))?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)


def unwrap_vlm_text(raw: str) -> tuple[str, list[BoundingBox]]:
    """Strip grounding tokens; return plain markdown/text + any det boxes."""
    if not raw:
        return "", []
    boxes: list[BoundingBox] = []
    for m in _DET_RE.finditer(raw):
        box = _parse_det_coords(m.group(1))
        if box:
            boxes.append(box)
    # Prefer ref spans if present
    refs = _REF_RE.findall(raw)
    if refs:
        text = "\n".join(r.strip() for r in refs if r.strip())
    else:
        text = _DET_RE.sub("", raw)
        text = re.sub(r"<\|/?[a-zA-Z_]+\|>", "", text)
    return text.strip(), boxes


def _parse_det_coords(blob: str) -> BoundingBox | None:
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", blob)
    if len(nums) < 4:
        return None
    x0, y0, x1, y1 = (float(nums[0]), float(nums[1]), float(nums[2]), float(nums[3]))
    return BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)


def postprocess_to_medical_json(
    page_texts: list[tuple[int, str]],
    *,
    mime_type: str = "",
    backend: str = "unknown",
    ocr_confidence_default: float | None = 0.85,
    boxes_by_page: dict[int, list[BoundingBox]] | None = None,
    patient_hints: dict[str, Any] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> MedicalDocumentJSON:
    """
    Convert per-page OCR text into MedicalDocumentJSON.

    page_texts: list of (page_number, raw_or_clean_text)
    """
    laboratory: list[LaboratoryEntry] = []
    seen_keys: set[str] = set()
    page_confidences: list[float] = []
    boxes_by_page = boxes_by_page or {}

    for page_no, raw in page_texts:
        text, inline_boxes = unwrap_vlm_text(raw)
        page_boxes = list(boxes_by_page.get(page_no, [])) + inline_boxes
        entries = extract_laboratory_entries(
            text,
            page_number=page_no,
            ocr_confidence=ocr_confidence_default,
            boxes=page_boxes,
        )
        for e in entries:
            key = e.test_name.strip().lower()
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            laboratory.append(e)
        if ocr_confidence_default is not None:
            page_confidences.append(ocr_confidence_default)

    mean_ocr = (
        sum(page_confidences) / len(page_confidences) if page_confidences else None
    )
    mean_ext = None
    if laboratory:
        vals = [e.extraction_confidence for e in laboratory if e.extraction_confidence is not None]
        mean_ext = sum(vals) / len(vals) if vals else None

    return MedicalDocumentJSON(
        patient=dict(patient_hints or {}),
        laboratory=laboratory,
        metadata={
            "mime_type": mime_type,
            "backend": backend,
            "page_count": len(page_texts),
            "lab_count": len(laboratory),
            **(extra_metadata or {}),
        },
        confidence={
            "ocr_confidence": mean_ocr,
            "extraction_confidence": mean_ext,
            "overall": _combine_confidence(mean_ocr, mean_ext),
        },
    )


def extract_laboratory_entries(
    text: str,
    *,
    page_number: int | None = None,
    ocr_confidence: float | None = None,
    boxes: list[BoundingBox] | None = None,
) -> list[LaboratoryEntry]:
    """Structural extraction of lab rows from free text / markdown tables."""
    if not text or not text.strip():
        return []

    entries: list[LaboratoryEntry] = []
    box_iter = list(boxes or [])

    for m in _LAB_LINE.finditer(text):
        name = _clean_name(m.group("name"))
        if not name or _looks_like_header(name):
            continue
        value_raw = m.group("value").replace(",", ".")
        unit = (m.group("unit") or "").strip() or None
        ref_low, ref_high = m.group("ref_low"), m.group("ref_high")
        ref = None
        if ref_low and ref_high:
            ref = f"{ref_low}–{ref_high}"
        flag = (m.group("flag") or "").strip().upper() or None
        if flag == "*":
            flag = None  # ambiguous marker from report typography only if alone
        try:
            value: str | float = float(value_raw)
        except ValueError:
            value = value_raw
        bb = box_iter.pop(0) if box_iter else None
        entries.append(
            LaboratoryEntry(
                test_name=name,
                value=value,
                unit=unit,
                reference_range=ref,
                flag=flag.lower() if flag and flag not in ("H", "L") else (
                    {"H": "high", "L": "low"}.get(flag or "", flag)
                ),
                page_number=page_number,
                bounding_box=bb,
                ocr_confidence=ocr_confidence,
                extraction_confidence=_row_extraction_confidence(m.group(0), unit, ref),
            )
        )

    if not entries:
        for m in _TABLE_PIPE.finditer(text):
            name = _clean_name(m.group("name"))
            if not name or _looks_like_header(name):
                continue
            value_raw = m.group("value").replace(",", ".")
            unit = (m.group("unit") or "").strip() or None
            ref = (m.group("ref") or "").strip() or None
            try:
                value = float(value_raw)
            except ValueError:
                value = value_raw
            bb = box_iter.pop(0) if box_iter else None
            entries.append(
                LaboratoryEntry(
                    test_name=name,
                    value=value,
                    unit=unit,
                    reference_range=ref,
                    flag=None,
                    page_number=page_number,
                    bounding_box=bb,
                    ocr_confidence=ocr_confidence,
                    extraction_confidence=_row_extraction_confidence(m.group(0), unit, ref),
                )
            )

    return entries


def medical_json_to_legacy_values(doc: MedicalDocumentJSON):
    """
    Convert Medical JSON → compatibility lab values for production /parse API.
    Phase 1A: uses models.ocr.legacy_map (no services import).
    """
    from .legacy_map import medical_json_to_compatibility_values

    return medical_json_to_compatibility_values(doc)


def medical_json_to_parsed_fields(doc: MedicalDocumentJSON):
    from packages.ml_interfaces.types import ParsedField

    fields = []
    for e in doc.laboratory:
        conf = e.extraction_confidence
        fields.append(
            ParsedField(
                test_name=e.test_name,
                panel=e.panel,
                value_numeric=e.value if isinstance(e.value, (int, float)) else None,
                value_text=None if isinstance(e.value, (int, float)) else (
                    str(e.value) if e.value is not None else None
                ),
                unit=e.unit,
                reference_range_low=None,
                reference_range_high=None,
                reference_range_text=e.reference_range,
                confidence=conf,
                raw_span=None,
            )
        )
    return fields


def _clean_name(name: str) -> str:
    n = re.sub(r"\s+", " ", (name or "").strip())
    n = n.strip("|:-")
    return n


def _looks_like_header(name: str) -> bool:
    low = name.lower()
    headers = {
        "test",
        "test name",
        "parameter",
        "result",
        "investigation",
        "analyte",
        "unit",
        "reference",
        "ref range",
        "normal range",
    }
    return low in headers or low.startswith("complete blood")


def _row_extraction_confidence(raw_line: str, unit: str | None, ref: str | None) -> float:
    """Heuristic confidence from structural completeness — not a clinical score."""
    score = 0.55
    if unit:
        score += 0.2
    if ref:
        score += 0.15
    if len(raw_line) > 12:
        score += 0.05
    return min(round(score, 3), 0.99)


def _combine_confidence(ocr: float | None, ext: float | None) -> float | None:
    if ocr is None and ext is None:
        return None
    if ocr is None:
        return ext
    if ext is None:
        return ocr
    return round(0.5 * ocr + 0.5 * ext, 4)
