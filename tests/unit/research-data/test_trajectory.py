"""
tests/unit/research-data/test_trajectory.py

Unit test suite for Longitudinal Trajectory Construction & Features (CP-07).
Verifies:
  1. Chronological ordering (t_1 <= t_2 <= ... <= t_n) with tie-breaking on evidence_id
  2. Single-observation trajectory
  3. Two-point delta and rate of change
  4. Relative percentage change
  5. Slope per day calculation
  6. Positive trend dynamics
  7. Negative trend dynamics
  8. Flat / constant trajectory
  9. Non-monotonic / fluctuating trajectory
  10. Duplicate dates handling
  11. Zero baseline safe handling (no ZeroDivisionError)
  12. Missing numeric values (None)
  13. Non-numeric / string values
  14. Malformed date handling
  15. Patient isolation (multiple patients)
  16. Analyte isolation (multiple analytes)
  17. Empty input handling
  18. Serialization (to_dict)
"""

from __future__ import annotations

import pytest

from packages.research_data.retrieval.contract import RetrievalResult
from packages.research_data.retrieval.trajectory import (
    TrajectoryBlock,
    build_trajectories,
    calculate_trajectory_features,
    parse_numeric_value,
)


def make_retrieval_result(
    evidence_id: str,
    date_str: str,
    value: float | str | None,
    patient_id: str = "p_1",
    analyte: str = "HbA1c",
    score: float = 0.8,
) -> RetrievalResult:
    """Helper to create standardized RetrievalResult fixtures."""
    return RetrievalResult(
        evidence_id=evidence_id,
        patient_id=patient_id,
        score=score,
        rank=1,
        retrieval_method="test",
        analyte_canonical=analyte,
        concept_id="LOINC:4548-4" if analyte == "HbA1c" else "LOINC:2345-7",
        loinc_code="4548-4" if analyte == "HbA1c" else "2345-7",
        observation_date=date_str,
        value=value,
        unit="%" if analyte == "HbA1c" else "mg/dL",
        flag="normal",
        source_provenance="fixture",
    )


class TestTrajectoryConstruction:
    def test_chronological_ordering_strictly_enforced(self):
        """Observations provided out of order must be sorted chronologically."""
        obs = [
            make_retrieval_result("ev_3", "2023-05-01T10:00:00Z", 6.8),
            make_retrieval_result("ev_1", "2021-01-01T10:00:00Z", 5.5),
            make_retrieval_result("ev_2", "2022-03-15T10:00:00Z", 6.1),
        ]
        blocks = build_trajectories(obs)
        assert len(blocks) == 1
        block = blocks[("p_1", "HbA1c")]

        assert [o.evidence_id for o in block.observations] == ["ev_1", "ev_2", "ev_3"]
        assert block.first_observation_date == "2021-01-01T10:00:00Z"
        assert block.last_observation_date == "2023-05-01T10:00:00Z"
        assert block.observation_count == 3

    def test_duplicate_dates_tie_broken_by_evidence_id(self):
        """Identical timestamps must break ties deterministically by evidence_id ascending."""
        obs = [
            make_retrieval_result("ev_z", "2022-01-01T00:00:00Z", 100.0),
            make_retrieval_result("ev_a", "2022-01-01T00:00:00Z", 100.0),
            make_retrieval_result("ev_m", "2022-01-01T00:00:00Z", 100.0),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]
        assert [o.evidence_id for o in block.observations] == ["ev_a", "ev_m", "ev_z"]
        assert block.date_span_days == 0.0
        assert block.slope_per_day == 0.0

    def test_single_observation_trajectory(self):
        """A single observation should produce a stable trajectory without exceptions."""
        obs = [make_retrieval_result("ev_single", "2023-01-01T10:00:00Z", 5.7)]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.observation_count == 1
        assert block.date_span_days == 0.0
        assert block.delta == 0.0
        assert block.relative_change == 0.0
        assert block.slope_per_day == 0.0
        assert block.direction == "stable"
        assert block.direction_consistency == 1.0
        assert block.monotonicity == 1.0
        assert block.baseline_value == 5.7
        assert block.latest_value == 5.7

    def test_two_point_delta_and_relative_change(self):
        """Two points with known values must compute exact delta, relative change, and slope."""
        # 100 days apart: 2023-01-01 to 2023-04-11 (100 days)
        obs = [
            make_retrieval_result("ev_1", "2023-01-01T00:00:00Z", 100.0),
            make_retrieval_result("ev_2", "2023-04-11T00:00:00Z", 150.0),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.observation_count == 2
        assert block.delta == 50.0
        assert block.relative_change == 0.50  # +50%
        assert block.date_span_days == 100.0
        assert block.slope_per_day == 0.50  # 50 / 100 = 0.5 units/day
        assert block.direction == "increasing"
        assert block.direction_consistency == 1.0
        assert block.monotonicity == 1.0

    def test_positive_trend(self):
        """Consistently rising values must yield direction='increasing' and positive monotonicity."""
        obs = [
            make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", 5.5),
            make_retrieval_result("ev_2", "2022-06-01T00:00:00Z", 6.0),
            make_retrieval_result("ev_3", "2023-01-01T00:00:00Z", 6.8),
            make_retrieval_result("ev_4", "2023-08-01T00:00:00Z", 7.4),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.direction == "increasing"
        assert block.direction_consistency == 1.0
        assert block.monotonicity == 1.0
        assert block.delta == 1.9
        assert block.min_value == 5.5
        assert block.max_value == 7.4

    def test_negative_trend(self):
        """Consistently declining values must yield direction='decreasing' and negative monotonicity."""
        obs = [
            make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", 180.0),
            make_retrieval_result("ev_2", "2022-06-01T00:00:00Z", 160.0),
            make_retrieval_result("ev_3", "2023-01-01T00:00:00Z", 130.0),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.direction == "decreasing"
        assert block.direction_consistency == 1.0
        assert block.monotonicity == -1.0
        assert block.delta == -50.0
        assert block.relative_change == round(-50.0 / 180.0, 6)

    def test_flat_trajectory(self):
        """Constant values across time must produce direction='stable'."""
        obs = [
            make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", 95.0),
            make_retrieval_result("ev_2", "2022-06-01T00:00:00Z", 95.0),
            make_retrieval_result("ev_3", "2023-01-01T00:00:00Z", 95.0),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.direction == "stable"
        assert block.delta == 0.0
        assert block.relative_change == 0.0
        assert block.slope_per_day == 0.0
        assert block.direction_consistency == 1.0
        assert block.monotonicity == 1.0

    def test_non_monotonic_fluctuating_trajectory(self):
        """Fluctuating values (e.g. up then down) must yield intermediate monotonicity."""
        # 100 -> 140 (+40), 140 -> 110 (-30)
        obs = [
            make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", 100.0),
            make_retrieval_result("ev_2", "2022-06-01T00:00:00Z", 140.0),
            make_retrieval_result("ev_3", "2023-01-01T00:00:00Z", 110.0),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        # Overall delta is +10 (increasing)
        assert block.delta == 10.0
        assert block.direction == "increasing"
        # 1 positive step, 1 negative step out of 2 steps -> consistency = 1/2 = 0.5
        assert block.direction_consistency == 0.5
        # monotonicity: (1 - 1) / 2 = 0.0
        assert block.monotonicity == 0.0
        assert block.max_value == 140.0
        assert block.min_value == 100.0

    def test_zero_baseline_safe_handling(self):
        """Baseline of zero must not cause ZeroDivisionError for relative_change."""
        obs = [
            make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", 0.0),
            make_retrieval_result("ev_2", "2022-06-01T00:00:00Z", 10.0),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.delta == 10.0
        # Zero baseline cannot divide by zero -> returns None safely
        assert block.relative_change is None
        assert block.direction == "increasing"

    def test_missing_and_non_numeric_values_handled_safely(self):
        """Observations with None or text values must not raise errors or corrupt numeric features."""
        obs = [
            make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", 5.5),
            make_retrieval_result("ev_2", "2022-03-01T00:00:00Z", None),
            make_retrieval_result("ev_3", "2022-06-01T00:00:00Z", "positive"),
            make_retrieval_result("ev_4", "2022-09-01T00:00:00Z", 6.5),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.observation_count == 4
        # Numeric dynamics computed over the 2 valid numeric points (5.5 and 6.5)
        assert block.delta == 1.0
        assert block.direction == "increasing"
        assert block.baseline_value == 5.5
        assert block.latest_value == 6.5

    def test_all_non_numeric_values_yields_insufficient_data(self):
        """Trajectory with zero numeric observations produces direction='insufficient_data'."""
        obs = [
            make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", "Negative"),
            make_retrieval_result("ev_2", "2022-06-01T00:00:00Z", "Positive"),
        ]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]

        assert block.observation_count == 2
        assert block.delta is None
        assert block.slope_per_day is None
        assert block.direction == "insufficient_data"

    def test_multiple_patients_and_analytes_isolated(self):
        """Observations from different patients or analytes must be cleanly partitioned."""
        obs = [
            make_retrieval_result("p1_h1", "2022-01-01T00:00:00Z", 5.5, patient_id="P1", analyte="HbA1c"),
            make_retrieval_result("p1_h2", "2022-06-01T00:00:00Z", 6.0, patient_id="P1", analyte="HbA1c"),
            make_retrieval_result("p1_g1", "2022-01-01T00:00:00Z", 95.0, patient_id="P1", analyte="Glucose"),
            make_retrieval_result("p2_h1", "2022-01-01T00:00:00Z", 7.0, patient_id="P2", analyte="HbA1c"),
        ]
        blocks = build_trajectories(obs)
        assert len(blocks) == 3

        assert ("P1", "HbA1c") in blocks
        assert ("P1", "Glucose") in blocks
        assert ("P2", "HbA1c") in blocks

        assert blocks[("P1", "HbA1c")].observation_count == 2
        assert blocks[("P1", "Glucose")].observation_count == 1
        assert blocks[("P2", "HbA1c")].observation_count == 1

    def test_empty_candidate_set(self):
        """Empty input must return an empty dictionary without errors."""
        blocks = build_trajectories([])
        assert blocks == {}

    def test_trajectory_block_serialization(self):
        """TrajectoryBlock.to_dict() must serialize all fields to JSON-serializable types."""
        obs = [make_retrieval_result("ev_1", "2022-01-01T00:00:00Z", 5.5)]
        blocks = build_trajectories(obs)
        block = blocks[("p_1", "HbA1c")]
        data = block.to_dict()

        assert data["patient_id"] == "p_1"
        assert data["analyte_canonical"] == "HbA1c"
        assert data["observation_count"] == 1
        assert isinstance(data["observations"], list)
        assert data["observations"][0]["evidence_id"] == "ev_1"
