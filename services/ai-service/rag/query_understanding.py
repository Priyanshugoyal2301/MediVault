"""
services/ai-service/rag/query_understanding.py

Deterministic clinical query understanding and temporal intent parser (CP-05).

Parses natural language user queries into structured ClinicalQuery objects
without external LLM calls or paid network APIs. Identifies:
  - Clinical analytes (raw mentions, canonical concepts, LOINC codes)
  - Temporal retrieval intents (CURRENT_VALUE, HISTORICAL, LAST_N, COMPARISON,
    TREND, DEFINITION_GUIDELINE, ABNORMALITY)
  - Temporal operators (LATEST, EXACT_DATE, BEFORE, AFTER, BETWEEN, SINCE, LAST_N, ALL_TIME)
  - Date boundaries and relative retrieval windows
  - Comparison targets (PREVIOUS, HISTORICAL, PERIOD, BASELINE)
  - Abnormality constraints
  - Deterministic confidence scoring and unresolved term tracking
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    RelativeWindow,
    TemporalOperator,
    WindowUnit,
)

# ---------------------------------------------------------------------------
# Number words mapping
# ---------------------------------------------------------------------------

_NUMBER_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "a": 1,
    "an": 1,
}

# ---------------------------------------------------------------------------
# Month names mapping
# ---------------------------------------------------------------------------

_MONTH_NAMES: dict[str, int] = {
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

# ---------------------------------------------------------------------------
# Clinical Analyte Knowledge Base (Deterministic & Curated)
# ---------------------------------------------------------------------------


_ANALYTES: tuple[dict[str, Any], ...] = (
    # Extended compounds first (longest phrases match first)
    {
        "canonical": "HbA1c",
        "loinc": "4548-4",
        "concept_id": "LOINC:4548-4",
        "aliases": (
            "glycated hemoglobin", "glycated haemoglobin", "glycohemoglobin",
            "glycohaemoglobin", "hba1c", "a1c", "hemoglobin a1c", "haemoglobin a1c",
        ),
    },
    {
        "canonical": "eAG (Est. Avg Glucose)",
        "loinc": "27353-2",
        "concept_id": "LOINC:27353-2",
        "aliases": ("estimated average glucose", "estimated avg glucose", "eag"),
    },
    {
        "canonical": "LDL Cholesterol",
        "loinc": "2089-1",
        "concept_id": "LOINC:2089-1",
        "aliases": (
            "ldl cholesterol level", "ldl cholesterol levels", "ldl cholesterol reading",
            "ldl cholesterol result", "ldl cholesterol test", "ldl cholesterol report",
            "ldl cholesterol", "ldl-cholesterol", "bad cholesterol",
            "low-density lipoprotein", "low density lipoprotein",
            "ldl-c", "ldlc", "ldl",
        ),
    },
    {
        "canonical": "HDL Cholesterol",
        "loinc": "2085-9",
        "concept_id": "LOINC:2085-9",
        "aliases": (
            "hdl cholesterol level", "hdl cholesterol levels", "hdl cholesterol reading",
            "hdl cholesterol result", "hdl cholesterol test", "hdl cholesterol report",
            "hdl cholesterol", "hdl-cholesterol", "good cholesterol",
            "high-density lipoprotein", "high density lipoprotein",
            "hdl-c", "hdlc", "hdl",
        ),
    },
    {
        "canonical": "VLDL Cholesterol",
        "loinc": "13457-7",
        "concept_id": "LOINC:13457-7",
        "aliases": ("vldl cholesterol", "vldl-cholesterol", "vldl-c", "vldl"),
    },
    {
        "canonical": "Non-HDL Cholesterol",
        "loinc": "43396-1",
        "concept_id": "LOINC:43396-1",
        "aliases": ("non-hdl cholesterol", "non hdl cholesterol", "non-hdl", "non hdl"),
    },
    {
        "canonical": "Total Cholesterol",
        "loinc": "2093-3",
        "concept_id": "LOINC:2093-3",
        "aliases": (
            "total cholesterol", "serum cholesterol", "cholesterol level",
            "cholesterol count", "cholesterol report", "cholesterol", "cholestrol",
            "lipid profile", "lipid profiles", "lipid panel", "lipid panels", "lipids",
        ),
    },
    {
        "canonical": "TC/HDL Ratio",
        "loinc": "9830-1",
        "concept_id": "LOINC:9830-1",
        "aliases": ("tc/hdl ratio", "tc/hdl", "cholesterol ratio"),
    },
    {
        "canonical": "Triglycerides",
        "loinc": "2571-8",
        "concept_id": "LOINC:2571-8",
        "aliases": ("triglycerides", "triglyceride", "serum triglycerides", "tg"),
    },
    {
        "canonical": "Haemoglobin",
        "loinc": "718-7",
        "concept_id": "LOINC:718-7",
        "aliases": (
            "haemoglobin", "hemoglobin", "haemoglobin (hb)", "hemoglobin (hb)",
            "serum hemoglobin", "serum haemoglobin", "hb blood", "blood hb",
            "khoon", "hb", "hgb",
        ),
    },
    {
        "canonical": "Platelets",
        "loinc": "777-3",
        "concept_id": "LOINC:777-3",
        "aliases": ("platelet count", "platelets count", "total platelets", "platelets", "platelet", "thrombocytes"),
    },
    {
        "canonical": "WBC",
        "loinc": "6690-2",
        "concept_id": "LOINC:6690-2",
        "aliases": (
            "total leucocyte count", "total leukocyte count", "white blood cells",
            "white blood cell count", "white blood cell", "white blood cells count",
            "leukocyte count", "leukocytes", "leucocytes", "wbc count", "wbc", "tlc",
        ),
    },
    {
        "canonical": "RBC",
        "loinc": "789-8",
        "concept_id": "LOINC:789-8",
        "aliases": (
            "total red blood cell count", "total red blood cells", "red blood cell count",
            "red blood cells count", "red blood cells", "red blood cell",
            "erythrocyte count", "erythrocytes", "rbc count", "rbc",
        ),
    },
    {
        "canonical": "Hematocrit",
        "loinc": "4544-3",
        "concept_id": "LOINC:4544-3",
        "aliases": ("packed cell volume", "hematocrit", "haematocrit", "pcv"),
    },
    {
        "canonical": "MCV",
        "loinc": "787-2",
        "concept_id": "LOINC:787-2",
        "aliases": ("mean corpuscular volume", "mcv"),
    },
    {
        "canonical": "MCH",
        "loinc": "785-6",
        "concept_id": "LOINC:785-6",
        "aliases": ("mean corpuscular hemoglobin", "mch"),
    },
    {
        "canonical": "MCHC",
        "loinc": "786-4",
        "concept_id": "LOINC:786-4",
        "aliases": ("mean corpuscular hemoglobin concentration", "mchc"),
    },
    {
        "canonical": "Neutrophils",
        "loinc": "770-8",
        "concept_id": "LOINC:770-8",
        "aliases": ("neutrophils", "neutrophil count", "neutrophil"),
    },
    {
        "canonical": "Lymphocytes",
        "loinc": "736-9",
        "concept_id": "LOINC:736-9",
        "aliases": ("lymphocytes", "lymphocyte count", "lymphocyte"),
    },
    {
        "canonical": "Monocytes",
        "loinc": "5905-5",
        "concept_id": "LOINC:5905-5",
        "aliases": ("monocytes", "monocyte count", "monocyte"),
    },
    {
        "canonical": "Eosinophils",
        "loinc": "711-2",
        "concept_id": "LOINC:711-2",
        "aliases": ("eosinophils", "eosinophil count", "eosinophil"),
    },
    {
        "canonical": "Basophils",
        "loinc": "704-7",
        "concept_id": "LOINC:704-7",
        "aliases": ("basophils", "basophil count", "basophil"),
    },
    {
        "canonical": "TSH",
        "loinc": "3016-3",
        "concept_id": "LOINC:3016-3",
        "aliases": (
            "thyroid stimulating hormone", "thyroid-stimulating hormone",
            "thyrotropin", "tsh level", "tsh test", "thyroid level",
            "thyroid test", "thyroid", "tsh",
        ),
    },
    {
        "canonical": "Free T3",
        "loinc": "3051-0",
        "concept_id": "LOINC:3051-0",
        "aliases": ("free triiodothyronine", "free t3", "ft3"),
    },
    {
        "canonical": "Free T4",
        "loinc": "3024-7",
        "concept_id": "LOINC:3024-7",
        "aliases": ("free thyroxine", "free t4", "ft4"),
    },
    {
        "canonical": "T3",
        "loinc": "3053-6",
        "concept_id": "LOINC:3053-6",
        "aliases": ("total triiodothyronine", "triiodothyronine", "t3"),
    },
    {
        "canonical": "T4",
        "loinc": "3026-2",
        "concept_id": "LOINC:3026-2",
        "aliases": ("total thyroxine", "thyroxine", "t4"),
    },
    {
        "canonical": "Glucose",
        "loinc": "2345-7",
        "concept_id": "LOINC:2345-7",
        "aliases": (
            "fasting blood sugar", "fasting blood glucose", "fasting glucose",
            "fasting sugar", "postprandial blood sugar", "post prandial blood sugar",
            "postprandial glucose", "random blood sugar", "random glucose",
            "blood sugar level", "blood glucose level", "blood sugar",
            "blood glucose", "serum glucose", "fbs", "ppbs", "rbs",
            "glucose", "sugar", "cheeni", "shakkar",
        ),
    },
    {
        "canonical": "Creatinine",
        "loinc": "2160-0",
        "concept_id": "LOINC:2160-0",
        "aliases": (
            "serum creatinine", "sr creatinine", "blood creatinine",
            "kidney function creatinine", "creatinine level", "creatinine",
        ),
    },
    {
        "canonical": "Urea",
        "loinc": "3094-0",
        "concept_id": "LOINC:3094-0",
        "aliases": ("blood urea nitrogen", "blood urea", "serum urea", "urea", "bun"),
    },
    {
        "canonical": "Bilirubin Total",
        "loinc": "1975-2",
        "concept_id": "LOINC:1975-2",
        "aliases": (
            "total bilirubin", "serum bilirubin", "bilirubin total",
            "bilirubin level", "bilirubin", "piliya", "jaundice",
        ),
    },
    {
        "canonical": "Alanine Aminotransferase",
        "loinc": "1742-6",
        "concept_id": "LOINC:1742-6",
        "aliases": (
            "alanine aminotransferase", "alanine transaminase",
            "serum glutamic pyruvic transaminase", "alt level", "alt", "sgpt",
        ),
    },
    {
        "canonical": "Aspartate Aminotransferase",
        "loinc": "1920-8",
        "concept_id": "LOINC:1920-8",
        "aliases": (
            "aspartate aminotransferase", "aspartate transaminase",
            "serum glutamic oxaloacetic transaminase", "ast level", "ast", "sgot",
        ),
    },
    {
        "canonical": "Alkaline Phosphatase",
        "loinc": "6768-6",
        "concept_id": "LOINC:6768-6",
        "aliases": ("alkaline phosphatase", "alk phos", "alp"),
    },
    {
        "canonical": "Uric Acid",
        "loinc": "3084-1",
        "concept_id": "LOINC:3084-1",
        "aliases": ("serum uric acid", "uric acid"),
    },
    {
        "canonical": "ESR",
        "loinc": "30341-2",
        "concept_id": "LOINC:30341-2",
        "aliases": ("erythrocyte sedimentation rate", "esr"),
    },
    {
        "canonical": "Calcium",
        "loinc": "17861-6",
        "concept_id": "LOINC:17861-6",
        "aliases": ("serum calcium", "total calcium", "calcium"),
    },
    {
        "canonical": "Potassium",
        "loinc": "2823-3",
        "concept_id": "LOINC:2823-3",
        "aliases": ("serum potassium", "potassium"),
    },
    {
        "canonical": "Sodium",
        "loinc": "2951-2",
        "concept_id": "LOINC:2951-2",
        "aliases": ("serum sodium", "sodium"),
    },
)


class ClinicalQueryParser:
    """
    Deterministic clinical query understanding parser.

    Implements pattern-driven semantic parsing with zero external network or
    LLM dependencies. Produces a typed ClinicalQuery contract.
    """

    def __init__(self) -> None:
        pass

    def parse(self, raw_query: str, anchor_date: date | None = None) -> ClinicalQuery:
        """
        Parses a natural language query into a structured ClinicalQuery.

        Args:
            raw_query: Verbatim user query string.
            anchor_date: Optional reference date for relative window resolution.
                         Defaults to date.today() if omitted.
        """
        if anchor_date is None:
            anchor_date = date.today()

        clean_query = (raw_query or "").strip()
        if not clean_query:
            return ClinicalQuery(
                raw_query=raw_query or "",
                intent=QueryIntent.DEFINITION_GUIDELINE,
                confidence=0.0,
                temporal_operator=TemporalOperator.NONE,
            )

        # Check for malformed / non-clinical gibberish
        if not re.search(r"[a-zA-Z0-9]", clean_query) or len(clean_query) < 2:
            return ClinicalQuery(
                raw_query=raw_query,
                intent=QueryIntent.DEFINITION_GUIDELINE,
                confidence=0.0,
                temporal_operator=TemporalOperator.NONE,
            )

        lower_query = clean_query.lower()

        # 1. Analyte extraction
        analyte_info = self._extract_analyte(clean_query, lower_query)

        # 2. Date and temporal window extraction
        temp_info = self._extract_temporal_constraints(lower_query, anchor_date)

        # 3. Abnormality constraint extraction
        is_abnormal_request = self._detect_abnormality(lower_query)

        # 4. Limit / Last-N extraction
        limit_val = self._extract_limit(lower_query)

        # 5. Intent and comparison detection
        intent, comparison_target = self._resolve_intent_and_comparison(
            clean_query, lower_query, analyte_info, temp_info, limit_val, is_abnormal_request
        )

        # 6. Determine final temporal operator
        temporal_operator = self._resolve_temporal_operator(
            intent, temp_info, limit_val
        )

        # 7. Calculate confidence
        confidence = self._compute_confidence(
            clean_query, lower_query, intent, analyte_info, temp_info, limit_val
        )

        # Construct final typed query contract
        return ClinicalQuery(
            raw_query=raw_query,
            intent=intent,
            analyte_mentions=analyte_info["mentions"],
            analyte_canonical=analyte_info["canonical"],
            concept_id=analyte_info["concept_id"],
            loinc_code=analyte_info["loinc"],
            temporal_operator=temporal_operator,
            start_date=temp_info.get("start_date"),
            end_date=temp_info.get("end_date"),
            relative_window=temp_info.get("relative_window"),
            limit=limit_val,
            comparison_target=comparison_target,
            abnormal_only=is_abnormal_request,
            confidence=confidence,
            unresolved_terms=analyte_info["unresolved_terms"],
            version="1.0",
        )

    # -----------------------------------------------------------------------
    # Analyte Recognition
    # -----------------------------------------------------------------------

    def _extract_analyte(self, raw_query: str, lower_query: str) -> dict[str, Any]:
        """
        Finds matched analyte in the query using longest-alias-first strategy.
        Preserves verbatim mention span for clinical auditability.
        """
        best_match = None
        best_span = None
        best_len = 0

        for entry in _ANALYTES:
            for alias in entry["aliases"]:
                # Check for boundary-aware word or hyphen/slash match
                # Escape alias for regex safety
                escaped = re.escape(alias)
                pattern = rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])"
                m = re.search(pattern, lower_query)
                if m:
                    # Guard against generic "cholesterol" aliases stealing "ldl/hdl/vldl cholesterol"
                    if entry["canonical"] == "Total Cholesterol":
                        pre = lower_query[:m.start()].rstrip()
                        if pre.endswith(("ldl", "hdl", "vldl", "non-hdl", "bad", "good")):
                            continue
                    span_len = len(alias)
                    if span_len > best_len:
                        best_len = span_len
                        best_match = entry
                        best_span = raw_query[m.start():m.end()]

        if best_match and best_span:
            return {
                "canonical": best_match["canonical"],
                "loinc": best_match["loinc"],
                "concept_id": best_match["concept_id"],
                "mentions": [best_span],
                "unresolved_terms": [],
            }

        # Check for unknown / candidate analyte phrasing (e.g. "my XYZ test", "what was my XYZ?")
        unknown_candidates = self._detect_unknown_analyte_candidates(lower_query)
        if unknown_candidates:
            return {
                "canonical": None,
                "loinc": None,
                "concept_id": None,
                "mentions": unknown_candidates,
                "unresolved_terms": unknown_candidates,
            }

        return {
            "canonical": None,
            "loinc": None,
            "concept_id": None,
            "mentions": [],
            "unresolved_terms": [],
        }

    def _detect_unknown_analyte_candidates(self, lower_query: str) -> list[str]:
        """
        Detects potential analyte tokens in slot positions like 'my <word> test'
        or 'what was my <word>' when not recognized in vocabulary.
        """
        # Stopwords that are never considered candidate analytes
        stopwords = {
            "last", "past", "latest", "previous", "recent", "first", "second",
            "third", "abnormal", "high", "low", "normal", "blood", "lab", "test",
            "report", "level", "result", "reading", "value", "doctor", "health",
            "sugar", "date", "year", "month", "day", "record",
        }
        patterns = [
            r"\bmy\s+([a-zA-Z0-9_\-]+)\s+(?:test|report|level|reading|value|count)\b",
            r"\bwhat\s+(?:was|is)\s+my\s+([a-zA-Z0-9_\-]+)\b",
            r"\bshow\s+(?:my\s+)?([a-zA-Z0-9_\-]+)\s+(?:test|report|level|reading)\b",
        ]
        candidates = []
        for p in patterns:
            for m in re.finditer(p, lower_query):
                word = m.group(1).strip()
                if word and word not in stopwords and len(word) > 2:
                    candidates.append(word)
        return candidates

    # -----------------------------------------------------------------------
    # Temporal & Date Parsing
    # -----------------------------------------------------------------------

    def _extract_temporal_constraints(
        self, lower_query: str, anchor_date: date
    ) -> dict[str, Any]:
        """
        Extracts absolute dates, ranges, and relative windows.
        """
        result: dict[str, Any] = {
            "start_date": None,
            "end_date": None,
            "relative_window": None,
            "explicit_operator": None,
        }

        # 1. Relative window pattern (e.g., "past 6 months", "last 2 years", "last 30 days")
        rel_pattern = (
            r"\b(?:in\s+the\s+)?(?:past|last|previous)\s+"
            r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+"
            r"(days?|weeks?|months?|years?)\b"
        )
        rel_match = re.search(rel_pattern, lower_query)
        if rel_match:
            raw_num = rel_match.group(1)
            num = _NUMBER_WORDS.get(raw_num, int(raw_num) if raw_num.isdigit() else 1)
            unit_str = rel_match.group(2).rstrip("s")

            if unit_str == "day":
                unit = WindowUnit.DAYS
                start_d = anchor_date - timedelta(days=num)
            elif unit_str == "week":
                unit = WindowUnit.WEEKS
                start_d = anchor_date - timedelta(weeks=num)
            elif unit_str == "month":
                unit = WindowUnit.MONTHS
                start_d = self._subtract_months(anchor_date, num)
            else:  # year
                unit = WindowUnit.YEARS
                start_d = self._subtract_years(anchor_date, num)

            result["relative_window"] = RelativeWindow(value=num, unit=unit)
            result["start_date"] = start_d
            result["end_date"] = anchor_date
            result["explicit_operator"] = TemporalOperator.SINCE
            return result

        # 1b. Singular relative window without number ("past month", "last year", "past week")
        rel_sing_pattern = r"\b(?:in\s+the\s+)?(?:past|last|previous)\s+(month|year|week)\b"
        rel_sing_match = re.search(rel_sing_pattern, lower_query)
        if rel_sing_match:
            unit_str = rel_sing_match.group(1)
            if unit_str == "week":
                unit = WindowUnit.WEEKS
                start_d = anchor_date - timedelta(weeks=1)
            elif unit_str == "month":
                unit = WindowUnit.MONTHS
                start_d = self._subtract_months(anchor_date, 1)
            else:
                unit = WindowUnit.YEARS
                start_d = self._subtract_years(anchor_date, 1)

            result["relative_window"] = RelativeWindow(value=1, unit=unit)
            result["start_date"] = start_d
            result["end_date"] = anchor_date
            result["explicit_operator"] = TemporalOperator.SINCE
            return result

        # 2. Date Range: between <date1> and <date2> / from <date1> to <date2>
        range_between = re.search(
            r"\bbetween\s+([a-zA-Z0-9\-\/ ]+?)\s+and\s+([a-zA-Z0-9\-\/ ]+)\b", lower_query
        )
        if range_between:
            d1 = self._parse_single_date(range_between.group(1).strip())
            d2 = self._parse_single_date(range_between.group(2).strip())
            if d1 and d2:
                result["start_date"] = min(d1[0], d2[0])
                result["end_date"] = max(d1[1], d2[1])
                result["explicit_operator"] = TemporalOperator.BETWEEN
                return result

        range_from_to = re.search(
            r"\bfrom\s+([a-zA-Z0-9\-\/ ]+?)\s+to\s+([a-zA-Z0-9\-\/ ]+)\b", lower_query
        )
        if range_from_to:
            d1 = self._parse_single_date(range_from_to.group(1).strip())
            d2 = self._parse_single_date(range_from_to.group(2).strip())
            if d1 and d2:
                result["start_date"] = min(d1[0], d2[0])
                result["end_date"] = max(d1[1], d2[1])
                result["explicit_operator"] = TemporalOperator.BETWEEN
                return result

        # 2b. Range / Comparison with two ISO dates (e.g., "from 2022-02-10 with 2024-03-30", "compare 2021-05-12 and 2024-02-11")
        iso_dates = re.findall(r"\b(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})\b", lower_query)
        if len(iso_dates) >= 2:
            parsed_dates = []
            for y_str, m_str, d_str in iso_dates[:2]:
                try:
                    parsed_dates.append(date(int(y_str), int(m_str), int(d_str)))
                except ValueError:
                    pass
            if len(parsed_dates) >= 2:
                result["start_date"] = min(parsed_dates)
                result["end_date"] = max(parsed_dates)
                result["explicit_operator"] = TemporalOperator.BETWEEN
                return result

        # 3. Directional bounds: before <date> / after <date> / since <date>
        before_match = re.search(r"\b(?:before|prior\s+to|earlier\s+than)\s+([a-zA-Z0-9\-\/ ]+)\b", lower_query)
        if before_match:
            d = self._parse_single_date(before_match.group(1).strip())
            if d:
                result["end_date"] = d[0]
                result["explicit_operator"] = TemporalOperator.BEFORE
                return result

        after_match = re.search(r"\b(?:after|since)\s+([a-zA-Z0-9\-\/ ]+)\b", lower_query)
        if after_match:
            d = self._parse_single_date(after_match.group(1).strip())
            if d:
                result["start_date"] = d[0]
                result["explicit_operator"] = TemporalOperator.SINCE
                return result

        # 4. Exact single date or Month/Year in query
        single_date = self._find_single_date_in_query(lower_query)
        if single_date:
            d_start, d_end, op = single_date
            result["start_date"] = d_start
            result["end_date"] = d_end
            result["explicit_operator"] = op
            return result

        return result

    def _parse_single_date(self, text: str) -> tuple[date, date] | None:
        """Parses a date string chunk into a (start_date, end_date) pair."""
        text = text.strip()

        # ISO format: YYYY-MM-DD
        m_iso = re.search(r"\b(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})\b", text)
        if m_iso:
            try:
                d = date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
                return (d, d)
            except ValueError:
                pass

        # DD/MM/YYYY or DD-MM-YYYY
        m_slash = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2}|19\d{2})\b", text)
        if m_slash:
            try:
                d = date(int(m_slash.group(3)), int(m_slash.group(2)), int(m_slash.group(1)))
                return (d, d)
            except ValueError:
                pass

        # DD Month YYYY (e.g. 14 Jan 2024 or 14th January 2024)
        m_dmy = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)\s+(20\d{2}|19\d{2})\b", text
        )
        if m_dmy:
            m_name = m_dmy.group(2).lower()
            if m_name in _MONTH_NAMES:
                try:
                    d = date(int(m_dmy.group(3)), _MONTH_NAMES[m_name], int(m_dmy.group(1)))
                    return (d, d)
                except ValueError:
                    pass

        # Month YYYY (e.g. January 2024)
        m_my = re.search(r"\b([a-zA-Z]+)\s+(20\d{2}|19\d{2})\b", text)
        if m_my:
            m_name = m_my.group(1).lower()
            if m_name in _MONTH_NAMES:
                yr = int(m_my.group(2))
                mo = _MONTH_NAMES[m_name]
                last_day = self._days_in_month(yr, mo)
                return (date(yr, mo, 1), date(yr, mo, last_day))

        # Year only (e.g. 2023)
        m_yr = re.search(r"\b(20\d{2}|19\d{2})\b", text)
        if m_yr:
            yr = int(m_yr.group(1))
            return (date(yr, 1, 1), date(yr, 12, 31))

        return None

    def _find_single_date_in_query(
        self, lower_query: str
    ) -> tuple[date, date, TemporalOperator] | None:
        """Scans the query for single date references."""
        # Check ISO
        m_iso = re.search(r"\b(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})\b", lower_query)
        if m_iso:
            try:
                d = date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
                return (d, d, TemporalOperator.EXACT_DATE)
            except ValueError:
                pass

        # Check DD Month YYYY
        m_dmy = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)\s+(20\d{2}|19\d{2})\b", lower_query
        )
        if m_dmy:
            m_name = m_dmy.group(2).lower()
            if m_name in _MONTH_NAMES:
                try:
                    d = date(int(m_dmy.group(3)), _MONTH_NAMES[m_name], int(m_dmy.group(1)))
                    return (d, d, TemporalOperator.EXACT_DATE)
                except ValueError:
                    pass

        # Check Month YYYY
        m_my = re.search(
            r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
            r"\s+(20\d{2}|19\d{2})\b",
            lower_query,
        )
        if m_my:
            mo = _MONTH_NAMES[m_my.group(1)]
            yr = int(m_my.group(2))
            last_day = self._days_in_month(yr, mo)
            return (date(yr, mo, 1), date(yr, mo, last_day), TemporalOperator.BETWEEN)

        # Check standalone Year (e.g. "in 2023", "2024 results")
        m_yr = re.search(r"\b(?:in\s+|for\s+|from\s+)?(20\d{2}|19\d{2})\b", lower_query)
        if m_yr:
            yr = int(m_yr.group(1))
            return (date(yr, 1, 1), date(yr, 12, 31), TemporalOperator.BETWEEN)

        return None

    def _subtract_months(self, anchor: date, months: int) -> date:
        year = anchor.year
        month = anchor.month - months
        while month < 1:
            month += 12
            year -= 1
        day = min(anchor.day, self._days_in_month(year, month))
        return date(year, month, day)

    def _subtract_years(self, anchor: date, years: int) -> date:
        year = anchor.year - years
        day = min(anchor.day, self._days_in_month(year, anchor.month))
        return date(year, anchor.month, day)

    def _days_in_month(self, year: int, month: int) -> int:
        if month in (1, 3, 5, 7, 8, 10, 12):
            return 31
        if month in (4, 6, 9, 11):
            return 30
        # February leap year
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        return 29 if is_leap else 28

    # -----------------------------------------------------------------------
    # Abnormality & Limit
    # -----------------------------------------------------------------------

    def _detect_abnormality(self, lower_query: str) -> bool:
        """Detects whether query requests abnormal/out-of-range records."""
        abnormal_keywords = (
            "abnormal", "abnormality", "abnormalities", "out of range",
            "out-of-range", "outside normal", "flagged", "high", "elevated",
            "low", "critical", "borderline", "kharab", "aswabhavik", "gadbad",
        )
        return any(re.search(rf"\b{re.escape(kw)}\b", lower_query) for kw in abnormal_keywords)

    def _extract_limit(self, lower_query: str) -> int | None:
        """Extracts observation count limit (e.g. 'last 3 tests' -> 3, 'last 3 HbA1c results' -> 3)."""
        pattern = (
            r"\b(?:last|past|previous|latest)\s+"
            r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
            r"(?:[a-zA-Z0-9_\-\/ ]*?\s+)?"
            r"(?:tests?|panels?|readings?|measurements?|reports?|values?|results?|records?|draws?|points?|observations?)\b"
        )
        m = re.search(pattern, lower_query)
        if m:
            val_str = m.group(1)
            return _NUMBER_WORDS.get(val_str, int(val_str) if val_str.isdigit() else None)

        pattern_inv = (
            r"\b(\d+|one|two|three|four|five)\s+"
            r"(?:most\s+recent|latest)\s+"
            r"(?:[a-zA-Z0-9_\-\/ ]*?\s+)?"
            r"(?:tests?|panels?|readings?|measurements?|reports?|values?|results?|observations?)\b"
        )
        m_inv = re.search(pattern_inv, lower_query)
        if m_inv:
            val_str = m_inv.group(1)
            return _NUMBER_WORDS.get(val_str, int(val_str) if val_str.isdigit() else None)

        return None

    # -----------------------------------------------------------------------
    # Intent and Comparison Resolution
    # -----------------------------------------------------------------------

    def _resolve_intent_and_comparison(
        self,
        clean_query: str,
        lower_query: str,
        analyte_info: dict[str, Any],
        temp_info: dict[str, Any],
        limit_val: int | None,
        is_abnormal_request: bool,
    ) -> tuple[QueryIntent, ComparisonTarget | None]:
        """
        Determines the primary retrieval/reasoning intent and comparison target.
        Applies deterministic clinical precedence rules.
        """
        has_analyte = analyte_info["canonical"] is not None
        has_unresolved = bool(analyte_info["unresolved_terms"])
        has_personal_pronoun = bool(
            re.search(r"\b(my|mine|mera|meri|mere|i|me|mujhe)\b", lower_query)
        )

        # 1. Guideline / Definition intent:
        # e.g., "What is normal HbA1c?", "What does high LDL mean?", "Normal range of TSH"
        guideline_triggers = (
            "what is a normal", "what is the normal", "what is normal",
            "normal range", "normal levels", "reference range", "normal values",
            "what does high", "what does low", "why does", "what causes",
            "guidelines for", "definition of", "what is", "what are",
        )
        is_guideline = any(lower_query.startswith(g) or f" {g} " in f" {lower_query} " for g in guideline_triggers)
        if is_guideline and not has_personal_pronoun:
            # Questions like "What is HbA1c?" or "What is normal HbA1c?" -> DEFINITION_GUIDELINE
            return (QueryIntent.DEFINITION_GUIDELINE, None)

        # 2. Trend intent (evaluated before general comparison triggers so 'changed over time' -> TREND)
        # e.g., "is my creatinine increasing?", "hemoglobin trend over time", "how has my HbA1c changed over time?"
        trend_triggers = (
            "trend", "trending", "trajectory", "progression", "pattern",
            "over time", "increasing", "decreasing", "rising", "falling",
            "going up", "going down", "improved", "worsened", "deteriorating",
            "badh raha hai", "ghat raha hai", "sudhaar", "girawat",
        )
        if any(t in lower_query for t in trend_triggers):
            return (QueryIntent.TREND, None)

        # 3. Comparison / Predecessor intent
        # e.g., "compare my cholesterol in 2023 vs 2024", "compare from 2022-02-10 with 2024-03-30",
        # "What was my previous HbA1c reading before the latest one?", "show previous test"
        comp_triggers = (
            "compare", "comparison", " vs ", " versus ", "changed since",
            "change from", "difference between", "how has it changed",
            "compared to", "how has my", "variation", "kaisa badla",
            "before the latest", "prior to the latest", "reading before", "test before",
        )
        is_comparison = any(t in lower_query for t in comp_triggers)
        if not is_comparison and limit_val is None:
            if re.search(r"\b(?:previous|prior)\b(?:\s+\w+)?\s+(?:reading|result|test|measurement|value|report)\b", lower_query):
                is_comparison = True
            elif re.search(r"\b(?:previous|prior)\b.*\b(?:before|latest|recent)\b", lower_query):
                is_comparison = True

        if is_comparison and limit_val is None:
            target = ComparisonTarget.PREVIOUS
            if re.search(r"\b(20\d{2})\s*(?:vs|versus|and)\s*(20\d{2})\b", lower_query) or (
                temp_info.get("start_date") and temp_info.get("end_date")
            ):
                target = ComparisonTarget.PERIOD
            elif re.search(r"\b(baseline|initial|first\s+test|earliest)\b", lower_query):
                target = ComparisonTarget.BASELINE
            elif re.search(r"\b(historical|history|average|usual)\b", lower_query):
                target = ComparisonTarget.HISTORICAL
            return (QueryIntent.COMPARISON, target)

        # 4. Last-N intent
        if limit_val is not None:
            return (QueryIntent.LAST_N, None)

        # 5. Pure Abnormality intent (no specific analyte or asking generally)
        if is_abnormal_request and not has_analyte and not has_unresolved:
            return (QueryIntent.ABNORMALITY, None)

        # If asking about abnormalities with an analyte (e.g. "show my high cholesterol readings")
        if is_abnormal_request and not temp_info.get("start_date"):
            # If no date bound, ask for abnormalities in that analyte
            return (QueryIntent.ABNORMALITY, None)

        # 6. Historical intent (bounded by date or asking for past records)
        if temp_info.get("start_date") or temp_info.get("relative_window"):
            return (QueryIntent.HISTORICAL, None)

        past_record_triggers = (
            "history", "records", "all my", "all readings", "past results",
            "past records", "purani report", "purane test",
        )
        if any(t in lower_query for t in past_record_triggers):
            return (QueryIntent.HISTORICAL, None)

        # 7. Current value intent
        # "latest", "current", "recent", "what is my sugar", "mera sugar kitna hai"
        current_triggers = (
            "latest", "current", "recent", "most recent", "last", "now", "today",
            "abhi", "taza", "aakhri", "pichla",
        )
        if any(t in lower_query for t in current_triggers) or has_personal_pronoun:
            return (QueryIntent.CURRENT_VALUE, None)

        # If has analyte but no specific qualifiers, default to CURRENT_VALUE
        if has_analyte or has_unresolved:
            return (QueryIntent.CURRENT_VALUE, None)

        # Default fallback
        return (QueryIntent.DEFINITION_GUIDELINE, None)

    # -----------------------------------------------------------------------
    # Temporal Operator Resolution
    # -----------------------------------------------------------------------

    def _resolve_temporal_operator(
        self,
        intent: QueryIntent,
        temp_info: dict[str, Any],
        limit_val: int | None,
    ) -> TemporalOperator:
        """Resolves the final temporal operator based on intent and constraints."""
        if temp_info.get("explicit_operator"):
            return temp_info["explicit_operator"]

        if limit_val is not None or intent == QueryIntent.LAST_N:
            return TemporalOperator.LAST_N

        if intent == QueryIntent.CURRENT_VALUE:
            return TemporalOperator.LATEST

        if intent in (QueryIntent.TREND, QueryIntent.COMPARISON):
            return TemporalOperator.ALL_TIME

        if intent == QueryIntent.DEFINITION_GUIDELINE:
            return TemporalOperator.NONE

        if intent == QueryIntent.ABNORMALITY:
            return TemporalOperator.ALL_TIME

        return TemporalOperator.NONE

    # -----------------------------------------------------------------------
    # Confidence Scoring
    # -----------------------------------------------------------------------

    def _compute_confidence(
        self,
        clean_query: str,
        lower_query: str,
        intent: QueryIntent,
        analyte_info: dict[str, Any],
        temp_info: dict[str, Any],
        limit_val: int | None,
    ) -> float:
        """Computes a deterministic parse confidence in range [0.0, 1.0]."""
        score = 0.0

        # Base syntactic credibility
        tokens = [w for w in re.split(r"\s+", lower_query) if w]
        if len(tokens) >= 2:
            score += 0.3
        elif len(tokens) == 1:
            score += 0.15

        # Analyte recognized
        if analyte_info["canonical"]:
            score += 0.4
        elif analyte_info["unresolved_terms"]:
            # Ambiguous/unknown analyte: partial credit for identifying slot, penalize certainty
            score += 0.15

        # Intent specificity & temporal bounds
        if intent in (QueryIntent.TREND, QueryIntent.COMPARISON, QueryIntent.LAST_N):
            score += 0.2
        elif temp_info.get("start_date") or temp_info.get("relative_window"):
            score += 0.2
        elif intent == QueryIntent.CURRENT_VALUE and analyte_info["canonical"]:
            score += 0.2
        elif intent == QueryIntent.DEFINITION_GUIDELINE and len(tokens) >= 3:
            score += 0.2
        elif intent == QueryIntent.ABNORMALITY:
            score += 0.2

        # Penalize ambiguous short queries lacking clinical concept
        if not analyte_info["canonical"] and intent != QueryIntent.DEFINITION_GUIDELINE:
            score = min(score, 0.5)

        # Cap between 0.05 and 1.0
        return round(max(0.05, min(1.0, score)), 4)
