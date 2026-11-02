"""
tests/unit/ai-service/test_date_parser.py

Unit tests for clinical date extraction and semantic precedence engine (CP-02).

Required cases:
  1. ISO date
  2. slash-separated date
  3. hyphen-separated date
  4. textual month date
  5. labelled collection date
  6. multiple dates in one report
  7. collection date + report date together
  8. ambiguous/missing date
  9. malformed date
  10. multiple candidate dates with precedence rules
  + ReportParser integration tests (Representation B: document date & observation-specific date)
"""

from datetime import date
from decimal import Decimal

import pytest

from services.ai_service.parsers.dates import (
    CONFIDENCE_BY_TYPE,
    DateCandidate,
    SemanticDateType,
    extract_dates,
    extract_document_date,
    extract_line_observation_date,
    parse_date_string,
    select_clinical_date,
)
from services.ai_service.parsers.report_parser import ReportParser


class TestDateFormatsAndParsing:
    """Tests 1-4: Format parsing support."""

    def test_case_1_iso_date(self):
        """1. ISO date: YYYY-MM-DD."""
        d = parse_date_string("2024-05-18")
        assert d == date(2024, 5, 18)

        # Dot and slash variant for ISO ordering
        d_slash = parse_date_string("2024/05/18")
        assert d_slash == date(2024, 5, 18)

    def test_case_2_slash_separated_date(self):
        """2. Slash-separated date: DD/MM/YYYY."""
        d = parse_date_string("18/05/2024")
        assert d == date(2024, 5, 18)

        # Disambiguated single-digit day/month
        d2 = parse_date_string("03/09/2023")
        assert d2 == date(2023, 9, 3)

    def test_case_3_hyphen_separated_date(self):
        """3. Hyphen-separated date: DD-MM-YYYY."""
        d = parse_date_string("18-05-2024")
        assert d == date(2024, 5, 18)

        d2 = parse_date_string("05-11-2022")
        assert d2 == date(2022, 11, 5)

    def test_case_4_textual_month_date(self):
        """4. Textual month date in multiple common variations."""
        # DD Mon YYYY
        assert parse_date_string("18 May 2024") == date(2024, 5, 18)
        assert parse_date_string("18-May-2024") == date(2024, 5, 18)
        assert parse_date_string("18/May/2024") == date(2024, 5, 18)
        assert parse_date_string("18 January 2024") == date(2024, 1, 18)
        assert parse_date_string("18-JAN-2024") == date(2024, 1, 18)

        # Mon DD, YYYY
        assert parse_date_string("May 18, 2024") == date(2024, 5, 18)
        assert parse_date_string("Oct 05, 2023") == date(2023, 10, 5)
        assert parse_date_string("September 12, 2022") == date(2022, 9, 12)

        # YYYY Mon DD
        assert parse_date_string("2024 May 18") == date(2024, 5, 18)
        assert parse_date_string("2024-Jan-15") == date(2024, 1, 15)


class TestSemanticClassificationAndPrecedence:
    """Tests 5-10: Semantic labelling, precedence hierarchy, rejection, and edge cases."""

    def test_case_5_labelled_collection_date(self):
        """5. Labelled collection date classification and high confidence."""
        text = "Patient: Sunita Sharma\nSample Collection Date: 18/05/2024\nHaemoglobin: 13.5 g/dL"
        cand = extract_document_date(text)
        assert cand is not None
        assert cand.date_value == date(2024, 5, 18)
        assert cand.date_iso == "2024-05-18"
        assert cand.date_type == SemanticDateType.COLLECTION
        assert cand.confidence == CONFIDENCE_BY_TYPE[SemanticDateType.COLLECTION]
        assert "Collection" in cand.label_text

    def test_case_6_multiple_dates_in_one_report(self):
        """6. Multiple dates in one report are all correctly classified."""
        report = """
        APOLLO DIAGNOSTICS
        Registration Date: 10/05/2024
        Sample Collection Date: 11/05/2024
        Date of Test: 12/05/2024
        Result Date: 13/05/2024
        Report Date: 14/05/2024
        Billing Date: 15/05/2024
        """
        cands = extract_dates(report)
        types = {c.date_type for c in cands}
        assert SemanticDateType.ADMINISTRATIVE in types
        assert SemanticDateType.COLLECTION in types
        assert SemanticDateType.TEST in types
        assert SemanticDateType.RESULT in types
        assert SemanticDateType.REPORT in types

    def test_case_7_collection_date_plus_report_date_together(self):
        """7. Collection date + report date together: collection date takes deterministic precedence."""
        report = """
        METROPOLIS HEALTHCARE
        Collection Date: 11/05/2024
        Report Date: 14/05/2024
        Haemoglobin : 14.2 g/dL (13.0-17.0)
        """
        doc_date = extract_document_date(report)
        assert doc_date is not None
        assert doc_date.date_value == date(2024, 5, 11)
        assert doc_date.date_iso == "2024-05-11"
        assert doc_date.date_type == SemanticDateType.COLLECTION

    def test_case_8_ambiguous_or_missing_date(self):
        """8. Ambiguous/missing date: returns None (preserves ambiguity rather than inventing dates)."""
        # No date at all
        assert extract_document_date("No dates mentioned in this report header.") is None

        # Administrative only (e.g. billing or registration only)
        admin_only = """
        Registration Date: 10/05/2024
        Billing Date: 10/05/2024
        Test: Haemoglobin 12.0
        """
        assert extract_document_date(admin_only) is None

    def test_case_9_malformed_date(self):
        """9. Malformed dates: invalid day, invalid month, or unparseable formats are rejected."""
        assert parse_date_string("32/01/2024") is None      # day 32
        assert parse_date_string("15/13/2024") is None      # month 13
        assert parse_date_string("29/02/2023") is None      # not a leap year
        assert parse_date_string("99-99-9999") is None
        assert parse_date_string("random-text-here") is None

        report = "Report Date: 99/99/9999\nCollection Date: 32/01/2024"
        assert extract_document_date(report) is None

    def test_case_10_multiple_candidate_dates_precedence_rules(self):
        """
        10. Deterministic precedence policy:
            Collection (1) > Test (2) > Result (3) > Report (4) > Unlabelled (5).
            Administrative dates are rejected.
        """
        c_coll = DateCandidate(date(2024, 1, 1), "2024-01-01", SemanticDateType.COLLECTION, 0.95, "coll")
        c_test = DateCandidate(date(2024, 1, 2), "2024-01-02", SemanticDateType.TEST, 0.90, "test")
        c_res = DateCandidate(date(2024, 1, 3), "2024-01-03", SemanticDateType.RESULT, 0.85, "res")
        c_rep = DateCandidate(date(2024, 1, 4), "2024-01-04", SemanticDateType.REPORT, 0.75, "rep")
        c_unlab = DateCandidate(date(2024, 1, 5), "2024-01-05", SemanticDateType.UNLABELLED, 0.50, "unlab")
        c_adm = DateCandidate(date(2024, 1, 6), "2024-01-06", SemanticDateType.ADMINISTRATIVE, 0.0, "adm")

        # Collection beats Test
        assert select_clinical_date([c_test, c_coll]) == c_coll
        # Test beats Result
        assert select_clinical_date([c_res, c_test]) == c_test
        # Result beats Report
        assert select_clinical_date([c_rep, c_res]) == c_res
        # Report beats Unlabelled
        assert select_clinical_date([c_unlab, c_rep]) == c_rep
        # Unlabelled is used when no clinical label is present
        assert select_clinical_date([c_unlab]) == c_unlab
        # Administrative is completely rejected
        assert select_clinical_date([c_adm]) is None
        assert select_clinical_date([c_adm, c_unlab]) == c_unlab


class StubOcr:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        return self._text


class TestReportParserDateIntegration:
    """Integration of date engine into ReportParser (Representation B)."""

    def test_values_inherit_document_date(self):
        report_text = """
        DR LAL PATHLABS
        Sample Collection Date: 15/01/2024
        Report Date: 16/01/2024

        COMPLETE BLOOD COUNT (CBC)
        Haemoglobin : 14.5 g/dL (13.0 - 17.0)
        Platelets   : 250000 /cumm (150000 - 400000)
        """
        parser = ReportParser(ocr=StubOcr(report_text))
        values = parser.parse(b"", "application/pdf")

        assert len(values) == 2
        for v in values:
            assert v.date_of_test == "2024-01-15"
            assert v.date_type == "collection"
            assert v.date_confidence == 0.95

    def test_observation_specific_date_overrides_document_date(self):
        """Representation B: observation-specific date overrides document date."""
        report_text = """
        CITY DIAGNOSTIC CENTRE
        Collection Date: 10/01/2024

        Haemoglobin : 14.0 g/dL (13.0 - 17.0)
        Total Cholesterol : 210 mg/dL (< 200) Tested: 12/01/2024
        """
        parser = ReportParser(ocr=StubOcr(report_text))
        values = parser.parse(b"", "application/pdf")

        hb = next(v for v in values if v.test_name == "Haemoglobin")
        chol = next(v for v in values if v.test_name == "Total Cholesterol")

        # Haemoglobin inherits document collection date (2024-01-10)
        assert hb.date_of_test == "2024-01-10"
        assert hb.date_type == "collection"

        # Total Cholesterol has observation-specific date (2024-01-12)
        assert chol.date_of_test == "2024-01-12"
        assert chol.date_type == "test"
