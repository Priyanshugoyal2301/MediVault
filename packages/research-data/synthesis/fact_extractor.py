"""
packages/research-data/synthesis/fact_extractor.py

Deterministic Fact Extraction Layer (CP-09).
Consumes LongitudinalEvidencePackage from CP-08 and extracts structured,
auditable ObservedFacts and DerivedFacts.

Guarantees:
  1. Complete provenance: Every observed fact is strictly tied to its evidence_id.
  2. Mathematical rigor: Every derived fact records the exact subset of contributing evidence_ids.
  3. Zero speculation: Mathematical and temporal facts only; strictly zero diagnosis or treatment claims.
"""

from __future__ import annotations

import logging
from typing import Sequence

from packages.research_data.retrieval.contract import (
    RetrievalResult,
    parse_date_to_timestamp,
)
from packages.research_data.retrieval.longitudinal_selection import (
    LongitudinalEvidencePackage,
)
from packages.research_data.retrieval.trajectory import parse_numeric_value
from packages.research_data.synthesis.contracts import (
    DerivedFact,
    ObservedFact,
)

logger = logging.getLogger(__name__)


class DeterministicFactExtractor:
    """
    Extracts structured observed facts and derived mathematical calculations
    from a LongitudinalEvidencePackage with strict evidence provenance.
    """

    def extract_facts(
        self, package: LongitudinalEvidencePackage
    ) -> tuple[list[ObservedFact], list[DerivedFact]]:
        """
        Extracts all observed facts and derived mathematical facts from the package.
        Returns: (observed_facts, derived_facts).
        """
        observed_facts = self._extract_observed_facts(package)
        derived_facts = self._extract_derived_facts(package, observed_facts)
        return observed_facts, derived_facts

    def _extract_observed_facts(
        self, package: LongitudinalEvidencePackage
    ) -> list[ObservedFact]:
        observed: list[ObservedFact] = []
        for obs in package.selected_observations:
            role = package.selection_rationale.get(obs.evidence_id, "selected")
            fact = ObservedFact(
                evidence_id=obs.evidence_id,
                observation_date=obs.observation_date,
                analyte_canonical=obs.analyte_canonical or (package.target_analyte or "Unknown"),
                value=obs.value,
                unit=obs.unit or "",
                flag=obs.flag,
                loinc_code=obs.loinc_code,
                concept_id=obs.concept_id,
                source_provenance=obs.source_provenance,
                role=role,
            )
            observed.append(fact)
        return observed

    def _extract_derived_facts(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
    ) -> list[DerivedFact]:
        derived: list[DerivedFact] = []
        if not observed_facts:
            return derived

        # Filter numeric observations sorted chronologically
        numeric_obs = [
            (parse_date_to_timestamp(o.observation_date), parse_numeric_value(o.value), o)
            for o in observed_facts
            if parse_numeric_value(o.value) is not None
        ]

        if not numeric_obs:
            return derived

        t_first, y_first, o_first = numeric_obs[0]
        t_last, y_last, o_last = numeric_obs[-1]
        unit = o_first.unit

        # 1. Trajectory Span Duration
        span_days = max(0.0, round((t_last - t_first) / 86400.0, 2))
        derived.append(
            DerivedFact(
                metric="span_days",
                value=span_days,
                unit="days",
                contributing_evidence_ids=[o_first.evidence_id, o_last.evidence_id] if len(numeric_obs) > 1 else [o_first.evidence_id],
                description=f"Observation span of {span_days} days between {o_first.observation_date[:10]} and {o_last.observation_date[:10]}",
                start_date=o_first.observation_date,
                end_date=o_last.observation_date,
            )
        )

        # 2. Net Absolute Delta
        delta = round(y_last - y_first, 4)
        delta_ids = [o_first.evidence_id, o_last.evidence_id] if len(numeric_obs) > 1 else [o_first.evidence_id]
        derived.append(
            DerivedFact(
                metric="absolute_delta",
                value=delta,
                unit=unit,
                contributing_evidence_ids=delta_ids,
                description=f"Net change of {delta:+g} {unit} from {y_first} to {y_last}",
                start_date=o_first.observation_date,
                end_date=o_last.observation_date,
            )
        )

        # 3. Relative Change
        if abs(y_first) > 1e-6:
            rel_change_pct = round((delta / abs(y_first)) * 100.0, 2)
            derived.append(
                DerivedFact(
                    metric="relative_change_pct",
                    value=rel_change_pct,
                    unit="%",
                    contributing_evidence_ids=delta_ids,
                    description=f"Relative change of {rel_change_pct:+g}% relative to baseline value {y_first} {unit}",
                    start_date=o_first.observation_date,
                    end_date=o_last.observation_date,
                )
            )

        # 4. Trajectory Direction
        tol = 1e-4
        if delta > tol:
            direction = "increased"
        elif delta < -tol:
            direction = "decreased"
        else:
            direction = "stable"

        derived.append(
            DerivedFact(
                metric="direction",
                value=direction,
                unit="",
                contributing_evidence_ids=delta_ids,
                description=f"Overall direction is {direction} over the evaluated interval",
                start_date=o_first.observation_date,
                end_date=o_last.observation_date,
            )
        )

        # 5. Rate / Slope per day
        if span_days > 0.0:
            slope = round(delta / span_days, 6)
            derived.append(
                DerivedFact(
                    metric="slope_per_day",
                    value=slope,
                    unit=f"{unit}/day" if unit else "units/day",
                    contributing_evidence_ids=delta_ids,
                    description=f"Rate of change is {slope:+g} {unit}/day over {span_days} days",
                    start_date=o_first.observation_date,
                    end_date=o_last.observation_date,
                )
            )

        # 6. Minimum & Maximum Extrema
        all_vals = [val for _, val, _ in numeric_obs]
        min_val = min(all_vals)
        max_val = max(all_vals)
        min_obs = next(o for _, val, o in numeric_obs if val == min_val)
        max_obs = next(o for _, val, o in numeric_obs if val == max_val)

        derived.append(
            DerivedFact(
                metric="min_value",
                value=min_val,
                unit=unit,
                contributing_evidence_ids=[min_obs.evidence_id],
                description=f"Minimum observed value of {min_val} {unit} on {min_obs.observation_date[:10]}",
                start_date=min_obs.observation_date,
                end_date=min_obs.observation_date,
            )
        )
        derived.append(
            DerivedFact(
                metric="max_value",
                value=max_val,
                unit=unit,
                contributing_evidence_ids=[max_obs.evidence_id],
                description=f"Maximum observed value of {max_val} {unit} on {max_obs.observation_date[:10]}",
                start_date=max_obs.observation_date,
                end_date=max_obs.observation_date,
            )
        )

        # 7. Inflection Point (if secular chord deviation detected)
        inflection_info = package.feature_summaries.get("inflection_point", {})
        inflection_id = inflection_info.get("inflection_evidence_id")
        if inflection_id:
            inflection_obs = next((o for _, _, o in numeric_obs if o.evidence_id == inflection_id), None)
            if inflection_obs:
                dev = inflection_info.get("max_chord_deviation", 0.0)
                derived.append(
                    DerivedFact(
                        metric="inflection_point",
                        value=dev,
                        unit=unit,
                        contributing_evidence_ids=[o_first.evidence_id, inflection_obs.evidence_id, o_last.evidence_id],
                        description=(
                            f"Significant non-linear inflection of {inflection_obs.value} {unit} observed on "
                            f"{inflection_obs.observation_date[:10]} with secular chord deviation of {dev:.4f}"
                        ),
                        start_date=inflection_obs.observation_date,
                        end_date=inflection_obs.observation_date,
                    )
                )

        return derived
