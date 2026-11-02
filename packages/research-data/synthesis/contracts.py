"""
packages/research-data/synthesis/contracts.py

Domain Contracts for Grounded Clinical Evidence Synthesis (CP-09).
Provides typed representations for:
  - FactType (OBSERVED, DERIVED, INTERPRETATION)
  - InterpretationPolicy (DISABLED, CONSTRAINED_REFERENCE_ONLY)
  - ObservedFact (verbatim from observation)
  - DerivedFact (deterministic mathematical calculation)
  - ClinicalInterpretation (non-prescriptive contextual remark)
  - GroundedClaim (sentence/claim with explicit evidence_id provenance)
  - GroundingAuditReport (audit metrics verifying 100% claim-level grounding)
  - GroundedEvidenceSynthesis (versioned synthesis artifact)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class FactType(str, Enum):
    """Classification of clinical facts within a synthesized response."""

    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    INTERPRETATION = "INTERPRETATION"


class InterpretationPolicy(str, Enum):
    """Policy governing clinical interpretations."""

    DISABLED = "DISABLED"
    CONSTRAINED_REFERENCE_ONLY = "CONSTRAINED_REFERENCE_ONLY"


@dataclass(frozen=True)
class ObservedFact:
    """
    An objective observation fact directly extracted from a single evidence observation.
    Must be traceable to exactly one evidence_id.
    """

    evidence_id: str
    observation_date: str
    analyte_canonical: str
    value: float | str | None
    unit: str
    flag: str | None
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    loinc_code: str | None = None
    concept_id: str | None = None
    source_provenance: str = ""
    role: str = "selected"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DerivedFact:
    """
    A mathematical calculation derived deterministically from two or more observations.
    Must be traceable to a specific set of contributing evidence_ids.
    """

    metric: str  # absolute_delta, relative_change, slope_per_day, direction, span_days, inflection
    value: float | str | None
    unit: str
    contributing_evidence_ids: list[str]
    description: str
    start_date: str | None = None
    end_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "contributing_evidence_ids": list(self.contributing_evidence_ids),
            "description": self.description,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


@dataclass(frozen=True)
class ClinicalInterpretation:
    """
    A strictly non-diagnostic contextual interpretation.
    Must NOT state disease diagnosis, progression causality, or treatment advice.
    """

    evidence_id: str
    statement: str
    reference_context: str
    policy: InterpretationPolicy = InterpretationPolicy.CONSTRAINED_REFERENCE_ONLY

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "statement": self.statement,
            "reference_context": self.reference_context,
            "policy": self.policy.value,
        }


@dataclass
class GroundedClaim:
    """
    A single claim/sentence in the synthesized response with claim-level provenance.
    Every numerical or temporal statement must be traceable to one or more evidence_ids.
    """

    claim_id: str
    sentence: str
    fact_type: FactType
    evidence_ids: list[str]
    numeric_values: list[float] = field(default_factory=list)
    date_mentions: list[str] = field(default_factory=list)
    is_grounded: bool = False
    verification_details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "sentence": self.sentence,
            "fact_type": self.fact_type.value,
            "evidence_ids": list(self.evidence_ids),
            "numeric_values": list(self.numeric_values),
            "date_mentions": list(self.date_mentions),
            "is_grounded": self.is_grounded,
            "verification_details": dict(self.verification_details),
        }


@dataclass
class GroundingAuditReport:
    """Audit verification of claim-level grounding and provenance completeness."""

    total_claims: int = 0
    grounded_claims: int = 0
    unsupported_claims: int = 0
    claim_grounding_rate: float = 0.0
    evidence_utilization_rate: float = 0.0
    hallucination_detected: bool = False
    interpretation_policy: str = "DISABLED"
    audit_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_claims": self.total_claims,
            "grounded_claims": self.grounded_claims,
            "unsupported_claims": self.unsupported_claims,
            "claim_grounding_rate": round(self.claim_grounding_rate, 4),
            "evidence_utilization_rate": round(self.evidence_utilization_rate, 4),
            "hallucination_detected": self.hallucination_detected,
            "interpretation_policy": self.interpretation_policy,
            "audit_notes": list(self.audit_notes),
        }


@dataclass
class GroundedEvidenceSynthesis:
    """
    Versioned domain representation of a grounded clinical evidence synthesis (CP-09).
    Combines structured facts, natural synthesis text, claim-level provenance mappings,
    and audit verification.
    """

    query_id: str | None
    patient_id: str
    raw_query: str
    query_intent: str
    target_analyte: str | None
    summary_text: str
    claims: list[GroundedClaim]
    observed_facts: list[ObservedFact]
    derived_facts: list[DerivedFact]
    interpretations: list[ClinicalInterpretation]
    audit_report: GroundingAuditReport
    evidence_package_version: str = "1.0"
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "patient_id": self.patient_id,
            "raw_query": self.raw_query,
            "query_intent": self.query_intent,
            "target_analyte": self.target_analyte,
            "summary_text": self.summary_text,
            "claims": [c.to_dict() for c in self.claims],
            "observed_facts": [f.to_dict() for f in self.observed_facts],
            "derived_facts": [f.to_dict() for f in self.derived_facts],
            "interpretations": [i.to_dict() for i in self.interpretations],
            "audit_report": self.audit_report.to_dict(),
            "evidence_package_version": self.evidence_package_version,
            "version": self.version,
        }
