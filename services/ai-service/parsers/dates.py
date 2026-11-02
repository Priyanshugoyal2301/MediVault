"""
ai-service/parsers/dates.py

Clinical date extraction and semantic precedence engine for medical lab reports.

Implements Representation B:
  - Document-level clinical date derived via deterministic semantic precedence.
  - Optional observation-specific date overrides.
  - Full propagation to ParsedValue -> ParsedValueOut -> TimelineEvent.

Precedence Policy:
  1. Specimen / Sample collection date (highest priority clinical date)
  2. Observation / Test date
  3. Result date
  4. Report / Issue date
  5. Unlabelled date (fallback only if no clinically labelled date is present)
  Rejected: Administrative / billing / admission / registration / DOB dates
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Sequence


class SemanticDateType(str, Enum):
    COLLECTION = "collection"
    TEST = "test"
    RESULT = "result"
    REPORT = "report"
    ADMINISTRATIVE = "administrative"
    UNLABELLED = "unlabelled"


# Numerical rank for deterministic precedence (lower is higher priority)
PRECEDENCE_RANKS: dict[SemanticDateType, int] = {
    SemanticDateType.COLLECTION: 1,
    SemanticDateType.TEST: 2,
    SemanticDateType.RESULT: 3,
    SemanticDateType.REPORT: 4,
    SemanticDateType.UNLABELLED: 5,
    SemanticDateType.ADMINISTRATIVE: 99,
}

CONFIDENCE_BY_TYPE: dict[SemanticDateType, float] = {
    SemanticDateType.COLLECTION: 0.95,
    SemanticDateType.TEST: 0.90,
    SemanticDateType.RESULT: 0.85,
    SemanticDateType.REPORT: 0.75,
    SemanticDateType.UNLABELLED: 0.50,
    SemanticDateType.ADMINISTRATIVE: 0.0,
}


@dataclass(frozen=True)
class DateCandidate:
    date_value: date
    date_iso: str
    date_type: SemanticDateType
    confidence: float
    raw_match: str
    label_text: str | None = None
    line_number: int | None = None


# Month name lookup (case-insensitive)
MONTH_MAP: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

MONTH_REGEX_STR = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

# ---------------------------------------------------------------------------
# Semantic label regexes
# ---------------------------------------------------------------------------
_LABEL_COLLECTION = (
    r"(?:sample\s+collection\s+date|specimen\s+collection\s+date|collection\s+date|"
    r"date\s+of\s+collection|sample\s+collected\s+on|specimen\s+collected\s+on|"
    r"collected\s+date|sample\s+date|specimen\s+date|collected\s+on|collected\s+at|"
    r"coll\.?\s*date|sample\s*coll\.?|specimen\s*coll\.?|coll\s+dt)"
)

_LABEL_TEST = (
    r"(?:date\s+of\s+test|test\s+date|observation\s+date|date\s+of\s+observation|"
    r"date\s+of\s+examination|examination\s+date|examined\s+on|tested(?:\s+on)?|"
    r"testing(?:\s+date)?|performed\s+on|analysis\s+date|date\s+of\s+analysis|test\s+dt)"
)

_LABEL_RESULT = (
    r"(?:result\s+date|date\s+of\s+result|results\s+on|resulted\s+on|result\s+dt)"
)

_LABEL_REPORT = (
    r"(?:report\s+date|date\s+of\s+report|reported\s+on|issue\s+date|date\s+of\s+issue|"
    r"report\s+issue\s+date|authorized\s+on|released\s+on|reporting\s+date|report\s+dt|"
    r"printed\s+on|print\s+date|date\s+of\s+print|generated\s+on)"
)

_LABEL_ADMIN = (
    r"(?:registration\s+date|reg\.?\s*date|date\s+of\s+registration|admission\s+date|"
    r"adm\.?\s*date|date\s+of\s+admission|billing\s+date|bill\s+date|invoice\s+date|"
    r"date\s+of\s+birth|birth\s+date|\bdob\b)"
)

LABELLED_PATTERNS: list[tuple[SemanticDateType, str]] = [
    (SemanticDateType.COLLECTION, _LABEL_COLLECTION),
    (SemanticDateType.TEST, _LABEL_TEST),
    (SemanticDateType.RESULT, _LABEL_RESULT),
    (SemanticDateType.REPORT, _LABEL_REPORT),
    (SemanticDateType.ADMINISTRATIVE, _LABEL_ADMIN),
]

# Separator between label and date value
_LABEL_SEP = r"[\s:|=–—\-#\t.]*"


def _parse_valid_date(year: int, month: int, day: int) -> date | None:
    """Validate and construct date. Rejects invalid dates and unrealistic years."""
    if year < 100:
        year = 2000 + year if year < 50 else 1900 + year
    if not (1900 <= year <= 2100):
        return None
    if not (1 <= month <= 12):
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date_string(raw: str) -> date | None:
    """
    Parse a date substring into a datetime.date object.
    Supports:
      - YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
      - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
      - DD Mon YYYY, DD-Mon-YYYY, DD/Mon/YYYY, DD.Mon.YYYY
      - Mon DD, YYYY, Mon DD YYYY
      - YYYY Mon DD, YYYY-Mon-DD
    """
    s = raw.strip()

    # 1. ISO format: YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _parse_valid_date(y, mo, d)

    # 2. Textual month: DD Mon YYYY (e.g. 15 Jan 2024, 15-Jan-2024, 15/Jan/2024)
    m = re.match(rf"^(\d{{1,2}})[-/.\s]+({MONTH_REGEX_STR})[-/.,\s]+(\d{{2,4}})", s, re.IGNORECASE)
    if m:
        d = int(m.group(1))
        mo_str = m.group(2).lower()
        y = int(m.group(3))
        mo = MONTH_MAP.get(mo_str)
        if mo:
            return _parse_valid_date(y, mo, d)

    # 3. Textual month: Mon DD, YYYY or Mon DD YYYY (e.g. Jan 15, 2024)
    m = re.match(rf"^({MONTH_REGEX_STR})[-/.\s]+(\d{{1,2}})[-/.,\s]+(\d{{2,4}})", s, re.IGNORECASE)
    if m:
        mo_str = m.group(1).lower()
        d = int(m.group(2))
        y = int(m.group(3))
        mo = MONTH_MAP.get(mo_str)
        if mo:
            return _parse_valid_date(y, mo, d)

    # 4. Textual month: YYYY Mon DD or YYYY-Mon-DD (e.g. 2024 Jan 15)
    m = re.match(rf"^(\d{{4}})[-/.\s]+({MONTH_REGEX_STR})[-/.,\s]+(\d{{1,2}})", s, re.IGNORECASE)
    if m:
        y = int(m.group(1))
        mo_str = m.group(2).lower()
        d = int(m.group(3))
        mo = MONTH_MAP.get(mo_str)
        if mo:
            return _parse_valid_date(y, mo, d)

    # 5. Numeric: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", s)
    if m:
        first, second, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Indian standard is DD/MM/YYYY.
        # Disambiguation: if first > 12 and second <= 12, first is day.
        # If second > 12 and first <= 12, second is day (MM/DD/YYYY).
        # If both <= 12, default to Indian standard DD/MM/YYYY.
        if first > 12 and second <= 12:
            return _parse_valid_date(y, second, first)
        elif second > 12 and first <= 12:
            return _parse_valid_date(y, first, second)
        else:
            return _parse_valid_date(y, second, first)

    return None


# Combined pattern to scan free-floating / unlabelled dates
_DATE_VALUE_PATTERN = rf"""
    (?:\b\d{{4}}[-/.]\d{{1,2}}[-/.]\d{{1,2}}\b)                             # YYYY-MM-DD
    | (?:\b\d{{1,2}}[-/.]\d{{1,2}}[-/.]\d{{2,4}}\b)                        # DD/MM/YYYY
    | (?:\b\d{{1,2}}[-/.\s]+{MONTH_REGEX_STR}[-/.,\s]+\d{{2,4}}\b)         # DD Mon YYYY
    | (?:\b{MONTH_REGEX_STR}[-/.\s]+\d{{1,2}}[-/.,\s]+\d{{2,4}}\b)         # Mon DD, YYYY
    | (?:\b\d{{4}}[-/.\s]+{MONTH_REGEX_STR}[-/.,\s]+\d{{1,2}}\b)          # YYYY Mon DD
"""
_RE_UNLABELLED_DATE = re.compile(_DATE_VALUE_PATTERN, re.IGNORECASE | re.VERBOSE)


def extract_dates(text: str) -> list[DateCandidate]:
    """
    Extract all date candidates from document text, classifying by semantic label
    where possible and recording confidence, raw text, and line index.
    """
    candidates: list[DateCandidate] = []
    lines = text.splitlines()

    for line_idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        matched_spans: list[tuple[int, int]] = []

        # 1. Search for labelled dates first
        for date_type, label_pat in LABELLED_PATTERNS:
            regex = re.compile(
                rf"(?P<label>{label_pat}){_LABEL_SEP}(?P<date>{_DATE_VALUE_PATTERN})",
                re.IGNORECASE | re.VERBOSE,
            )
            for m in regex.finditer(line):
                raw_date_str = m.group("date")
                parsed = parse_date_string(raw_date_str)
                if parsed:
                    label_text = m.group("label").strip()
                    cand = DateCandidate(
                        date_value=parsed,
                        date_iso=parsed.isoformat(),
                        date_type=date_type,
                        confidence=CONFIDENCE_BY_TYPE[date_type],
                        raw_match=m.group(0).strip(),
                        label_text=label_text,
                        line_number=line_idx + 1,
                    )
                    candidates.append(cand)
                    matched_spans.append((m.start(), m.end()))

        # 2. Search for unlabelled dates in the remaining text of the line
        for m in _RE_UNLABELLED_DATE.finditer(line):
            start, end = m.start(), m.end()
            # Avoid re-capturing spans already matched as labelled dates
            if any(s <= start and end <= e for s, e in matched_spans):
                continue

            raw_date_str = m.group(0)
            parsed = parse_date_string(raw_date_str)
            if parsed:
                # Check surrounding context on the line for administrative keywords
                line_lower = line.lower()
                is_admin = bool(re.search(_LABEL_ADMIN, line_lower, re.IGNORECASE))
                dtype = SemanticDateType.ADMINISTRATIVE if is_admin else SemanticDateType.UNLABELLED
                cand = DateCandidate(
                    date_value=parsed,
                    date_iso=parsed.isoformat(),
                    date_type=dtype,
                    confidence=CONFIDENCE_BY_TYPE[dtype],
                    raw_match=raw_date_str.strip(),
                    label_text=None,
                    line_number=line_idx + 1,
                )
                candidates.append(cand)

    return candidates


def select_clinical_date(candidates: Sequence[DateCandidate]) -> DateCandidate | None:
    """
    Select the single most authoritative clinical document date using deterministic precedence:
      1. Specimen / Sample collection date
      2. Observation / Test date
      3. Result date
      4. Report / Issue date
      5. Unlabelled date (only if confidence > 0.0)

    Administrative dates are rejected.
    If multiple candidates exist within the highest available priority,
    the candidate with highest confidence (then earliest occurrence) is selected.
    If no clinically relevant candidates exist, returns None (preserves ambiguity).
    """
    valid = [c for c in candidates if c.date_type != SemanticDateType.ADMINISTRATIVE]
    if not valid:
        return None

    def _sort_key(c: DateCandidate) -> tuple[int, float, int]:
        rank = PRECEDENCE_RANKS.get(c.date_type, 99)
        # Sort by:
        # 1. Precedence rank ascending (1 = Collection is best)
        # 2. Confidence descending (higher confidence preferred)
        # 3. Line number ascending (earlier in document preferred)
        return (rank, -c.confidence, c.line_number or 9999)

    sorted_candidates = sorted(valid, key=_sort_key)
    return sorted_candidates[0]


def extract_document_date(text: str) -> DateCandidate | None:
    """
    End-to-end convenience helper:
    Extracts all candidate dates and selects the authoritative clinical document date.
    """
    candidates = extract_dates(text)
    return select_clinical_date(candidates)


def extract_line_observation_date(line: str) -> DateCandidate | None:
    """
    Extract an observation-specific date from an individual lab result line if present.
    """
    candidates = extract_dates(line)
    return select_clinical_date(candidates)
