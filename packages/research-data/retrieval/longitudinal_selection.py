"""
packages/research-data/retrieval/longitudinal_selection.py

Longitudinal Evidence Selection & Trajectory Reasoning Layer (CP-08).
Consumes candidate RetrievalResults from CP-06 and TrajectoryBlocks from CP-07
to produce a structured, coherent, minimally sufficient LongitudinalEvidencePackage
for downstream grounded synthesis (CP-09).

Guarantees:
  1. Intent-Faithful Selection:
     - previous_value strictly selects the predecessor (never replaces with baseline).
     - current_value strictly selects the latest eligible observation.
     - last_n strictly preserves the requested N observations.
     - historical/bounded date queries strictly respect CP-06 hard temporal boundaries.
     - longitudinal_trend selects minimally sufficient trajectory anchors (baseline,
       endpoint, inflection point) while suppressing dense redundant clusters.
  2. Patient Isolation: Evaluates strictly within each patient's candidate trajectory.
  3. Hard Temporal Gating: Candidates with score == 0.0 are strictly ineligible.
  4. Provenance & Non-Fabrication: Original evidence_ids and metadata are preserved verbatim.
  5. Deterministic Reasoning: Mathematical facts only (delta, rate, direction, inflection);
     zero clinical diagnosis, zero disease progression, zero treatment recommendations.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    TemporalOperator,
)
from packages.research_data.retrieval.contract import (
    RetrievalResult,
    parse_date_to_timestamp,
)
from packages.research_data.retrieval.trajectory import (
    TrajectoryBlock,
    build_trajectories,
    calculate_inflection_point,
    parse_numeric_value,
)

logger = logging.getLogger(__name__)


@dataclass
class LongitudinalEvidencePackage:
    """
    Versioned domain representation of a longitudinal evidence package (CP-08).
    Decoupled from FastAPI response models, designed for consumption by CP-09 grounded synthesis.
    Distinguishes primary target evidence from trajectory-supporting evidence.
    """

    patient_id: str
    query_id: str | None
    raw_query: str
    query_intent: str
    target_analyte: str | None
    selected_evidence_ids: list[str]
    selected_observations: list[RetrievalResult]
    trajectory_blocks: list[TrajectoryBlock]
    feature_summaries: dict[str, Any]
    selection_rationale: dict[str, str]  # evidence_id -> rationale tag
    provenance_references: list[dict[str, Any]]
    selection_metadata: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    primary_evidence_ids: list[str] = field(default_factory=list)
    supporting_evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the evidence package into a JSON-compatible dictionary."""
        return {
            "patient_id": self.patient_id,
            "query_id": self.query_id,
            "raw_query": self.raw_query,
            "query_intent": self.query_intent,
            "target_analyte": self.target_analyte,
            "selected_evidence_ids": list(self.selected_evidence_ids),
            "primary_evidence_ids": list(self.primary_evidence_ids),
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "selected_observations": [obs.to_dict() for obs in self.selected_observations],
            "trajectory_blocks": [block.to_dict() for block in self.trajectory_blocks],
            "feature_summaries": dict(self.feature_summaries),
            "selection_rationale": dict(self.selection_rationale),
            "provenance_references": list(self.provenance_references),
            "selection_metadata": dict(self.selection_metadata),
            "version": self.version,
        }


# -----------------------------------------------------------------------------
# Synthetic-Cohort Abnormality Research Heuristics
# -----------------------------------------------------------------------------
# NOTE: The thresholds below are deterministic research heuristics established
# specifically for the controlled Synthea development cohort, where observation
# records lack explicit laboratory flags and reference intervals.
# In clinical practice, parameters like Glucose (e.g. >= 100 mg/dL) require
# fasting vs. post-prandial context. These thresholds are research heuristics
# for synthetic benchmark evaluation and MUST NOT be treated as authoritative
# or universally valid clinical diagnostic decision boundaries.
SYNTHETIC_COHORT_ABNORMALITY_HEURISTICS: dict[str, dict[str, float]] = {
    "LDL Cholesterol": {"high": 130.0},
    "Total Cholesterol": {"high": 200.0},
    "Triglycerides": {"high": 150.0},
    "HDL Cholesterol": {"low": 40.0},
    "HbA1c": {"high": 6.5},
    "Glucose": {"high": 100.0},  # Research heuristic: unclassified fasting status
    "Haemoglobin": {"low": 12.0, "high": 17.5},
    "WBC": {"low": 4000.0, "high": 11000.0},
    "Platelets": {"low": 150000.0, "high": 450000.0},
    "Creatinine": {"high": 1.2},
    "TSH": {"low": 0.4, "high": 4.0},
}


def is_abnormal_observation(obs: RetrievalResult) -> bool:
    """
    Checks whether an observation indicates an abnormal or out-of-range clinical value.
    Precedence:
      1. Recorded Laboratory Flag: If an explicit laboratory flag is recorded in the record,
         it takes precedence over all numerical heuristics.
      2. Recorded Reference Interval: If explicit reference intervals (reference_low /
         reference_high) are present in metadata, the value is evaluated against them.
      3. Synthetic-Cohort Research Heuristics: Fallback to documented synthetic-cohort
         heuristics only when neither flags nor reference intervals are available.
    """
    # 1. Prefer recorded laboratory flag if present
    flag = str(obs.flag or "").strip().lower()
    if flag in ("abnormal", "high", "low", "critical", "h", "l", "elevated", "panic"):
        return True
    if flag in ("normal", "n", "within normal limits", "wnl"):
        return False

    val = parse_numeric_value(obs.value)
    if val is None:
        return False

    # 2. Prefer recorded reference interval if available in metadata
    meta = obs.metadata or {}
    ref_low = meta.get("reference_low")
    ref_high = meta.get("reference_high")
    if ref_low is not None or ref_high is not None:
        low_val = parse_numeric_value(ref_low)
        high_val = parse_numeric_value(ref_high)
        if low_val is not None and val < low_val:
            return True
        if high_val is not None and val > high_val:
            return True
        if low_val is not None or high_val is not None:
            # Within explicit recorded reference interval
            return False

    # 3. Deterministic Synthetic-Cohort Research Heuristic Fallback
    analyte = obs.analyte_canonical or ""
    heuristics = SYNTHETIC_COHORT_ABNORMALITY_HEURISTICS.get(analyte)
    if heuristics:
        low_limit = heuristics.get("low")
        high_limit = heuristics.get("high")
        if low_limit is not None and val < low_limit:
            return True
        if high_limit is not None and val >= high_limit:
            return True
        return False

    return False


class LongitudinalEvidenceSelector:
    """
    Longitudinal Evidence Selection & Trajectory Reasoning Engine (CP-08).
    Selects a minimally sufficient, explanatory, and intent-faithful evidence subset
    from retrieved candidates and constructs deterministic longitudinal fact summaries.
    """

    def __init__(
        self,
        cluster_window_days: float = 14.0,
        cluster_value_delta_threshold: float = 0.05,
    ) -> None:
        self.cluster_window_days = cluster_window_days
        self.cluster_value_delta_threshold = cluster_value_delta_threshold

    def select(
        self,
        query: ClinicalQuery,
        candidates: Sequence[RetrievalResult],
        query_id: str | None = None,
        max_trajectory_evidence: int = 10,
    ) -> LongitudinalEvidencePackage:
        """
        Executes query-intent-aware evidence selection over retrieved candidates.
        Guarantees patient isolation, hard temporal exclusions, and deterministic reasoning.
        """
        raw_query = query.raw_query or ""
        pid = getattr(query, "patient_id", None)
        if not pid and candidates:
            pid = candidates[0].patient_id
        patient_id = pid or "UNKNOWN"

        # 1. Filter candidates for patient isolation and hard temporal gating
        # Candidates with score == 0.0 (filtered out by CP-06 hard temporal bounds) are strictly excluded.
        eligible_candidates = [
            c for c in candidates
            if (not pid or c.patient_id == pid) and c.score > 0.0
        ]

        if not eligible_candidates:
            return LongitudinalEvidencePackage(
                patient_id=patient_id,
                query_id=query_id,
                raw_query=raw_query,
                query_intent=str(query.intent.value if hasattr(query.intent, "value") else query.intent),
                target_analyte=query.analyte_canonical,
                selected_evidence_ids=[],
                selected_observations=[],
                trajectory_blocks=[],
                feature_summaries={},
                selection_rationale={},
                provenance_references=[],
                selection_metadata={"reason": "no_eligible_candidates"},
            )

        # 2. Build full TrajectoryBlocks for all analytes
        trajectory_map = build_trajectories(eligible_candidates)
        all_blocks = list(trajectory_map.values())

        # 3. Determine target analyte
        target_analyte = query.analyte_canonical
        if not target_analyte:
            # Fallback to the analyte of the top-ranked candidate
            target_analyte = eligible_candidates[0].analyte_canonical

        # Target trajectory block
        target_block = trajectory_map.get((patient_id, target_analyte or ""))
        if not target_block and all_blocks:
            target_block = all_blocks[0]
            target_analyte = target_block.analyte_canonical

        obs_series: list[RetrievalResult] = target_block.observations if target_block else []

        # 4. Intent-Aware Selection
        intent_str = str(query.intent.value if hasattr(query.intent, "value") else query.intent).upper()
        raw_lower = raw_query.lower()

        primary_obs: list[RetrievalResult] = []
        supporting_obs: list[RetrievalResult] = []
        selection_rationale: dict[str, str] = {}

        # ---------------------------------------------------------
        # Case A: LAST_N OBSERVATIONS QUERY
        # ---------------------------------------------------------
        if (
            "LAST_N" in intent_str
            or query.temporal_operator == TemporalOperator.LAST_N
            or (getattr(query, "limit", None) is not None and getattr(query, "limit", None) > 1)
        ):
            n = getattr(query, "limit", None) or 3
            primary_obs, supporting_obs, selection_rationale = self._select_last_n(obs_series, n=n)

        # ---------------------------------------------------------
        # Case B: DATE_COMPARISON QUERY
        # ---------------------------------------------------------
        elif (
            "DATE_COMPARISON" in intent_str
            or (
                ("COMPARISON" in intent_str or "compare" in raw_lower)
                and (
                    getattr(query, "comparison_target", None) == ComparisonTarget.PERIOD
                    or (query.start_date and query.end_date)
                    or len(re.findall(r"\b(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})\b", raw_lower)) >= 2
                )
            )
        ):
            primary_obs, supporting_obs, selection_rationale = self._select_date_comparison(obs_series, query)

        # ---------------------------------------------------------
        # Case C: PREVIOUS_VALUE / PREDECESSOR QUERY
        # ---------------------------------------------------------
        elif (
            (
                "PREVIOUS" in intent_str
                or (getattr(query, "comparison_target", None) == ComparisonTarget.PREVIOUS and "TREND" not in intent_str)
                or any(k in raw_lower for k in ("previous reading", "prior to the latest", "before the latest", "last reading before"))
            )
            and "trend" not in raw_lower
            and "over time" not in raw_lower
        ):
            primary_obs, supporting_obs, selection_rationale = self._select_previous_value(obs_series)

        # ---------------------------------------------------------
        # Case D: CURRENT_VALUE / LATEST QUERY
        # ---------------------------------------------------------
        elif (
            (
                "CURRENT" in intent_str
                or query.temporal_operator == TemporalOperator.LATEST
                or any(k in raw_lower for k in ("most recent", "latest", "current", "last reading"))
            )
            and "trend" not in raw_lower
            and "over time" not in raw_lower
            and "last 3" not in raw_lower
            and "last 5" not in raw_lower
            and "last n" not in raw_lower
        ):
            primary_obs, supporting_obs, selection_rationale = self._select_current_value(obs_series)

        # ---------------------------------------------------------
        # Case E: ABNORMALITY / FIRST_ABNORMAL QUERY
        # ---------------------------------------------------------
        elif (
            "ABNORMAL" in intent_str
            or query.abnormal_only
            or any(k in raw_lower for k in ("abnormal", "first abnormal", "out of range", "high", "low", "elevated", "flagged"))
        ):
            is_first_abnormal = (
                "first" in raw_lower
                or "first_abnormal" in str(getattr(query, "metadata", {})).lower()
                or "when did" in raw_lower
                or "when was" in raw_lower
            )
            primary_obs, supporting_obs, selection_rationale = self._select_abnormal(obs_series, first_only=is_first_abnormal)

        # ---------------------------------------------------------
        # Case F: HISTORICAL INTERVAL / DATE WINDOW QUERY
        # ---------------------------------------------------------
        elif (
            "HISTORICAL" in intent_str
            or query.temporal_operator in (
                TemporalOperator.BETWEEN,
                TemporalOperator.BEFORE,
                TemporalOperator.AFTER,
                TemporalOperator.SINCE,
                TemporalOperator.EXACT_DATE,
            )
        ):
            primary_obs, supporting_obs, selection_rationale = self._select_historical_interval(obs_series)

        # ---------------------------------------------------------
        # Case G: LONGITUDINAL_TREND / TRAJECTORY QUERY (Default)
        # ---------------------------------------------------------
        else:
            primary_obs, supporting_obs, selection_rationale = self._select_longitudinal_trend(
                obs_series, max_evidence=max_trajectory_evidence
            )

        # Fallback if no observation was selected
        if not primary_obs and not supporting_obs and obs_series:
            primary_obs = [obs_series[-1]]
            selection_rationale[obs_series[-1].evidence_id] = "fallback_latest"

        # Sort combined selected observations chronologically for presentation
        all_obs_dict = {o.evidence_id: o for o in (primary_obs + supporting_obs)}
        selected_obs = sorted(
            all_obs_dict.values(),
            key=lambda o: (parse_date_to_timestamp(o.observation_date), o.evidence_id),
        )
        selected_evidence_ids = [o.evidence_id for o in selected_obs]
        primary_evidence_ids = [o.evidence_id for o in primary_obs]
        supporting_evidence_ids = [o.evidence_id for o in supporting_obs]

        # 5. Extract Deterministic Feature Summaries from Selected Evidence
        feature_summaries = self._compute_feature_summaries(selected_obs, target_block)

        # 6. Extract Provenance References
        provenance_references = [
            {
                "evidence_id": obs.evidence_id,
                "observation_date": obs.observation_date,
                "value": obs.value,
                "unit": obs.unit,
                "flag": obs.flag,
                "analyte_canonical": obs.analyte_canonical,
                "loinc_code": obs.loinc_code,
                "concept_id": obs.concept_id,
                "source_provenance": obs.source_provenance,
                "role": selection_rationale.get(obs.evidence_id, "selected"),
                "is_primary": obs.evidence_id in primary_evidence_ids,
            }
            for obs in selected_obs
        ]

        return LongitudinalEvidencePackage(
            patient_id=patient_id,
            query_id=query_id,
            raw_query=raw_query,
            query_intent=intent_str,
            target_analyte=target_analyte,
            selected_evidence_ids=selected_evidence_ids,
            primary_evidence_ids=primary_evidence_ids,
            supporting_evidence_ids=supporting_evidence_ids,
            selected_observations=selected_obs,
            trajectory_blocks=all_blocks,
            feature_summaries=feature_summaries,
            selection_rationale=selection_rationale,
            provenance_references=provenance_references,
            selection_metadata={
                "candidate_pool_size": len(candidates),
                "eligible_candidate_count": len(eligible_candidates),
                "target_series_total_count": len(obs_series),
                "selected_count": len(selected_obs),
                "primary_count": len(primary_evidence_ids),
                "supporting_count": len(supporting_evidence_ids),
                "requested_n": getattr(query, "limit", None),
                "retrieval_sufficient_for_n": (
                    len(obs_series) >= (getattr(query, "limit", None) or 1)
                    if getattr(query, "limit", None)
                    else True
                ),
            },
        )

    # -------------------------------------------------------------------------
    # Intent-Specific Selection Strategies
    # -------------------------------------------------------------------------

    def _select_previous_value(
        self, obs_series: list[RetrievalResult]
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """
        Selects the exact predecessor observation immediately preceding the latest.
        Returns: (primary_observations, supporting_observations, rationale_dict).
        CRITICAL: Never substitutes baseline anchor in place of the true predecessor.
        """
        n = len(obs_series)
        if n == 0:
            return [], [], {}
        if n == 1:
            obs = obs_series[0]
            return [obs], [], {obs.evidence_id: "only_observation_available"}

        predecessor = obs_series[-2]
        latest = obs_series[-1]

        return (
            [predecessor],
            [latest],
            {
                predecessor.evidence_id: "predecessor",
                latest.evidence_id: "reference_latest",
            },
        )

    def _select_current_value(
        self, obs_series: list[RetrievalResult]
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """Selects the single most recent eligible observation as primary."""
        if not obs_series:
            return [], [], {}
        latest = obs_series[-1]
        return [latest], [], {latest.evidence_id: "latest"}

    def _select_last_n(
        self, obs_series: list[RetrievalResult], n: int
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """Selects exactly the last N chronological observations as primary."""
        if not obs_series:
            return [], [], {}
        n_req = max(1, n)
        subset = obs_series[-n_req:]
        rationale: dict[str, str] = {}
        for idx, obs in enumerate(subset, start=1):
            rationale[obs.evidence_id] = f"last_n_{idx}_of_{len(subset)}"
        return subset, [], rationale

    def _select_abnormal(
        self, obs_series: list[RetrievalResult], first_only: bool
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """Selects abnormal observations (earliest abnormal if first_only=True)."""
        abnormals = [o for o in obs_series if is_abnormal_observation(o)]
        if not abnormals:
            if obs_series:
                latest = obs_series[-1]
                return [], [latest], {latest.evidence_id: "no_abnormality_detected"}
            return [], [], {}

        if first_only:
            earliest_abnormal = abnormals[0]
            return [earliest_abnormal], [], {earliest_abnormal.evidence_id: "first_abnormal"}

        rationale = {o.evidence_id: "abnormal" for o in abnormals}
        return abnormals, [], rationale

    def _select_date_comparison(
        self, obs_series: list[RetrievalResult], query: ClinicalQuery
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """Selects observations corresponding to comparison anchor dates."""
        n = len(obs_series)
        if n <= 2:
            rationale = {o.evidence_id: "comparison_anchor" for o in obs_series}
            return obs_series, [], rationale

        if query.start_date and query.end_date:
            ts_start = parse_date_to_timestamp(query.start_date.isoformat())
            ts_end = parse_date_to_timestamp(query.end_date.isoformat())

            closest_start = min(obs_series, key=lambda o: abs(parse_date_to_timestamp(o.observation_date) - ts_start))
            closest_end = min(obs_series, key=lambda o: abs(parse_date_to_timestamp(o.observation_date) - ts_end))

            selected = [closest_start]
            rationale = {closest_start.evidence_id: "comparison_date_a"}
            if closest_end.evidence_id != closest_start.evidence_id:
                selected.append(closest_end)
                rationale[closest_end.evidence_id] = "comparison_date_b"
            return selected, [], rationale

        baseline = obs_series[0]
        endpoint = obs_series[-1]
        return [baseline, endpoint], [], {
            baseline.evidence_id: "comparison_baseline",
            endpoint.evidence_id: "comparison_endpoint",
        }

    def _select_historical_interval(
        self, obs_series: list[RetrievalResult]
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """Selects observations within the historical window."""
        rationale: dict[str, str] = {}
        for idx, o in enumerate(obs_series):
            if idx == 0:
                rationale[o.evidence_id] = "interval_start"
            elif idx == len(obs_series) - 1:
                rationale[o.evidence_id] = "interval_end"
            else:
                rationale[o.evidence_id] = "interval_intermediate"
        return obs_series, [], rationale

    def _select_longitudinal_trend(
        self, obs_series: list[RetrievalResult], max_evidence: int
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """
        Selects a minimally sufficient, explanatory longitudinal trajectory.
        Preserves baseline ($O_1$), endpoint ($O_n$), and significant inflection points
        as primary evidence, while intermediate milestones serve as supporting evidence.
        """
        n = len(obs_series)
        if n == 0:
            return [], [], {}
        if n == 1:
            return [obs_series[0]], [], {obs_series[0].evidence_id: "single_observation"}
        if n == 2:
            return [obs_series[0], obs_series[1]], [], {
                obs_series[0].evidence_id: "baseline",
                obs_series[1].evidence_id: "endpoint",
            }

        inflection_info = calculate_inflection_point(obs_series, method="secant_chord")
        inflection_id = inflection_info["inflection_evidence_id"]

        # Primary trajectory anchors
        baseline = obs_series[0]
        endpoint = obs_series[-1]

        primary_dict: dict[str, tuple[RetrievalResult, str]] = {
            baseline.evidence_id: (baseline, "baseline"),
            endpoint.evidence_id: (endpoint, "endpoint"),
        }

        # Detect maximum inflection point along the secular chord
        if inflection_id:
            inflection_obs = next((o for o in obs_series if o.evidence_id == inflection_id), None)
            if inflection_obs and inflection_obs.evidence_id not in primary_dict:
                primary_dict[inflection_obs.evidence_id] = (inflection_obs, "inflection_point")

        # Select distinct intermediate milestones as supporting evidence
        supporting_dict: dict[str, tuple[RetrievalResult, str]] = {}
        intermediate_obs = obs_series[1:-1]
        all_selected_count = len(primary_dict)

        if intermediate_obs and all_selected_count < max_evidence:
            selected_timestamps = [
                parse_date_to_timestamp(obs.observation_date) for obs, _ in primary_dict.values()
            ]

            candidates_scored: list[tuple[float, RetrievalResult]] = []
            for int_obs in intermediate_obs:
                if int_obs.evidence_id in primary_dict:
                    continue
                t_cand = parse_date_to_timestamp(int_obs.observation_date)
                min_dist_days = min(abs(t_cand - t_sel) / 86400.0 for t_sel in selected_timestamps)

                if min_dist_days < self.cluster_window_days:
                    continue

                candidates_scored.append((min_dist_days, int_obs))

            candidates_scored.sort(key=lambda x: x[0], reverse=True)
            remaining_slots = max_evidence - all_selected_count

            for _, int_obs in candidates_scored[:remaining_slots]:
                supporting_dict[int_obs.evidence_id] = (int_obs, "intermediate_milestone")

        primary_obs = sorted(
            [obs for obs, _ in primary_dict.values()],
            key=lambda o: (parse_date_to_timestamp(o.observation_date), o.evidence_id),
        )
        supporting_obs = sorted(
            [obs for obs, _ in supporting_dict.values()],
            key=lambda o: (parse_date_to_timestamp(o.observation_date), o.evidence_id),
        )
        rationale = {
            obs.evidence_id: role
            for obs, role in list(primary_dict.values()) + list(supporting_dict.values())
        }
        return primary_obs, supporting_obs, rationale

    # -------------------------------------------------------------------------
    # Deterministic Feature Reasoning (No Clinical Inference)
    # -------------------------------------------------------------------------

    def _compute_feature_summaries(
        self, selected_obs: list[RetrievalResult], target_block: TrajectoryBlock | None
    ) -> dict[str, Any]:
        """
        Calculates deterministic mathematical dynamics from the selected evidence set.
        States purely objective facts (delta, rate, direction, intervals).
        Does NOT state medical diagnosis, clinical prognosis, or treatment recommendations.
        """
        if not selected_obs:
            return {}

        numeric_vals = [
            (parse_date_to_timestamp(o.observation_date), parse_numeric_value(o.value), o)
            for o in selected_obs
            if parse_numeric_value(o.value) is not None
        ]

        if not numeric_vals:
            return {
                "observation_count": len(selected_obs),
                "is_numeric": False,
                "first_date": selected_obs[0].observation_date,
                "last_date": selected_obs[-1].observation_date,
            }

        t_first, y_first, _ = numeric_vals[0]
        t_last, y_last, _ = numeric_vals[-1]

        delta = round(y_last - y_first, 4)
        span_days = max(0.0, round((t_last - t_first) / 86400.0, 2))

        # Relative change
        if abs(y_first) > 1e-6:
            relative_change = round(delta / abs(y_first), 4)
        else:
            relative_change = 0.0 if abs(delta) < 1e-6 else None

        # Rate per day
        slope_per_day = round(delta / span_days, 6) if span_days > 0.0 else 0.0

        # Objective direction
        tol = 1e-4
        if delta > tol:
            direction = "increased"
        elif delta < -tol:
            direction = "decreased"
        else:
            direction = "stable"

        # Inflection point in selected set
        inflection_info = calculate_inflection_point(selected_obs, method="secant_chord")

        all_nums = [val for _, val, _ in numeric_vals]

        return {
            "observation_count": len(selected_obs),
            "date_span_days": span_days,
            "baseline_value": y_first,
            "latest_value": y_last,
            "min_value": min(all_nums),
            "max_value": max(all_nums),
            "absolute_delta": delta,
            "relative_change": relative_change,
            "slope_per_day": slope_per_day,
            "direction": direction,
            "unit": selected_obs[0].unit,
            "inflection_point": inflection_info,
            "total_patient_history_count": target_block.observation_count if target_block else len(selected_obs),
        }
