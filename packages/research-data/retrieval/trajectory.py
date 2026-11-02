"""
packages/research-data/retrieval/trajectory.py

Longitudinal Trajectory Construction & Mathematical Feature Extraction (CP-07).
Constructs chronological patient observation trajectories and extracts deterministic
longitudinal dynamics (delta, relative change, slope, direction, consistency, monotonicity).

Guarantees:
  1. Patient & Analyte Isolation: Observations are partitioned by (patient_id, analyte_canonical).
  2. Chronological Ordering: Guaranteed t_1 <= t_2 <= ... <= t_n with deterministic tie-breaking.
  3. Safe Edge Case Handling: Zero baseline, duplicate timestamps, missing or non-numeric values.
  4. Non-fabrication: Never invents dates, values, or evidence IDs.
  5. Pure domain representation: Free from web/FastAPI framework dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Sequence

from packages.research_data.retrieval.contract import (
    RetrievalResult,
    parse_date_to_timestamp,
)

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryBlock:
    """
    Structured domain representation of a patient's longitudinal analyte trajectory (CP-07).
    Suitable for downstream clinical reasoning and evidence selection in CP-08.
    """

    patient_id: str
    analyte_canonical: str
    observations: list[RetrievalResult] = field(default_factory=list)
    first_observation_date: str | None = None
    last_observation_date: str | None = None
    observation_count: int = 0
    date_span_days: float = 0.0
    delta: float | None = None
    relative_change: float | None = None
    slope_per_day: float | None = None
    direction: str = "insufficient_data"  # "increasing", "decreasing", "stable", "insufficient_data"
    direction_consistency: float = 0.0  # Fraction of step intervals aligned with dominant direction [0.0, 1.0]
    monotonicity: float = 0.0  # Normalized sign concordance [-1.0, 1.0]
    min_value: float | None = None
    max_value: float | None = None
    baseline_value: float | None = None
    latest_value: float | None = None
    unit: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the trajectory block to a JSON-compatible dictionary."""
        data = asdict(self)
        data["observations"] = [obs.to_dict() for obs in self.observations]
        return data


def parse_numeric_value(val: Any) -> float | None:
    """Safely extracts a float from a value, returning None if non-numeric or missing."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            # Strip standard units or comparison symbols if present
            cleaned = val.strip().lstrip("<>=").strip()
            return float(cleaned)
        except ValueError:
            return None
    return None


def calculate_inflection_point(
    sorted_obs: list[RetrievalResult],
    method: str = "secant_chord",
) -> dict[str, Any]:
    r"""
    Identifies the primary intermediate inflection / turning point in a chronologically
    sorted observation series with mathematical reproducibility.

    Mathematical Formulation:
      Given a chronologically ordered sequence of numeric observations:
        P = ((t_1, y_1), (t_2, y_2), ..., (t_n, y_n)) where t_1 <= t_2 <= ... <= t_n.

      If n <= 2:
        No interior intermediate points exist.
        Returns inflection_evidence_id = None, deviation = 0.0.

      If n >= 3:
        For each intermediate observation k in {2, ..., n-1}:
          1. Method 'secant_chord' (Linear Secant Interpolation):
             The expected secular baseline value \hat{y}_k at time t_k along the chord is:
                 \hat{y}_k = y_1 + ((t_k - t_1) / (t_n - t_1)) * (y_n - y_1)  if t_n > t_1
                 \hat{y}_k = y_1                                              if t_n == t_1
             The non-linear excursion (inflection magnitude) is:
                 d_k = |y_k - \hat{y}_k|

          2. Method 'baseline' (Baseline Deviation):
             \hat{y}_k = y_1
             d_k = |y_k - y_1|

        The maximum inflection point is:
            k* = argmax_{k in {2, ..., n-1}} d_k
        Deterministic tie-breaking: earliest timestamp, then ascending evidence_id.

    Returns:
        dict containing inflection_evidence_id, inflection_observation,
        inflection_deviation, expected_secant_value, and method.
    """
    numeric_points: list[tuple[float, float, RetrievalResult]] = []
    for obs in sorted_obs:
        num_val = parse_numeric_value(obs.value)
        if num_val is not None:
            ts = parse_date_to_timestamp(obs.observation_date)
            numeric_points.append((ts, num_val, obs))

    n = len(numeric_points)
    if n <= 2:
        return {
            "inflection_evidence_id": None,
            "inflection_observation": None,
            "inflection_deviation": 0.0,
            "expected_secant_value": None,
            "method": method,
        }

    t1, y1, _ = numeric_points[0]
    tn, yn, _ = numeric_points[-1]
    time_span = tn - t1

    best_obs: RetrievalResult | None = None
    best_id: str | None = None
    best_deviation = -1.0
    best_expected: float | None = None

    for i in range(1, n - 1):
        tk, yk, obs = numeric_points[i]

        if method == "baseline" or time_span <= 0.0:
            y_hat = y1
        else:
            # Linear secant chord interpolation
            fraction = (tk - t1) / time_span
            y_hat = y1 + fraction * (yn - y1)

        deviation = abs(yk - y_hat)

        # Strict deterministic tie-breaking: larger deviation wins,
        # then earlier timestamp (inherent in loop order), then evidence_id
        if deviation > best_deviation or (
            abs(deviation - best_deviation) < 1e-9
            and best_id is not None
            and obs.evidence_id < best_id
        ):
            best_deviation = deviation
            best_id = obs.evidence_id
            best_obs = obs
            best_expected = y_hat

    return {
        "inflection_evidence_id": best_id if best_deviation > 0.0 else None,
        "inflection_observation": best_obs if best_deviation > 0.0 else None,
        "inflection_deviation": round(max(0.0, best_deviation), 6),
        "expected_secant_value": round(best_expected, 6) if best_expected is not None else None,
        "method": method,
    }


def calculate_trajectory_features(
    sorted_obs: list[RetrievalResult],
) -> dict[str, Any]:

    """
    Computes deterministic mathematical features over a chronologically sorted series of observations.
    Handles duplicate dates, zero baselines, non-numeric values, and single-point series safely.
    """
    count = len(sorted_obs)
    if count == 0:
        return {
            "first_observation_date": None,
            "last_observation_date": None,
            "observation_count": 0,
            "date_span_days": 0.0,
            "delta": None,
            "relative_change": None,
            "slope_per_day": None,
            "direction": "insufficient_data",
            "direction_consistency": 0.0,
            "monotonicity": 0.0,
            "min_value": None,
            "max_value": None,
            "baseline_value": None,
            "latest_value": None,
            "unit": None,
            "inflection_evidence_id": None,
            "inflection_deviation": 0.0,
        }

    first_date = sorted_obs[0].observation_date
    last_date = sorted_obs[-1].observation_date
    unit = next((o.unit for o in sorted_obs if o.unit), None)

    # Filter observations with valid numeric values
    numeric_points: list[tuple[float, float, RetrievalResult]] = []
    for obs in sorted_obs:
        num_val = parse_numeric_value(obs.value)
        if num_val is not None:
            ts = parse_date_to_timestamp(obs.observation_date)
            numeric_points.append((ts, num_val, obs))

    # Time span across the entire series
    t_start = parse_date_to_timestamp(first_date)
    t_end = parse_date_to_timestamp(last_date)
    date_span_days = max(0.0, (t_end - t_start) / 86400.0) if t_start and t_end else 0.0

    if len(numeric_points) == 0:
        return {
            "first_observation_date": first_date,
            "last_observation_date": last_date,
            "observation_count": count,
            "date_span_days": date_span_days,
            "delta": None,
            "relative_change": None,
            "slope_per_day": None,
            "direction": "insufficient_data",
            "direction_consistency": 0.0,
            "monotonicity": 0.0,
            "min_value": None,
            "max_value": None,
            "baseline_value": None,
            "latest_value": None,
            "unit": unit,
            "inflection_evidence_id": None,
            "inflection_deviation": 0.0,
        }

    all_vals = [p[1] for p in numeric_points]
    min_val = min(all_vals)
    max_val = max(all_vals)
    baseline_val = numeric_points[0][1]
    latest_val = numeric_points[-1][1]

    if len(numeric_points) == 1:
        return {
            "first_observation_date": first_date,
            "last_observation_date": last_date,
            "observation_count": count,
            "date_span_days": date_span_days,
            "delta": 0.0,
            "relative_change": 0.0,
            "slope_per_day": 0.0,
            "direction": "stable",
            "direction_consistency": 1.0,
            "monotonicity": 1.0,
            "min_value": min_val,
            "max_value": max_val,
            "baseline_value": baseline_val,
            "latest_value": latest_val,
            "unit": unit,
            "inflection_evidence_id": None,
            "inflection_deviation": 0.0,
        }

    # Two or more numeric points: calculate trajectory dynamics
    # Delta
    delta = round(latest_val - baseline_val, 6)

    # Relative change: (latest - baseline) / |baseline|
    if abs(baseline_val) > 1e-9:
        relative_change = round(delta / abs(baseline_val), 6)
    else:
        # Zero baseline: if latest is also zero, relative change is 0.0; otherwise None
        relative_change = 0.0 if abs(latest_val) <= 1e-9 else None

    # Slope per day
    # Calculated based on time span between first and last numeric points
    t_num_start = numeric_points[0][0]
    t_num_end = numeric_points[-1][0]
    num_span_days = max(0.0, (t_num_end - t_num_start) / 86400.0) if t_num_start and t_num_end else 0.0

    if num_span_days > 0.0:
        slope_per_day = round(delta / num_span_days, 6)
    else:
        # Same day / duplicate dates
        slope_per_day = 0.0

    # Direction classification based on overall delta
    # Small tolerance to avoid floating-point jitter
    tol = 1e-4
    if delta > tol:
        direction = "increasing"
    elif delta < -tol:
        direction = "decreasing"
    else:
        direction = "stable"

    # Direction consistency & Monotonicity
    # Evaluated over consecutive steps between chronological numeric points
    n_steps = len(numeric_points) - 1
    pos_steps = 0
    neg_steps = 0
    flat_steps = 0

    for i in range(n_steps):
        step_diff = numeric_points[i + 1][1] - numeric_points[i][1]
        if step_diff > tol:
            pos_steps += 1
        elif step_diff < -tol:
            neg_steps += 1
        else:
            flat_steps += 1

    if direction == "increasing":
        direction_consistency = round(pos_steps / n_steps, 4)
    elif direction == "decreasing":
        direction_consistency = round(neg_steps / n_steps, 4)
    else:
        direction_consistency = round(flat_steps / n_steps, 4)

    # Monotonicity: normalized net concordance in [-1.0, 1.0]
    if flat_steps == n_steps:
        monotonicity = 1.0
    else:
        monotonicity = round((pos_steps - neg_steps) / n_steps, 4)

    inflection_info = calculate_inflection_point(sorted_obs, method="secant_chord")

    return {
        "first_observation_date": first_date,
        "last_observation_date": last_date,
        "observation_count": count,
        "date_span_days": round(date_span_days, 2),
        "delta": delta,
        "relative_change": relative_change,
        "slope_per_day": slope_per_day,
        "direction": direction,
        "direction_consistency": direction_consistency,
        "monotonicity": monotonicity,
        "min_value": min_val,
        "max_value": max_val,
        "baseline_value": baseline_val,
        "latest_value": latest_val,
        "unit": unit,
        "inflection_evidence_id": inflection_info["inflection_evidence_id"],
        "inflection_deviation": inflection_info["inflection_deviation"],
    }


def build_trajectories(
    observations: Sequence[RetrievalResult],
) -> dict[tuple[str, str], TrajectoryBlock]:
    """
    Groups observations by (patient_id, analyte_canonical) and builds structured TrajectoryBlocks.
    Observations within each trajectory block are strictly sorted in chronological order:
        t_1 <= t_2 <= ... <= t_n
    with deterministic tie-breaking on evidence_id for identical timestamps.
    """
    groups: dict[tuple[str, str], list[RetrievalResult]] = {}
    for obs in observations:
        pid = obs.patient_id or "UNKNOWN"
        analyte = obs.analyte_canonical or "UNKNOWN"
        key = (pid, analyte)
        if key not in groups:
            groups[key] = []
        groups[key].append(obs)

    blocks: dict[tuple[str, str], TrajectoryBlock] = {}
    for (pid, analyte), obs_list in groups.items():
        # Chronological sort: timestamp ascending, then evidence_id ascending
        sorted_obs = sorted(
            obs_list,
            key=lambda o: (parse_date_to_timestamp(o.observation_date), o.evidence_id),
        )

        features = calculate_trajectory_features(sorted_obs)

        block = TrajectoryBlock(
            patient_id=pid,
            analyte_canonical=analyte,
            observations=sorted_obs,
            first_observation_date=features["first_observation_date"],
            last_observation_date=features["last_observation_date"],
            observation_count=features["observation_count"],
            date_span_days=features["date_span_days"],
            delta=features["delta"],
            relative_change=features["relative_change"],
            slope_per_day=features["slope_per_day"],
            direction=features["direction"],
            direction_consistency=features["direction_consistency"],
            monotonicity=features["monotonicity"],
            min_value=features["min_value"],
            max_value=features["max_value"],
            baseline_value=features["baseline_value"],
            latest_value=features["latest_value"],
            unit=features["unit"],
            metadata={
                "inflection_evidence_id": features["inflection_evidence_id"],
                "inflection_deviation": features["inflection_deviation"],
            },
        )
        blocks[(pid, analyte)] = block

    return blocks
