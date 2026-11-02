"""
packages/research-data/quality_audit.py

Clinical Data Quality Audit generator (CP-03).
Computes quantitative dataset statistics, longitudinal completeness,
and terminology coverage metrics in machine-readable JSON format.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from packages.research_data.models import ResearchEvidenceRecord


@dataclass
class QualityAuditReport:
    dataset: str
    total_observations: int
    total_source_patients: int
    longitudinal_patients: int
    distinct_raw_analytes: int
    distinct_canonical_analytes: int
    date_range_start: str | None
    date_range_end: str | None
    missing_dates_count: int
    missing_units_count: int
    normalization_coverage_pct: float
    loinc_mapping_coverage_pct: float
    duplicated_observations_count: int
    malformed_observations_count: int
    analytes_breakdown: dict[str, int]
    mapping_status_breakdown: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class DataQualityAuditor:
    """Audits a collection of ResearchEvidenceRecords."""

    def audit(
        self,
        records: Sequence[ResearchEvidenceRecord],
        dataset_name: str = "clinical_cohort",
        malformed_count: int = 0,
    ) -> QualityAuditReport:
        if not records:
            return QualityAuditReport(
                dataset=dataset_name,
                total_observations=0,
                total_source_patients=0,
                longitudinal_patients=0,
                distinct_raw_analytes=0,
                distinct_canonical_analytes=0,
                date_range_start=None,
                date_range_end=None,
                missing_dates_count=0,
                missing_units_count=0,
                normalization_coverage_pct=0.0,
                loinc_mapping_coverage_pct=0.0,
                duplicated_observations_count=0,
                malformed_observations_count=malformed_count,
                analytes_breakdown={},
                mapping_status_breakdown={},
            )

        total_obs = len(records)
        patients: set[str] = set()
        patient_analyte_counts: dict[tuple[str, str], int] = defaultdict(int)

        raw_analytes: set[str] = set()
        canonical_analytes: set[str] = set()
        dates: list[str] = []

        missing_dates = 0
        missing_units = 0
        normalized_count = 0
        loinc_count = 0

        mapping_status_counts: dict[str, int] = defaultdict(int)
        canonical_counts: dict[str, int] = defaultdict(int)

        # Track duplicates by (patient, date, analyte_raw, value)
        seen_keys: set[tuple[str, str, str, Any]] = set()
        duplicates_count = 0

        for r in records:
            patients.add(r.source_patient_id)
            analyte_key = r.analyte_canonical or r.analyte_raw
            patient_analyte_counts[(r.source_patient_id, analyte_key)] += 1

            raw_analytes.add(r.analyte_raw)
            if r.analyte_canonical:
                canonical_analytes.add(r.analyte_canonical)
                normalized_count += 1
                canonical_counts[r.analyte_canonical] += 1

            if r.loinc_code:
                loinc_count += 1

            mapping_status_counts[r.mapping_status] += 1

            if not r.observation_date or not str(r.observation_date).strip():
                missing_dates += 1
            else:
                dates.append(str(r.observation_date))

            if not r.unit or not str(r.unit).strip():
                missing_units += 1

            dup_key = (r.source_patient_id, r.observation_date, r.analyte_raw, r.value_numeric or r.value_text)
            if dup_key in seen_keys:
                duplicates_count += 1
            else:
                seen_keys.add(dup_key)

        # Count longitudinal patients (patient with >= 2 observations for at least one analyte)
        longitudinal_patients_set: set[str] = set()
        for (pid, _analyte), count in patient_analyte_counts.items():
            if count >= 2:
                longitudinal_patients_set.add(pid)

        sorted_dates = sorted(dates) if dates else []
        date_start = sorted_dates[0] if sorted_dates else None
        date_end = sorted_dates[-1] if sorted_dates else None

        norm_pct = round((normalized_count / total_obs) * 100.0, 2) if total_obs > 0 else 0.0
        loinc_pct = round((loinc_count / total_obs) * 100.0, 2) if total_obs > 0 else 0.0

        return QualityAuditReport(
            dataset=dataset_name,
            total_observations=total_obs,
            total_source_patients=len(patients),
            longitudinal_patients=len(longitudinal_patients_set),
            distinct_raw_analytes=len(raw_analytes),
            distinct_canonical_analytes=len(canonical_analytes),
            date_range_start=date_start,
            date_range_end=date_end,
            missing_dates_count=missing_dates,
            missing_units_count=missing_units,
            normalization_coverage_pct=norm_pct,
            loinc_mapping_coverage_pct=loinc_pct,
            duplicated_observations_count=duplicates_count,
            malformed_observations_count=malformed_count,
            analytes_breakdown=dict(sorted(canonical_counts.items(), key=lambda x: -x[1])),
            mapping_status_breakdown=dict(mapping_status_counts),
        )
