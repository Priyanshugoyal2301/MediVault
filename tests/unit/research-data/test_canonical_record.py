"""
tests/unit/research-data/test_canonical_record.py

Verifies canonical ResearchEvidenceRecord model integrity (CP-03):
- schema contracts
- non-fabrication of missing fields
- dictionary serialization/deserialization
- provenance tracking
"""

from __future__ import annotations

import pytest

from packages.research_data.models import ResearchEvidenceRecord


class TestResearchEvidenceRecord:
    def test_record_instantiation_with_mandatory_fields(self):
        rec = ResearchEvidenceRecord(
            id="synthea:pat_1:row_1",
            dataset="synthea",
            source_patient_id="pat_1",
            source_encounter_id="enc_1",
            source_record_id="row_1",
            observation_date="2024-01-15T09:00:00Z",
            analyte_raw="Hemoglobin [Mass/volume] in Blood",
            analyte_canonical="Haemoglobin",
            concept_id="LOINC:718-7",
            loinc_code="718-7",
            value_numeric=14.2,
            value_text="14.2",
            unit="g/dL",
            mapping_status="exact_loinc",
            source_provenance="synthea:observations.csv:row_1",
        )

        assert rec.id == "synthea:pat_1:row_1"
        assert rec.dataset == "synthea"
        assert rec.value_numeric == 14.2
        assert rec.mapping_status == "exact_loinc"

    def test_missing_fields_remain_none_not_fabricated(self):
        """Optional clinical attributes must remain None, never manufactured."""
        rec = ResearchEvidenceRecord(
            id="synthea:pat_2:row_99",
            dataset="synthea",
            source_patient_id="pat_2",
            source_encounter_id=None,
            source_record_id="row_99",
            observation_date="2024-03-20",
            analyte_raw="Experimental Research Biomarker X",
        )

        assert rec.source_encounter_id is None
        assert rec.analyte_canonical is None
        assert rec.concept_id is None
        assert rec.loinc_code is None
        assert rec.value_numeric is None
        assert rec.value_text is None
        assert rec.unit is None
        assert rec.reference_low is None
        assert rec.reference_high is None
        assert rec.mapping_status == "unmapped"

    def test_to_dict_and_from_dict_roundtrip(self):
        rec = ResearchEvidenceRecord(
            id="mimic:subj_100:event_555",
            dataset="mimic_demo",
            source_patient_id="subj_100",
            source_encounter_id="hadm_999",
            source_record_id="event_555",
            observation_date="2180-05-12 10:00:00",
            analyte_raw="Cholesterol, LDL, Calculated",
            analyte_canonical="LDL Cholesterol",
            concept_id="LOINC:2089-1",
            loinc_code="2089-1",
            value_numeric=138.0,
            value_text="138",
            unit="mg/dL",
            reference_low=0.0,
            reference_high=100.0,
            mapping_status="exact_loinc",
            source_provenance="mimic:labevents.csv:event_555",
            flag="abnormal",
        )

        d = rec.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == "mimic:subj_100:event_555"
        assert d["value_numeric"] == 138.0
        assert d["flag"] == "abnormal"

        restored = ResearchEvidenceRecord.from_dict(d)
        assert restored.id == rec.id
        assert restored.value_numeric == rec.value_numeric
        assert restored.observation_date == rec.observation_date
        assert restored.flag == rec.flag
