"""
tests/unit/ai-service/test_evidence_retriever.py

Unit test suite for LongitudinalEvidenceRetrieverAdapter (CP-06 Phase 14).
Verifies adapter behavior, query parsing integration, patient scoping, and decoupled execution.
"""

from __future__ import annotations

import pytest

from packages.research_data.models import ResearchEvidenceRecord
from services.ai_service.adapters.evidence_retriever import (
    LongitudinalEvidenceRetrieverAdapter,
)


@pytest.fixture
def patient_records() -> list[ResearchEvidenceRecord]:
    return [
        ResearchEvidenceRecord(
            id="rec_1",
            dataset="synthea",
            source_patient_id="patient_abc",
            source_encounter_id="enc_1",
            source_record_id="row_1",
            observation_date="2023-04-10T10:00:00Z",
            analyte_raw="Fasting Glucose",
            analyte_canonical="Glucose",
            concept_id="LOINC:2345-7",
            loinc_code="2345-7",
            value_numeric=98.0,
            unit="mg/dL",
            flag="normal",
            source_provenance="fixture",
        ),
        ResearchEvidenceRecord(
            id="rec_2",
            dataset="synthea",
            source_patient_id="patient_abc",
            source_encounter_id="enc_2",
            source_record_id="row_2",
            observation_date="2024-01-15T09:30:00Z",
            analyte_raw="Fasting Glucose",
            analyte_canonical="Glucose",
            concept_id="LOINC:2345-7",
            loinc_code="2345-7",
            value_numeric=115.0,
            unit="mg/dL",
            flag="high",
            source_provenance="fixture",
        ),
        ResearchEvidenceRecord(
            id="rec_other",
            dataset="synthea",
            source_patient_id="patient_xyz",
            source_encounter_id="enc_other",
            source_record_id="row_other",
            observation_date="2024-01-15T09:30:00Z",
            analyte_raw="Fasting Glucose",
            analyte_canonical="Glucose",
            concept_id="LOINC:2345-7",
            loinc_code="2345-7",
            value_numeric=90.0,
            unit="mg/dL",
            flag="normal",
            source_provenance="fixture",
        ),
    ]


class TestEvidenceRetrieverAdapter:
    def test_adapter_retrieves_for_patient_with_string_query(self, patient_records):
        adapter = LongitudinalEvidenceRetrieverAdapter()
        results = adapter.retrieve_for_patient(
            query="What is my latest fasting glucose?",
            evidence=patient_records,
            patient_id="patient_abc",
            top_k=2,
        )
        assert len(results) == 2
        # All results belong strictly to patient_abc
        assert all(r.patient_id == "patient_abc" for r in results)
        # Latest observation (rec_2 on 2024-01-15) must be rank 1
        assert results[0].evidence_id == "rec_2"
        assert results[0].rank == 1

    def test_adapter_unknown_patient_returns_empty(self, patient_records):
        adapter = LongitudinalEvidenceRetrieverAdapter()
        results = adapter.retrieve_for_patient(
            query="What is my latest fasting glucose?",
            evidence=patient_records,
            patient_id="nonexistent_patient",
            top_k=2,
        )
        assert results == []
