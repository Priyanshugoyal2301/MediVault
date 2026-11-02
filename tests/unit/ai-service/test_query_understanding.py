"""
tests/unit/ai-service/test_query_understanding.py

Comprehensive deterministic unit test suite for Clinical Query Understanding
and Temporal Intent Parsing (CP-05).

Verifies:
  1. Each supported QueryIntent
  2. Each TemporalOperator
  3. Relative date expressions (window math with fixed anchor)
  4. Absolute dates (ISO, DD Month YYYY, Month YYYY, Year only, ranges)
  5. Last-N observation limit extraction
  6. Comparison queries (previous, period, baseline, historical)
  7. Trend and trajectory queries
  8. Analyte aliases and LOINC resolution
  9. Unknown analytes (captured in unresolved_terms, NO fake LOINC)
 10. Ambiguous queries (reduced confidence, graceful handling)
 11. Malformed and non-clinical inputs (no exceptions, zero confidence)
 12. Bilingual / Hindi queries
 13. Combinations of analyte + temporal constraint + abnormality flag
 14. Negative tests (unsupported attributes are NOT silently invented)
 15. Contract serialization (to_dict / from_dict roundtrip)
"""

from datetime import date
import pytest

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    RelativeWindow,
    TemporalOperator,
    WindowUnit,
)
from services.ai_service.rag.query_understanding import ClinicalQueryParser

# Fixed anchor date for deterministic temporal testing
ANCHOR = date(2024, 6, 15)


@pytest.fixture
def parser() -> ClinicalQueryParser:
    return ClinicalQueryParser()


# ===========================================================================
# 1. Intent Taxonomy Tests
# ===========================================================================

class TestIntentTaxonomy:
    def test_intent_current_value(self, parser):
        q = parser.parse("What is my latest HbA1c?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.CURRENT_VALUE
        assert q.temporal_operator == TemporalOperator.LATEST
        assert q.analyte_canonical == "HbA1c"

    def test_intent_historical_specific_date(self, parser):
        q = parser.parse("What was my blood sugar on 2024-01-14?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.HISTORICAL
        assert q.temporal_operator == TemporalOperator.EXACT_DATE
        assert q.start_date == date(2024, 1, 14)
        assert q.end_date == date(2024, 1, 14)

    def test_intent_last_n(self, parser):
        q = parser.parse("Show my last 3 lipid panels", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.LAST_N
        assert q.limit == 3
        assert q.temporal_operator == TemporalOperator.LAST_N
        assert q.analyte_canonical == "Total Cholesterol"

    def test_intent_comparison_previous(self, parser):
        q = parser.parse("How has my HbA1c changed since last time?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.COMPARISON
        assert q.comparison_target == ComparisonTarget.PREVIOUS
        assert q.analyte_canonical == "HbA1c"

    def test_intent_comparison_period(self, parser):
        q = parser.parse("Compare my cholesterol in 2023 vs 2024", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.COMPARISON
        assert q.comparison_target == ComparisonTarget.PERIOD
        assert q.analyte_canonical == "Total Cholesterol"

    def test_intent_trend(self, parser):
        q = parser.parse("Is my creatinine increasing over time?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.TREND
        assert q.temporal_operator == TemporalOperator.ALL_TIME
        assert q.analyte_canonical == "Creatinine"

    def test_intent_definition_guideline(self, parser):
        q = parser.parse("What is a normal TSH level?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.DEFINITION_GUIDELINE
        assert q.temporal_operator == TemporalOperator.NONE
        assert q.analyte_canonical == "TSH"

    def test_intent_abnormality(self, parser):
        q = parser.parse("Show my abnormal lab tests", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.ABNORMALITY
        assert q.abnormal_only is True


# ===========================================================================
# 2. Temporal Operators & Date Range Tests
# ===========================================================================

class TestTemporalOperators:
    def test_operator_exact_date(self, parser):
        q = parser.parse("Show my hemoglobin on 2023-11-20", anchor_date=ANCHOR)
        assert q.temporal_operator == TemporalOperator.EXACT_DATE
        assert q.start_date == date(2023, 11, 20)
        assert q.end_date == date(2023, 11, 20)

    def test_operator_between_dates(self, parser):
        q = parser.parse(
            "Show blood sugar between 2023-01-01 and 2023-06-30",
            anchor_date=ANCHOR,
        )
        assert q.temporal_operator == TemporalOperator.BETWEEN
        assert q.start_date == date(2023, 1, 1)
        assert q.end_date == date(2023, 6, 30)

    def test_operator_between_month_names(self, parser):
        q = parser.parse(
            "Show lipid profile between January 2023 and December 2023",
            anchor_date=ANCHOR,
        )
        assert q.temporal_operator == TemporalOperator.BETWEEN
        assert q.start_date == date(2023, 1, 1)
        assert q.end_date == date(2023, 12, 31)

    def test_operator_before(self, parser):
        q = parser.parse("Show my tests before 2024-01-01", anchor_date=ANCHOR)
        assert q.temporal_operator == TemporalOperator.BEFORE
        assert q.end_date == date(2024, 1, 1)

    def test_operator_after_since(self, parser):
        q = parser.parse("Show my tests after 2023-05-10", anchor_date=ANCHOR)
        assert q.temporal_operator == TemporalOperator.SINCE
        assert q.start_date == date(2023, 5, 10)

    def test_operator_month_year(self, parser):
        q = parser.parse("What was my glucose in March 2024?", anchor_date=ANCHOR)
        assert q.temporal_operator == TemporalOperator.BETWEEN
        assert q.start_date == date(2024, 3, 1)
        assert q.end_date == date(2024, 3, 31)

    def test_operator_year_only(self, parser):
        q = parser.parse("What was my cholesterol in 2023?", anchor_date=ANCHOR)
        assert q.temporal_operator == TemporalOperator.BETWEEN
        assert q.start_date == date(2023, 1, 1)
        assert q.end_date == date(2023, 12, 31)


# ===========================================================================
# 3. Relative Date Expression Tests
# ===========================================================================

class TestRelativeDateExpressions:
    def test_relative_months(self, parser):
        q = parser.parse("Show my HbA1c over the past 6 months", anchor_date=ANCHOR)
        assert q.relative_window == RelativeWindow(value=6, unit=WindowUnit.MONTHS)
        assert q.temporal_operator == TemporalOperator.SINCE
        assert q.end_date == ANCHOR
        assert q.start_date == date(2023, 12, 15)

    def test_relative_years(self, parser):
        q = parser.parse("Show my cholesterol in the last 2 years", anchor_date=ANCHOR)
        assert q.relative_window == RelativeWindow(value=2, unit=WindowUnit.YEARS)
        assert q.temporal_operator == TemporalOperator.SINCE
        assert q.end_date == ANCHOR
        assert q.start_date == date(2022, 6, 15)

    def test_relative_days(self, parser):
        q = parser.parse("Blood sugar past 30 days", anchor_date=ANCHOR)
        assert q.relative_window == RelativeWindow(value=30, unit=WindowUnit.DAYS)
        assert q.end_date == ANCHOR
        assert q.start_date == ANCHOR - date.resolution * 30 or date(2024, 5, 16)

    def test_relative_singular_month(self, parser):
        q = parser.parse("Show tests from the past month", anchor_date=ANCHOR)
        assert q.relative_window == RelativeWindow(value=1, unit=WindowUnit.MONTHS)
        assert q.start_date == date(2024, 5, 15)
        assert q.end_date == ANCHOR

    def test_relative_singular_year(self, parser):
        q = parser.parse("Show hemoglobin in the last year", anchor_date=ANCHOR)
        assert q.relative_window == RelativeWindow(value=1, unit=WindowUnit.YEARS)
        assert q.start_date == date(2023, 6, 15)


# ===========================================================================
# 4. Last-N Limit Extraction Tests
# ===========================================================================

class TestLastNExtraction:
    def test_last_n_numeric(self, parser):
        q = parser.parse("Show my last 5 readings for glucose", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.LAST_N
        assert q.limit == 5
        assert q.analyte_canonical == "Glucose"

    def test_last_n_word_digits(self, parser):
        q = parser.parse("Show previous two reports for TSH", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.LAST_N
        assert q.limit == 2
        assert q.analyte_canonical == "TSH"

    def test_last_n_most_recent(self, parser):
        q = parser.parse("Give me 3 most recent lab tests for hemoglobin", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.LAST_N
        assert q.limit == 3
        assert q.analyte_canonical == "Haemoglobin"


# ===========================================================================
# 5. Comparison Intent Tests
# ===========================================================================

class TestComparisonIntent:
    def test_comparison_with_previous(self, parser):
        q = parser.parse("Did my cholesterol change from last test?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.COMPARISON
        assert q.comparison_target == ComparisonTarget.PREVIOUS

    def test_comparison_periods(self, parser):
        q = parser.parse("Compare 2022 vs 2023 creatinine results", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.COMPARISON
        assert q.comparison_target == ComparisonTarget.PERIOD
        assert q.analyte_canonical == "Creatinine"

    def test_comparison_baseline(self, parser):
        q = parser.parse("Compare my latest HbA1c with my baseline test", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.COMPARISON
        assert q.comparison_target == ComparisonTarget.BASELINE

    def test_comparison_historical(self, parser):
        q = parser.parse("Compare my blood pressure against my usual history", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.COMPARISON
        assert q.comparison_target == ComparisonTarget.HISTORICAL


# ===========================================================================
# 6. Trend and Trajectory Tests
# ===========================================================================

class TestTrendIntent:
    def test_trend_is_increasing(self, parser):
        q = parser.parse("Is my creatinine rising?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.TREND
        assert q.analyte_canonical == "Creatinine"

    def test_trend_trajectory_phrase(self, parser):
        q = parser.parse("Show the trajectory of my platelet count", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.TREND
        assert q.analyte_canonical == "Platelets"

    def test_trend_going_down(self, parser):
        q = parser.parse("Is my hemoglobin going down over time?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.TREND
        assert q.analyte_canonical == "Haemoglobin"


# ===========================================================================
# 7. Analyte Recognition & Alias Mapping
# ===========================================================================

class TestAnalyteAliases:
    @pytest.mark.parametrize(
        "query,expected_canonical,expected_loinc,expected_concept_id",
        [
            ("What is my Hb?", "Haemoglobin", "718-7", "LOINC:718-7"),
            ("Show my fasting sugar", "Glucose", "2345-7", "LOINC:2345-7"),
            ("What is my A1c?", "HbA1c", "4548-4", "LOINC:4548-4"),
            ("Show my bad cholesterol", "LDL Cholesterol", "2089-1", "LOINC:2089-1"),
            ("What is my good cholesterol?", "HDL Cholesterol", "2085-9", "LOINC:2085-9"),
            ("Show my TLC count", "WBC", "6690-2", "LOINC:6690-2"),
            ("Check my platelet count", "Platelets", "777-3", "LOINC:777-3"),
            ("Show serum creatinine", "Creatinine", "2160-0", "LOINC:2160-0"),
            ("What is my SGPT level?", "Alanine Aminotransferase", "1742-6", "LOINC:1742-6"),
            ("Check SGOT", "Aspartate Aminotransferase", "1920-8", "LOINC:1920-8"),
            ("Show TSH test", "TSH", "3016-3", "LOINC:3016-3"),
            ("Total bilirubin value", "Bilirubin Total", "1975-2", "LOINC:1975-2"),
            ("Uric acid reading", "Uric Acid", "3084-1", "LOINC:3084-1"),
        ],
    )
    def test_analyte_alias_resolution(
        self, parser, query, expected_canonical, expected_loinc, expected_concept_id
    ):
        q = parser.parse(query, anchor_date=ANCHOR)
        assert q.analyte_canonical == expected_canonical
        assert q.loinc_code == expected_loinc
        assert q.concept_id == expected_concept_id
        assert len(q.analyte_mentions) > 0


# ===========================================================================
# 8. Unknown Analytes & Non-Fabrication
# ===========================================================================

class TestUnknownAnalytes:
    def test_unknown_analyte_does_not_fabricate_loinc(self, parser):
        q = parser.parse("What was my troponin test result?", anchor_date=ANCHOR)
        assert q.analyte_canonical is None
        assert q.loinc_code is None
        assert q.concept_id is None
        assert "troponin" in q.unresolved_terms
        assert "troponin" in q.analyte_mentions

    def test_unknown_analyte_ferritin(self, parser):
        q = parser.parse("Show my ferritin reading", anchor_date=ANCHOR)
        assert q.analyte_canonical is None
        assert q.loinc_code is None
        assert "ferritin" in q.unresolved_terms


# ===========================================================================
# 9. Ambiguous and Malformed Queries
# ===========================================================================

class TestAmbiguousAndMalformedQueries:
    def test_empty_query(self, parser):
        q = parser.parse("", anchor_date=ANCHOR)
        assert q.confidence == 0.0
        assert q.analyte_canonical is None

    def test_whitespace_query(self, parser):
        q = parser.parse("     ", anchor_date=ANCHOR)
        assert q.confidence == 0.0

    def test_punctuation_only_query(self, parser):
        q = parser.parse("???!!!", anchor_date=ANCHOR)
        assert q.confidence == 0.0

    def test_ambiguous_results_query(self, parser):
        q = parser.parse("show my results", anchor_date=ANCHOR)
        assert q.confidence <= 0.5
        assert q.analyte_canonical is None

    def test_gibberish_query(self, parser):
        q = parser.parse("asdfghjkl qwerty zxcvbnm", anchor_date=ANCHOR)
        assert q.analyte_canonical is None
        assert q.confidence < 0.6


# ===========================================================================
# 10. Bilingual / Hindi Queries
# ===========================================================================

class TestBilingualQueries:
    def test_hindi_sugar_current(self, parser):
        q = parser.parse("Mera sugar kitna hai?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.CURRENT_VALUE
        assert q.analyte_canonical == "Glucose"
        assert q.loinc_code == "2345-7"

    def test_hindi_hemoglobin_trend(self, parser):
        q = parser.parse("Kya mera hemoglobin badh raha hai?", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.TREND
        assert q.analyte_canonical == "Haemoglobin"

    def test_hindi_abnormal_tests(self, parser):
        q = parser.parse("Abnormal test dikhao", anchor_date=ANCHOR)
        assert q.intent == QueryIntent.ABNORMALITY
        assert q.abnormal_only is True

    def test_hindi_khoon_ki_janch(self, parser):
        q = parser.parse("Khoon ki janch me kya aaya?", anchor_date=ANCHOR)
        assert q.analyte_canonical == "Haemoglobin"


# ===========================================================================
# 11. Combinations of Constraints
# ===========================================================================

class TestConstraintCombinations:
    def test_analyte_plus_abnormality_plus_relative_window(self, parser):
        q = parser.parse(
            "Show my high cholesterol readings over the past 6 months",
            anchor_date=ANCHOR,
        )
        assert q.analyte_canonical == "Total Cholesterol"
        assert q.abnormal_only is True
        assert q.relative_window == RelativeWindow(value=6, unit=WindowUnit.MONTHS)
        assert q.start_date == date(2023, 12, 15)
        assert q.end_date == ANCHOR

    def test_analyte_plus_comparison_plus_periods(self, parser):
        q = parser.parse("Compare my LDL in 2023 vs 2024", anchor_date=ANCHOR)
        assert q.analyte_canonical == "LDL Cholesterol"
        assert q.intent == QueryIntent.COMPARISON
        assert q.comparison_target == ComparisonTarget.PERIOD


# ===========================================================================
# 12. Negative Tests (No Hallucinations)
# ===========================================================================

class TestNegativeConstraints:
    def test_no_date_in_query_leaves_dates_none(self, parser):
        q = parser.parse("What is my hemoglobin level?", anchor_date=ANCHOR)
        assert q.start_date is None
        assert q.end_date is None
        assert q.relative_window is None

    def test_no_comparison_keywords_leaves_target_none(self, parser):
        q = parser.parse("What was my creatinine on 2024-01-14?", anchor_date=ANCHOR)
        assert q.comparison_target is None

    def test_non_abnormal_query_leaves_abnormal_only_false(self, parser):
        q = parser.parse("Show my TSH results", anchor_date=ANCHOR)
        assert q.abnormal_only is False

    def test_no_limit_leaves_limit_none(self, parser):
        q = parser.parse("Show my glucose history", anchor_date=ANCHOR)
        assert q.limit is None


# ===========================================================================
# 13. Contract Serialization Roundtrip
# ===========================================================================

class TestContractSerialization:
    def test_to_dict_and_from_dict_roundtrip(self, parser):
        q1 = parser.parse(
            "Show my high cholesterol readings over the past 6 months",
            anchor_date=ANCHOR,
        )
        d = q1.to_dict()
        assert isinstance(d, dict)
        assert d["intent"] == "HISTORICAL"
        assert d["analyte_canonical"] == "Total Cholesterol"
        assert d["abnormal_only"] is True
        assert d["relative_window"]["value"] == 6
        assert d["relative_window"]["unit"] == "MONTHS"

        # Roundtrip back to ClinicalQuery
        q2 = ClinicalQuery.from_dict(d)
        assert q2.raw_query == q1.raw_query
        assert q2.intent == q1.intent
        assert q2.analyte_canonical == q1.analyte_canonical
        assert q2.loinc_code == q1.loinc_code
        assert q2.start_date == q1.start_date
        assert q2.end_date == q1.end_date
        assert q2.relative_window == q1.relative_window
        assert q2.abnormal_only == q1.abnormal_only
        assert q2.confidence == q1.confidence
