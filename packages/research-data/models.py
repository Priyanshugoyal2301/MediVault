"""
packages/research-data/models.py

Canonical research data models for longitudinal clinical Information Retrieval (CP-03).
Enforces strict architectural separation from user-uploaded application models.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Literal


MappingStatus = Literal["exact_loinc", "canonical_normalized", "unmapped"]

TemporalQueryIntent = Literal[
    "current_value",
    "previous_value",
    "last_n_observations",
    "historical_interval",
    "longitudinal_trend",
    "date_comparison",
    "first_abnormal",
]


@dataclass
class ResearchEvidenceRecord:
    """
    Canonical Research Observation representation.

    Every field represents a clinical observation from a research cohort
    (e.g., Synthea or MIMIC-IV Demo).
    Missing values must remain None/null — NO synthetic fabrication of
    missing clinical observations or LOINC codes is permitted.
    """

    id: str
    dataset: str
    source_patient_id: str
    source_encounter_id: str | None
    source_record_id: str
    observation_date: str  # ISO-8601 string YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
    analyte_raw: str
    analyte_canonical: str | None = None
    concept_id: str | None = None
    loinc_code: str | None = None
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    mapping_status: MappingStatus = "unmapped"
    source_provenance: str = ""
    flag: str | None = None  # e.g., 'abnormal', 'high', 'low', 'normal'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchEvidenceRecord:
        return cls(
            id=data["id"],
            dataset=data["dataset"],
            source_patient_id=data["source_patient_id"],
            source_encounter_id=data.get("source_encounter_id"),
            source_record_id=data["source_record_id"],
            observation_date=data["observation_date"],
            analyte_raw=data["analyte_raw"],
            analyte_canonical=data.get("analyte_canonical"),
            concept_id=data.get("concept_id"),
            loinc_code=data.get("loinc_code"),
            value_numeric=float(data["value_numeric"]) if data.get("value_numeric") is not None else None,
            value_text=data.get("value_text"),
            unit=data.get("unit"),
            reference_low=float(data["reference_low"]) if data.get("reference_low") is not None else None,
            reference_high=float(data["reference_high"]) if data.get("reference_high") is not None else None,
            mapping_status=data.get("mapping_status", "unmapped"),
            source_provenance=data.get("source_provenance", ""),
            flag=data.get("flag"),
        )


@dataclass
class LongitudinalSeries:
    """
    Chronologically ordered series of observations for a specific patient and analyte.
    Guarantees t1 <= t2 <= ... <= tn temporal ordering.
    """

    patient_id: str
    analyte: str
    records: list[ResearchEvidenceRecord] = field(default_factory=list)

    def sort_chronologically(self) -> None:
        self.records.sort(key=lambda r: r.observation_date)

    @property
    def count(self) -> int:
        return len(self.records)

    @property
    def is_longitudinal(self) -> bool:
        return len(self.records) >= 2


@dataclass
class EvaluationQuery:
    """
    Machine-readable evaluation benchmark query linking a clinical query
    to relevant evidence records for information retrieval experiments.
    """

    query_id: str
    patient_id: str
    query: str
    intent: TemporalQueryIntent
    target_analyte: str
    relevant_evidence_ids: list[str]
    split: Literal["dev", "val", "test"]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationQuery:
        return cls(
            query_id=data["query_id"],
            patient_id=data["patient_id"],
            query=data["query"],
            intent=data["intent"],
            target_analyte=data["target_analyte"],
            relevant_evidence_ids=list(data.get("relevant_evidence_ids", [])),
            split=data.get("split", "dev"),
            metadata=dict(data.get("metadata", {})),
        )
