"""
packages/research-data/synthesis/synthesizer.py

Grounded Clinical Evidence Synthesis Engine (CP-09).
Produces natural, clinical evidence-backed syntheses with strict sentence/claim-level
grounding and explicit provenance references.

Pipeline:
  User Query
     ↓
  ClinicalQuery
     ↓
  LongitudinalEvidencePackage
     ↓
  Deterministic Fact Extraction (Observed & Derived)
     ↓
  Grounded Synthesis & Claim-Level Grounding
     ↓
  Grounding Audit & Provenance Verification

Guarantees:
  1. Claim-level grounding: Every numerical or temporal statement is linked to specific evidence_id(s).
  2. Distinct fact layers: Observed facts, derived calculations, and clinical interpretations are separated.
  3. Non-prescriptive: Strictly zero diagnosis, zero disease progression claims, zero treatment recommendations.
  4. Safe fallback: Graceful handling of empty or insufficient evidence packages without fabrication.
"""

from __future__ import annotations

import logging
from typing import Sequence

from packages.research_data.retrieval.longitudinal_selection import (
    LongitudinalEvidencePackage,
)
from packages.research_data.synthesis.contracts import (
    ClinicalInterpretation,
    DerivedFact,
    FactType,
    GroundedClaim,
    GroundedEvidenceSynthesis,
    InterpretationPolicy,
    ObservedFact,
)
from packages.research_data.synthesis.fact_extractor import DeterministicFactExtractor
from packages.research_data.synthesis.grounding_verifier import GroundingVerifier

logger = logging.getLogger(__name__)


class GroundedEvidenceSynthesizer:
    """
    Synthesizes natural, evidence-backed clinical summaries with claim-level provenance.
    Strictly adheres to deterministic facts and non-prescriptive medical tone.
    """

    def __init__(
        self,
        fact_extractor: DeterministicFactExtractor | None = None,
        verifier: GroundingVerifier | None = None,
        interpretation_policy: InterpretationPolicy = InterpretationPolicy.DISABLED,
    ) -> None:
        self.fact_extractor = fact_extractor or DeterministicFactExtractor()
        self.verifier = verifier or GroundingVerifier()
        self.interpretation_policy = interpretation_policy

    def synthesize(
        self,
        package: LongitudinalEvidencePackage,
        interpretation_policy: InterpretationPolicy | None = None,
    ) -> GroundedEvidenceSynthesis:
        """
        Executes grounded synthesis over the provided LongitudinalEvidencePackage.
        Returns a complete, audited GroundedEvidenceSynthesis contract.
        """
        policy = interpretation_policy or self.interpretation_policy

        # 1. Deterministic Fact Extraction
        observed_facts, derived_facts = self.fact_extractor.extract_facts(package)

        # 2. Fallback for Empty Evidence Package
        if not package.selected_observations or not observed_facts:
            return self._build_empty_fallback(package, policy)

        # 3. Intent-Specific Grounded Claim Construction
        claims = self._build_intent_claims(package, observed_facts, derived_facts)

        # 4. Handle Clinical Interpretation Layer
        interpretations: list[ClinicalInterpretation] = []
        if policy == InterpretationPolicy.CONSTRAINED_REFERENCE_ONLY:
            interpretations, interp_claims = self._build_constrained_interpretations(
                package, observed_facts
            )
            claims.extend(interp_claims)

        # 5. Format Full Summary Text with Inline Citations
        summary_text = " ".join(c.sentence for c in claims)

        # 6. Formal Grounding Audit & Provenance Verification
        audit_report = self.verifier.audit_synthesis(
            package=package,
            claims=claims,
            observed_facts=observed_facts,
            derived_facts=derived_facts,
            interpretation_policy=policy.value,
        )

        return GroundedEvidenceSynthesis(
            query_id=package.query_id,
            patient_id=package.patient_id,
            raw_query=package.raw_query,
            query_intent=package.query_intent,
            target_analyte=package.target_analyte,
            summary_text=summary_text,
            claims=claims,
            observed_facts=observed_facts,
            derived_facts=derived_facts,
            interpretations=interpretations,
            audit_report=audit_report,
            evidence_package_version=package.version,
            version="1.0",
        )

    # -------------------------------------------------------------------------
    # Intent-Specific Synthesis Generators
    # -------------------------------------------------------------------------

    def _build_intent_claims(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
    ) -> list[GroundedClaim]:
        intent = package.query_intent.upper()
        raw_lower = package.raw_query.lower()
        analyte = package.target_analyte or "Clinical marker"
        has_predecessor = any("predecessor" in r for r in package.selection_rationale.values())

        # Map by selection role or query intent
        if "PREVIOUS" in intent or has_predecessor or "previous" in raw_lower or "prior to the latest" in raw_lower:
            return self._synthesize_previous_value(package, observed_facts, derived_facts, analyte)
        elif "CURRENT" in intent or (any("latest" in r for r in package.selection_rationale.values()) and len(observed_facts) == 1):
            return self._synthesize_current_value(package, observed_facts, derived_facts, analyte)
        elif "LAST_N" in intent or any("last_n" in r for r in package.selection_rationale.values()):
            return self._synthesize_last_n(package, observed_facts, derived_facts, analyte)
        elif "ABNORMAL" in intent or any("abnormal" in r for r in package.selection_rationale.values()):
            return self._synthesize_abnormal(package, observed_facts, derived_facts, analyte)
        elif "COMPARISON" in intent or any("comparison" in r for r in package.selection_rationale.values()):
            return self._synthesize_date_comparison(package, observed_facts, derived_facts, analyte)
        elif "HISTORICAL" in intent or any("interval" in r for r in package.selection_rationale.values()):
            return self._synthesize_historical_interval(package, observed_facts, derived_facts, analyte)
        else:
            # Default: LONGITUDINAL_TREND / trajectory
            return self._synthesize_longitudinal_trend(package, observed_facts, derived_facts, analyte)

    def _synthesize_previous_value(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
        analyte: str,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []

        # Find primary predecessor
        predecessor = next(
            (o for o in observed_facts if o.role == "predecessor" or o.evidence_id in package.primary_evidence_ids),
            observed_facts[0],
        )

        claims.append(
            GroundedClaim(
                claim_id="claim_prev_val",
                sentence=(
                    f"Your previous {analyte} level prior to the latest test was {predecessor.value} {predecessor.unit} "
                    f"recorded on {predecessor.observation_date[:10]} [{predecessor.evidence_id}]."
                ),
                fact_type=FactType.OBSERVED,
                evidence_ids=[predecessor.evidence_id],
                numeric_values=[float(predecessor.value)] if isinstance(predecessor.value, (int, float)) else [],
                date_mentions=[predecessor.observation_date[:10]],
            )
        )

        # Reference latest observation if included as supporting context
        latest = next(
            (o for o in observed_facts if o.role == "reference_latest" or o.evidence_id in package.supporting_evidence_ids),
            None,
        )
        if latest and latest.evidence_id != predecessor.evidence_id:
            claims.append(
                GroundedClaim(
                    claim_id="claim_ref_latest",
                    sentence=(
                        f"For comparison, your most recent {analyte} reading was {latest.value} {latest.unit} "
                        f"on {latest.observation_date[:10]} [{latest.evidence_id}]."
                    ),
                    fact_type=FactType.OBSERVED,
                    evidence_ids=[latest.evidence_id],
                    numeric_values=[float(latest.value)] if isinstance(latest.value, (int, float)) else [],
                    date_mentions=[latest.observation_date[:10]],
                )
            )

            # Delta between predecessor and latest
            delta_fact = next((df for df in derived_facts if df.metric == "absolute_delta"), None)
            if delta_fact and isinstance(delta_fact.value, (int, float)):
                direction_fact = next((df for df in derived_facts if df.metric == "direction"), None)
                dir_str = str(direction_fact.value) if direction_fact else "changed"
                claims.append(
                    GroundedClaim(
                        claim_id="claim_prev_delta",
                        sentence=(
                            f"Between these readings, {analyte} {dir_str} by {abs(float(delta_fact.value)):g} {delta_fact.unit} "
                            f"[{predecessor.evidence_id}, {latest.evidence_id}]."
                        ),
                        fact_type=FactType.DERIVED,
                        evidence_ids=[predecessor.evidence_id, latest.evidence_id],
                        numeric_values=[abs(float(delta_fact.value))],
                        date_mentions=[],
                    )
                )

        return claims

    def _synthesize_current_value(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
        analyte: str,
    ) -> list[GroundedClaim]:
        latest = observed_facts[-1]
        claims: list[GroundedClaim] = [
            GroundedClaim(
                claim_id="claim_current_val",
                sentence=(
                    f"Your most recent {analyte} level is {latest.value} {latest.unit} "
                    f"recorded on {latest.observation_date[:10]} [{latest.evidence_id}]."
                ),
                fact_type=FactType.OBSERVED,
                evidence_ids=[latest.evidence_id],
                numeric_values=[float(latest.value)] if isinstance(latest.value, (int, float)) else [],
                date_mentions=[latest.observation_date[:10]],
            )
        ]

        if latest.flag and str(latest.flag).lower() not in ("normal", ""):
            claims.append(
                GroundedClaim(
                    claim_id="claim_current_flag",
                    sentence=f"This measurement was flagged as {latest.flag} in the laboratory report [{latest.evidence_id}].",
                    fact_type=FactType.OBSERVED,
                    evidence_ids=[latest.evidence_id],
                    numeric_values=[],
                    date_mentions=[],
                )
            )

        return claims

    def _synthesize_last_n(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
        analyte: str,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []
        n_count = len(observed_facts)

        readings_text = ", ".join(
            f"{o.value} {o.unit} on {o.observation_date[:10]} [{o.evidence_id}]"
            for o in observed_facts
        )
        claims.append(
            GroundedClaim(
                claim_id="claim_last_n_list",
                sentence=f"Your last {n_count} {analyte} observations are: {readings_text}.",
                fact_type=FactType.OBSERVED,
                evidence_ids=[o.evidence_id for o in observed_facts],
                numeric_values=[float(o.value) for o in observed_facts if isinstance(o.value, (int, float))],
                date_mentions=[o.observation_date[:10] for o in observed_facts],
            )
        )

        if n_count > 1:
            delta_fact = next((df for df in derived_facts if df.metric == "absolute_delta"), None)
            dir_fact = next((df for df in derived_facts if df.metric == "direction"), None)
            if delta_fact and dir_fact:
                all_ids = [o.evidence_id for o in observed_facts]
                claims.append(
                    GroundedClaim(
                        claim_id="claim_last_n_summary",
                        sentence=(
                            f"Over this {n_count}-test sequence, {analyte} {dir_fact.value} "
                            f"by a net {abs(float(delta_fact.value)):g} {delta_fact.unit} "
                            f"[{observed_facts[0].evidence_id}, {observed_facts[-1].evidence_id}]."
                        ),
                        fact_type=FactType.DERIVED,
                        evidence_ids=[observed_facts[0].evidence_id, observed_facts[-1].evidence_id],
                        numeric_values=[abs(float(delta_fact.value))],
                        date_mentions=[],
                    )
                )

        return claims

    def _synthesize_abnormal(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
        analyte: str,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []
        abnormal_facts = [
            o for o in observed_facts
            if str(o.flag or "").lower() in ("abnormal", "high", "low", "critical", "h", "l")
        ]

        if not abnormal_facts:
            # All selected observations are within normal limits
            latest = observed_facts[-1]
            claims.append(
                GroundedClaim(
                    claim_id="claim_no_abnormality",
                    sentence=(
                        f"No abnormal readings were identified for {analyte}; "
                        f"the most recent measurement on {latest.observation_date[:10]} was {latest.value} {latest.unit} [{latest.evidence_id}]."
                    ),
                    fact_type=FactType.OBSERVED,
                    evidence_ids=[latest.evidence_id],
                    numeric_values=[float(latest.value)] if isinstance(latest.value, (int, float)) else [],
                    date_mentions=[latest.observation_date[:10]],
                )
            )
            return claims

        # First abnormal reading
        first_abn = abnormal_facts[0]
        claims.append(
            GroundedClaim(
                claim_id="claim_first_abnormal",
                sentence=(
                    f"The earliest abnormal {analyte} result on record was {first_abn.value} {first_abn.unit} "
                    f"(flagged as {first_abn.flag}) on {first_abn.observation_date[:10]} [{first_abn.evidence_id}]."
                ),
                fact_type=FactType.OBSERVED,
                evidence_ids=[first_abn.evidence_id],
                numeric_values=[float(first_abn.value)] if isinstance(first_abn.value, (int, float)) else [],
                date_mentions=[first_abn.observation_date[:10]],
            )
        )

        return claims

    def _synthesize_date_comparison(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
        analyte: str,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []
        if len(observed_facts) == 1:
            return self._synthesize_current_value(package, observed_facts, derived_facts, analyte)

        o_a = observed_facts[0]
        o_b = observed_facts[-1]

        claims.append(
            GroundedClaim(
                claim_id="claim_comp_points",
                sentence=(
                    f"Comparing {analyte} levels: {o_a.value} {o_a.unit} was recorded on {o_a.observation_date[:10]} [{o_a.evidence_id}], "
                    f"and {o_b.value} {o_b.unit} was recorded on {o_b.observation_date[:10]} [{o_b.evidence_id}]."
                ),
                fact_type=FactType.OBSERVED,
                evidence_ids=[o_a.evidence_id, o_b.evidence_id],
                numeric_values=[float(o_a.value), float(o_b.value)] if isinstance(o_a.value, (int, float)) and isinstance(o_b.value, (int, float)) else [],
                date_mentions=[o_a.observation_date[:10], o_b.observation_date[:10]],
            )
        )

        delta_fact = next((df for df in derived_facts if df.metric == "absolute_delta"), None)
        dir_fact = next((df for df in derived_facts if df.metric == "direction"), None)
        span_fact = next((df for df in derived_facts if df.metric == "span_days"), None)

        if delta_fact and dir_fact:
            span_clause = f" over {int(float(span_fact.value))} days" if span_fact and isinstance(span_fact.value, (int, float)) else ""
            claims.append(
                GroundedClaim(
                    claim_id="claim_comp_diff",
                    sentence=(
                        f"This represents a net {dir_fact.value} of {abs(float(delta_fact.value)):g} {delta_fact.unit}{span_clause} "
                        f"[{o_a.evidence_id}, {o_b.evidence_id}]."
                    ),
                    fact_type=FactType.DERIVED,
                    evidence_ids=[o_a.evidence_id, o_b.evidence_id],
                    numeric_values=[abs(float(delta_fact.value))],
                    date_mentions=[],
                )
            )

        return claims

    def _synthesize_historical_interval(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
        analyte: str,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []
        count = len(observed_facts)
        o_first = observed_facts[0]
        o_last = observed_facts[-1]

        claims.append(
            GroundedClaim(
                claim_id="claim_interval_span",
                sentence=(
                    f"During the requested period ({o_first.observation_date[:10]} to {o_last.observation_date[:10]}), "
                    f"{count} {analyte} observation(s) were recorded [{o_first.evidence_id}, {o_last.evidence_id}]."
                ),
                fact_type=FactType.OBSERVED,
                evidence_ids=[o_first.evidence_id, o_last.evidence_id],
                numeric_values=[],
                date_mentions=[o_first.observation_date[:10], o_last.observation_date[:10]],
            )
        )

        if count > 1:
            delta_fact = next((df for df in derived_facts if df.metric == "absolute_delta"), None)
            dir_fact = next((df for df in derived_facts if df.metric == "direction"), None)
            if delta_fact and dir_fact:
                claims.append(
                    GroundedClaim(
                        claim_id="claim_interval_delta",
                        sentence=(
                            f"Over this interval, {analyte} {dir_fact.value} from {o_first.value} {o_first.unit} "
                            f"to {o_last.value} {o_last.unit} [{o_first.evidence_id}, {o_last.evidence_id}]."
                        ),
                        fact_type=FactType.DERIVED,
                        evidence_ids=[o_first.evidence_id, o_last.evidence_id],
                        numeric_values=[float(o_first.value), float(o_last.value)] if isinstance(o_first.value, (int, float)) and isinstance(o_last.value, (int, float)) else [],
                        date_mentions=[],
                    )
                )

        return claims

    def _synthesize_longitudinal_trend(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
        derived_facts: Sequence[DerivedFact],
        analyte: str,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []
        n_count = len(observed_facts)

        if n_count == 1:
            return self._synthesize_current_value(package, observed_facts, derived_facts, analyte)

        baseline = observed_facts[0]
        endpoint = observed_facts[-1]

        # 1. Baseline and Endpoint Statement
        claims.append(
            GroundedClaim(
                claim_id="claim_trend_anchors",
                sentence=(
                    f"Your {analyte} longitudinal trajectory spans from a baseline of {baseline.value} {baseline.unit} "
                    f"on {baseline.observation_date[:10]} [{baseline.evidence_id}] to {endpoint.value} {endpoint.unit} "
                    f"on {endpoint.observation_date[:10]} [{endpoint.evidence_id}]."
                ),
                fact_type=FactType.OBSERVED,
                evidence_ids=[baseline.evidence_id, endpoint.evidence_id],
                numeric_values=[float(baseline.value), float(endpoint.value)] if isinstance(baseline.value, (int, float)) and isinstance(endpoint.value, (int, float)) else [],
                date_mentions=[baseline.observation_date[:10], endpoint.observation_date[:10]],
            )
        )

        # 2. Inflection point if detected
        inflection_fact = next((df for df in derived_facts if df.metric == "inflection_point"), None)
        if inflection_fact:
            inflection_obs = next(
                (o for o in observed_facts if o.role == "inflection_point" or o.observation_date == inflection_fact.start_date),
                None,
            )
            if inflection_obs:
                claims.append(
                    GroundedClaim(
                        claim_id="claim_trend_inflection",
                        sentence=(
                            f"During this period, a notable peak was recorded on {inflection_obs.observation_date[:10]} "
                            f"at {inflection_obs.value} {inflection_obs.unit} [{inflection_obs.evidence_id}]."
                        ),
                        fact_type=FactType.DERIVED,
                        evidence_ids=[inflection_obs.evidence_id],
                        numeric_values=[float(inflection_obs.value)] if isinstance(inflection_obs.value, (int, float)) else [],
                        date_mentions=[inflection_obs.observation_date[:10]],
                    )
                )

        # 3. Overall Dynamics (Delta, Direction, Span)
        delta_fact = next((df for df in derived_facts if df.metric == "absolute_delta"), None)
        dir_fact = next((df for df in derived_facts if df.metric == "direction"), None)
        span_fact = next((df for df in derived_facts if df.metric == "span_days"), None)

        if delta_fact and dir_fact:
            span_clause = f" over {int(float(span_fact.value))} days" if span_fact and isinstance(span_fact.value, (int, float)) else ""
            claims.append(
                GroundedClaim(
                    claim_id="claim_trend_dynamics",
                    sentence=(
                        f"Overall, your {analyte} has {dir_fact.value} by {abs(float(delta_fact.value)):g} {delta_fact.unit}{span_clause} "
                        f"[{baseline.evidence_id}, {endpoint.evidence_id}]."
                    ),
                    fact_type=FactType.DERIVED,
                    evidence_ids=[baseline.evidence_id, endpoint.evidence_id],
                    numeric_values=[abs(float(delta_fact.value))],
                    date_mentions=[],
                )
            )

        return claims

    # -------------------------------------------------------------------------
    # Constrained Clinical Interpretation Layer
    # -------------------------------------------------------------------------

    def _build_constrained_interpretations(
        self,
        package: LongitudinalEvidencePackage,
        observed_facts: Sequence[ObservedFact],
    ) -> tuple[list[ClinicalInterpretation], list[GroundedClaim]]:
        interpretations: list[ClinicalInterpretation] = []
        claims: list[GroundedClaim] = []

        for obs in observed_facts:
            flag_str = str(obs.flag or "").lower()
            if flag_str in ("abnormal", "high", "low", "critical", "h", "l"):
                interp = ClinicalInterpretation(
                    evidence_id=obs.evidence_id,
                    statement=(
                        f"The reading of {obs.value} {obs.unit} on {obs.observation_date[:10]} was flagged as {obs.flag} "
                        f"relative to standard clinical reference thresholds. Individual laboratory values should be interpreted "
                        f"in consultation with your healthcare provider [{obs.evidence_id}]."
                    ),
                    reference_context=f"Flag: {obs.flag}",
                    policy=InterpretationPolicy.CONSTRAINED_REFERENCE_ONLY,
                )
                interpretations.append(interp)

                claim = GroundedClaim(
                    claim_id=f"claim_interp_{obs.evidence_id}",
                    sentence=interp.statement,
                    fact_type=FactType.INTERPRETATION,
                    evidence_ids=[obs.evidence_id],
                    numeric_values=[float(obs.value)] if isinstance(obs.value, (int, float)) else [],
                    date_mentions=[obs.observation_date[:10]],
                )
                claims.append(claim)

        return interpretations, claims

    # -------------------------------------------------------------------------
    # Fallback Handling
    # -------------------------------------------------------------------------

    def _build_empty_fallback(
        self,
        package: LongitudinalEvidencePackage,
        policy: InterpretationPolicy,
    ) -> GroundedEvidenceSynthesis:
        analyte = package.target_analyte or "clinical measurements"
        msg = f"No eligible observations for {analyte} were identified in the specified timeframe."

        audit_report = self.verifier.audit_synthesis(
            package=package,
            claims=[],
            observed_facts=[],
            derived_facts=[],
            interpretation_policy=policy.value,
        )

        return GroundedEvidenceSynthesis(
            query_id=package.query_id,
            patient_id=package.patient_id,
            raw_query=package.raw_query,
            query_intent=package.query_intent,
            target_analyte=package.target_analyte,
            summary_text=msg,
            claims=[],
            observed_facts=[],
            derived_facts=[],
            interpretations=[],
            audit_report=audit_report,
            evidence_package_version=package.version,
            version="1.0",
        )
