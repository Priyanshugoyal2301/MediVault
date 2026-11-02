"""
tests/unit/research-data/test_longitudinal_selection.py

Unit test suite for Longitudinal Evidence Selection & Trajectory Reasoning (CP-08).
Verifies:
  1. Minimal sufficient trajectory selection (baseline, endpoint, inflection point)
  2. Baseline + endpoint selection (2-point trajectories)
  3. Meaningful intermediate selection (inflection point)
  4. Redundant cluster suppression (tight cluster suppressed, milestone retained)
  5. previous_value exact predecessor preservation (predecessor strictly preserved, baseline anchor not substituted)
  6. current_value exact latest preservation (latest observation primary)
  7. last-N preservation (exact requested N observations)
  8. Date-window preservation (hard temporal gating respected)
  9. Multi-patient isolation
  10. Multi-analyte isolation
  11. Single observation trajectory handling
  12. Zero baseline safe handling (no ZeroDivisionError)
  13. Duplicate timestamps safe handling
  14. Missing and non-numeric values safe handling
  15. Deterministic chronological ordering
  16. Provenance and evidence_id preservation
  17. Empty candidate pool handling
  18. Contradictory / non-monotonic trajectory fact extraction
  19. Adversarial test: Naive baseline + endpoint fails to capture acute intermediate spike
  20. LongitudinalEvidencePackage serialization (.to_dict())
"""

from __future__ import annotations

import pytest

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    TemporalOperator,
)
from packages.research_data.retrieval.contract import RetrievalResult
from packages.research_data.retrieval.longitudinal_selection import (
    LongitudinalEvidencePackage,
    LongitudinalEvidenceSelector,
)


def make_res(
    evidence_id: str,
    date_str: str,
    value: float | str | None,
    score: float = 0.9,
    patient_id: str = "p1",
    analyte: str = "HbA1c",
    flag: str = "normal",
    unit: str = "%",
) -> RetrievalResult:
    return RetrievalResult(
        evidence_id=evidence_id,
        patient_id=patient_id,
        score=score,
        rank=0,
        retrieval_method="test",
        analyte_canonical=analyte,
        concept_id="LOINC:4548-4",
        loinc_code="4548-4",
        observation_date=date_str,
        value=value,
        unit=unit,
        flag=flag,
        source_provenance="synthea:sample",
    )


class TestLongitudinalEvidenceSelection:
    @pytest.fixture
    def selector(self) -> LongitudinalEvidenceSelector:
        return LongitudinalEvidenceSelector(cluster_window_days=14.0)

    def test_single_observation_trajectory(self, selector: LongitudinalEvidenceSelector):
        candidates = [make_res("ev_1", "2023-01-01T00:00:00Z", 6.0)]
        query = ClinicalQuery(
            raw_query="What is my HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.selected_evidence_ids == ["ev_1"]
        assert pkg.feature_summaries["observation_count"] == 1
        assert pkg.feature_summaries["direction"] == "stable"
        assert pkg.feature_summaries["absolute_delta"] == 0.0

    def test_two_point_baseline_and_endpoint(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2022-01-01T00:00:00Z", 5.5),
            make_res("ev_2", "2023-01-01T00:00:00Z", 7.0),
        ]
        query = ClinicalQuery(
            raw_query="How has my HbA1c changed?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.selected_evidence_ids == ["ev_1", "ev_2"]
        assert pkg.selection_rationale["ev_1"] == "baseline"
        assert pkg.selection_rationale["ev_2"] == "endpoint"
        assert pkg.feature_summaries["absolute_delta"] == 1.5
        assert pkg.feature_summaries["direction"] == "increased"

    def test_previous_value_preserves_exact_predecessor_not_baseline(
        self, selector: LongitudinalEvidenceSelector
    ):
        """
        CRITICAL CP-08 TEST:
        When a patient has 4 observations over time:
          - ev_1: 2021-01-01 (5.5, baseline)
          - ev_2: 2022-01-01 (6.0)
          - ev_3: 2023-01-01 (6.8, true predecessor)
          - ev_4: 2024-01-01 (7.2, latest)

        For a PREVIOUS_VALUE query:
        The requested predecessor MUST be ev_3 (NOT ev_1 baseline).
        """
        candidates = [
            make_res("ev_1", "2021-01-01T00:00:00Z", 5.5),
            make_res("ev_2", "2022-01-01T00:00:00Z", 6.0),
            make_res("ev_3", "2023-01-01T00:00:00Z", 6.8),
            make_res("ev_4", "2024-01-01T00:00:00Z", 7.2),
        ]
        query = ClinicalQuery(
            raw_query="What was my previous HbA1c reading before the latest?",
            intent=QueryIntent.COMPARISON,
            comparison_target=ComparisonTarget.PREVIOUS,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert "ev_3" in pkg.selected_evidence_ids
        assert pkg.selection_rationale["ev_3"] == "predecessor"
        # ev_1 (baseline) must NOT be selected as predecessor
        assert pkg.selection_rationale.get("ev_1") is None

    def test_current_value_preserves_exact_latest(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2021-01-01T00:00:00Z", 5.5),
            make_res("ev_2", "2022-01-01T00:00:00Z", 6.0),
            make_res("ev_3", "2023-01-01T00:00:00Z", 6.8),
        ]
        query = ClinicalQuery(
            raw_query="What is my most recent HbA1c level?",
            intent=QueryIntent.CURRENT_VALUE,
            temporal_operator=TemporalOperator.LATEST,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.selected_evidence_ids == ["ev_3"]
        assert pkg.selection_rationale["ev_3"] == "latest"

    def test_last_n_observations_preserves_requested_n(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2020-01-01T00:00:00Z", 5.0),
            make_res("ev_2", "2021-01-01T00:00:00Z", 5.5),
            make_res("ev_3", "2022-01-01T00:00:00Z", 6.0),
            make_res("ev_4", "2023-01-01T00:00:00Z", 6.5),
            make_res("ev_5", "2024-01-01T00:00:00Z", 7.0),
        ]
        query = ClinicalQuery(
            raw_query="Show my last 3 HbA1c results.",
            intent=QueryIntent.LAST_N,
            temporal_operator=TemporalOperator.LAST_N,
            limit=3,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.selected_evidence_ids == ["ev_3", "ev_4", "ev_5"]

    def test_first_abnormal_preserves_earliest_abnormal(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2021-01-01T00:00:00Z", 5.4, flag="normal"),
            make_res("ev_2", "2022-01-01T00:00:00Z", 7.2, flag="abnormal"),
            make_res("ev_3", "2023-01-01T00:00:00Z", 8.0, flag="abnormal"),
        ]
        query = ClinicalQuery(
            raw_query="When did my HbA1c first become abnormal?",
            intent=QueryIntent.ABNORMALITY,
            abnormal_only=True,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.selected_evidence_ids == ["ev_2"]
        assert pkg.selection_rationale["ev_2"] == "first_abnormal"

    def test_hard_temporal_exclusion_preserved(self, selector: LongitudinalEvidenceSelector):
        """Candidates with score == 0.0 (filtered out by CP-06 hard bounds) must NEVER be selected."""
        candidates = [
            make_res("ev_in_1", "2023-02-01T00:00:00Z", 6.0, score=0.85),
            make_res("ev_in_2", "2023-03-01T00:00:00Z", 6.2, score=0.90),
            make_res("ev_out", "2021-01-01T00:00:00Z", 5.0, score=0.0),  # Gated out by hard bounds
        ]
        query = ClinicalQuery(
            raw_query="HbA1c between 2023-01-01 and 2023-04-01",
            intent=QueryIntent.HISTORICAL,
            temporal_operator=TemporalOperator.BETWEEN,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert "ev_out" not in pkg.selected_evidence_ids
        assert set(pkg.selected_evidence_ids) == {"ev_in_1", "ev_in_2"}

    def test_redundant_cluster_suppression(self, selector: LongitudinalEvidenceSelector):
        """
        In a trajectory with 8 points where 4 points are in a dense hospital cluster
        (e.g., daily checks over 4 days with minor noise), CP-08 should select
        baseline, endpoint, and suppress the redundant daily cluster.
        """
        candidates = [
            make_res("ev_base", "2021-01-01T00:00:00Z", 5.5),
            # Dense redundant cluster in June 2022
            make_res("ev_c1", "2022-06-01T00:00:00Z", 7.0),
            make_res("ev_c2", "2022-06-02T00:00:00Z", 7.05),
            make_res("ev_c3", "2022-06-03T00:00:00Z", 7.02),
            make_res("ev_c4", "2022-06-04T00:00:00Z", 7.04),
            # Endpoint
            make_res("ev_end", "2023-12-01T00:00:00Z", 6.5),
        ]
        query = ClinicalQuery(
            raw_query="How has my HbA1c changed over time?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates, max_trajectory_evidence=3)

        # Baseline and endpoint must be selected
        assert "ev_base" in pkg.selected_evidence_ids
        assert "ev_end" in pkg.selected_evidence_ids
        # Only one point from the cluster should be selected
        cluster_selected = [
            cid for cid in ("ev_c1", "ev_c2", "ev_c3", "ev_c4")
            if cid in pkg.selected_evidence_ids
        ]
        assert len(cluster_selected) <= 1

    def test_adversarial_naive_baseline_endpoint_misses_inflection_spike(
        self, selector: LongitudinalEvidenceSelector
    ):
        """
        ADVERSARIAL TEST:
        A patient has:
          - 2021-01-01: 6.0% (baseline)
          - 2022-06-01: 11.5% (acute crisis / massive inflection spike)
          - 2023-12-01: 6.1% (endpoint)

        A naive 'baseline + endpoint' selection would pick 6.0% and 6.1%,
        misleading the reasoning layer into concluding HbA1c was completely stable (+0.1%).
        CP-08 MUST detect the non-linear inflection spike (11.5%) and select all 3 points.
        """
        candidates = [
            make_res("ev_base", "2021-01-01T00:00:00Z", 6.0),
            make_res("ev_spike", "2022-06-01T00:00:00Z", 11.5),
            make_res("ev_end", "2023-12-01T00:00:00Z", 6.1),
        ]
        query = ClinicalQuery(
            raw_query="How has my HbA1c changed over time?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates, max_trajectory_evidence=3)

        assert "ev_spike" in pkg.selected_evidence_ids
        assert pkg.selection_rationale["ev_spike"] == "inflection_point"
        assert pkg.feature_summaries["max_value"] == 11.5

    def test_multi_patient_isolation(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_p1", "2023-01-01T00:00:00Z", 6.0, patient_id="p1"),
            make_res("ev_p2", "2023-01-01T00:00:00Z", 8.5, patient_id="p2"),
        ]
        query = ClinicalQuery(
            raw_query="What is my HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="HbA1c",
        )
        setattr(query, "patient_id", "p1")
        pkg = selector.select(query, candidates)

        assert pkg.selected_evidence_ids == ["ev_p1"]
        assert "ev_p2" not in pkg.selected_evidence_ids

    def test_multi_analyte_isolation(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_hba1c", "2023-01-01T00:00:00Z", 6.0, analyte="HbA1c"),
            make_res("ev_glucose", "2023-01-01T00:00:00Z", 110.0, analyte="Glucose"),
        ]
        query = ClinicalQuery(
            raw_query="What is my HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.selected_evidence_ids == ["ev_hba1c"]
        assert pkg.target_analyte == "HbA1c"

    def test_zero_baseline_safety(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2023-01-01T00:00:00Z", 0.0),
            make_res("ev_2", "2023-02-01T00:00:00Z", 5.0),
        ]
        query = ClinicalQuery(
            raw_query="Trend of my marker",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        # Division by zero avoided
        assert pkg.feature_summaries["relative_change"] is None
        assert pkg.feature_summaries["absolute_delta"] == 5.0
        assert pkg.feature_summaries["direction"] == "increased"

    def test_duplicate_dates_safety(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2023-01-01T00:00:00Z", 5.0),
            make_res("ev_2", "2023-01-01T00:00:00Z", 6.0),
        ]
        query = ClinicalQuery(
            raw_query="Trend of my marker",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.feature_summaries["date_span_days"] == 0.0
        assert pkg.feature_summaries["slope_per_day"] == 0.0

    def test_missing_and_non_numeric_values_safety(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2023-01-01T00:00:00Z", "POSITIVE"),
            make_res("ev_2", "2023-02-01T00:00:00Z", None),
        ]
        query = ClinicalQuery(
            raw_query="Marker history",
            intent=QueryIntent.HISTORICAL,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)

        assert pkg.feature_summaries["is_numeric"] is False
        assert len(pkg.selected_evidence_ids) == 2

    def test_empty_candidates_returns_safe_package(self, selector: LongitudinalEvidenceSelector):
        query = ClinicalQuery(
            raw_query="My HbA1c",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, [])

        assert pkg.selected_evidence_ids == []
        assert pkg.selected_observations == []
        assert pkg.feature_summaries == {}

    def test_to_dict_serialization(self, selector: LongitudinalEvidenceSelector):
        candidates = [
            make_res("ev_1", "2023-01-01T00:00:00Z", 5.5),
            make_res("ev_2", "2023-06-01T00:00:00Z", 6.5),
        ]
        query = ClinicalQuery(
            raw_query="Trend",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        data = pkg.to_dict()

        assert isinstance(data, dict)
        assert data["patient_id"] == "p1"
        assert len(data["selected_evidence_ids"]) == 2
        assert "provenance_references" in data
        assert "feature_summaries" in data


class TestAbnormalityHeuristicsAndPrecedence:
    """
    Unit tests verifying the abnormality precedence chain:
      1. Recorded Laboratory Flag (highest precedence)
      2. Recorded Reference Interval in metadata
      3. Deterministic Synthetic-Cohort Heuristic Fallback
      4. Safe handling of missing ranges and ambiguous measurement context.
    """

    def test_recorded_flag_takes_top_precedence(self):
        from packages.research_data.retrieval.longitudinal_selection import is_abnormal_observation

        # Flag "normal" overrides numerical value exceeding synthetic threshold
        obs_normal_flag = make_res("ev_1", "2023-01-01T00:00:00Z", 250.0, analyte="Total Cholesterol", flag="normal")
        assert is_abnormal_observation(obs_normal_flag) is False

        # Flag "high" overrides numerical value within normal synthetic threshold
        obs_high_flag = make_res("ev_2", "2023-01-01T00:00:00Z", 150.0, analyte="Total Cholesterol", flag="high")
        assert is_abnormal_observation(obs_high_flag) is True

    def test_recorded_reference_interval_precedence_over_heuristics(self):
        from packages.research_data.retrieval.longitudinal_selection import is_abnormal_observation

        # Glucose heuristic is >= 100 mg/dL.
        # But if recorded laboratory reference range is 70 - 115 mg/dL (e.g. post-prandial context):
        obs = make_res("ev_gl", "2023-01-01T00:00:00Z", 108.0, analyte="Glucose", flag="")
        obs.metadata = {"reference_low": "70", "reference_high": "115"}

        # Value 108 is within [70, 115], so reference interval precedence marks it NOT abnormal
        assert is_abnormal_observation(obs) is False

        # Value 120 exceeds 115, so marked abnormal via recorded reference interval
        obs_elevated = make_res("ev_gl2", "2023-01-01T00:00:00Z", 120.0, analyte="Glucose", flag="")
        obs_elevated.metadata = {"reference_low": "70", "reference_high": "115"}
        assert is_abnormal_observation(obs_elevated) is True

    def test_synthetic_cohort_heuristic_fallback_when_ranges_missing(self):
        from packages.research_data.retrieval.longitudinal_selection import is_abnormal_observation

        # No flag, no reference interval in metadata -> fallback to synthetic heuristics
        obs_hba1c_high = make_res("ev_h1", "2023-01-01T00:00:00Z", 6.8, analyte="HbA1c", flag="")
        assert is_abnormal_observation(obs_hba1c_high) is True

        obs_hba1c_norm = make_res("ev_h2", "2023-01-01T00:00:00Z", 5.4, analyte="HbA1c", flag="")
        assert is_abnormal_observation(obs_hba1c_norm) is False

    def test_missing_ranges_and_ambiguous_context_safety(self):
        from packages.research_data.retrieval.longitudinal_selection import is_abnormal_observation

        # Unmapped analyte with no heuristic and no flag -> safe False, no error
        obs_unmapped = make_res("ev_u", "2023-01-01T00:00:00Z", 50.0, analyte="Vitamin D", flag="")
        assert is_abnormal_observation(obs_unmapped) is False

        # Non-numeric string value with no explicit flag -> safe False
        obs_non_num = make_res("ev_nn", "2023-01-01T00:00:00Z", "BORDERLINE", analyte="HbA1c", flag="")
        assert is_abnormal_observation(obs_non_num) is False

        # None value -> safe False
        obs_none = make_res("ev_none", "2023-01-01T00:00:00Z", None, analyte="Glucose", flag="")
        assert is_abnormal_observation(obs_none) is False
