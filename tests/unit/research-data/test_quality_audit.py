"""
tests/unit/research-data/test_quality_audit.py

Verifies Data Quality Audit calculations (CP-03):
- total observations & patients
- longitudinal patient count (patients with >= 2 observations)
- missing dates & units tracking
- duplicate detection
- coverage percentages
"""

from __future__ import annotations

import json
import pytest

from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.quality_audit import DataQualityAuditor


class TestDataQualityAuditor:
    def test_audit_computes_correct_metrics(self):
        records = [
            # Patient 1: 3 observations (longitudinal)
            ResearchEvidenceRecord(
                id="1", dataset="test", source_patient_id="P1", source_encounter_id="E1",
                source_record_id="1", observation_date="2022-01-01", analyte_raw="LDL",
                analyte_canonical="LDL Cholesterol", loinc_code="2089-1", value_numeric=120.0,
                unit="mg/dL", mapping_status="exact_loinc",
            ),
            ResearchEvidenceRecord(
                id="2", dataset="test", source_patient_id="P1", source_encounter_id="E2",
                source_record_id="2", observation_date="2022-06-01", analyte_raw="LDL",
                analyte_canonical="LDL Cholesterol", loinc_code="2089-1", value_numeric=130.0,
                unit="mg/dL", mapping_status="exact_loinc",
            ),
            ResearchEvidenceRecord(
                id="3", dataset="test", source_patient_id="P1", source_encounter_id="E3",
                source_record_id="3", observation_date="2023-01-01", analyte_raw="LDL",
                analyte_canonical="LDL Cholesterol", loinc_code="2089-1", value_numeric=140.0,
                unit="mg/dL", mapping_status="exact_loinc",
            ),
            # Patient 2: 1 observation (not longitudinal)
            ResearchEvidenceRecord(
                id="4", dataset="test", source_patient_id="P2", source_encounter_id="E1",
                source_record_id="4", observation_date="2023-05-01", analyte_raw="Unknown Test",
                analyte_canonical=None, loinc_code=None, value_numeric=10.0,
                unit=None, mapping_status="unmapped",
            ),
        ]

        auditor = DataQualityAuditor()
        report = auditor.audit(records, dataset_name="unit_test_cohort")

        assert report.total_observations == 4
        assert report.total_source_patients == 2
        assert report.longitudinal_patients == 1  # Only P1 has >= 2 observations
        assert report.distinct_raw_analytes == 2
        assert report.distinct_canonical_analytes == 1
        assert report.date_range_start == "2022-01-01"
        assert report.date_range_end == "2023-05-01"
        assert report.missing_dates_count == 0
        assert report.missing_units_count == 1  # P2 has unit=None
        assert report.normalization_coverage_pct == 75.0  # 3 of 4 normalized
        assert report.loinc_mapping_coverage_pct == 75.0  # 3 of 4 have LOINC
        assert report.duplicated_observations_count == 0

        # Check JSON serialization
        as_json = report.to_json()
        parsed = json.loads(as_json)
        assert parsed["total_observations"] == 4
