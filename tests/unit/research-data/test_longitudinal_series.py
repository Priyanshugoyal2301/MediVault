"""
tests/unit/research-data/test_longitudinal_series.py

Verifies longitudinal clinical sequence reconstruction (CP-03):
- chronological sorting t1 <= t2 <= ... <= tn
- preservation of repeated observations (no collapsing to latest value)
- multi-encounter patient tracking
"""

from __future__ import annotations

import pytest

from packages.research_data.models import LongitudinalSeries, ResearchEvidenceRecord


class TestLongitudinalSeries:
    def test_chronological_ordering_is_strictly_enforced(self):
        # Create un-ordered observations for same patient & analyte
        rec_t3 = ResearchEvidenceRecord(
            id="r3",
            dataset="synthea",
            source_patient_id="P1",
            source_encounter_id="E3",
            source_record_id="3",
            observation_date="2023-09-01T10:00:00Z",
            analyte_raw="LDL",
            analyte_canonical="LDL Cholesterol",
            value_numeric=145.0,
        )
        rec_t1 = ResearchEvidenceRecord(
            id="r1",
            dataset="synthea",
            source_patient_id="P1",
            source_encounter_id="E1",
            source_record_id="1",
            observation_date="2021-03-15T09:00:00Z",
            analyte_raw="LDL",
            analyte_canonical="LDL Cholesterol",
            value_numeric=112.0,
        )
        rec_t2 = ResearchEvidenceRecord(
            id="r2",
            dataset="synthea",
            source_patient_id="P1",
            source_encounter_id="E2",
            source_record_id="2",
            observation_date="2022-05-20T08:30:00Z",
            analyte_raw="LDL",
            analyte_canonical="LDL Cholesterol",
            value_numeric=128.0,
        )

        series = LongitudinalSeries(patient_id="P1", analyte="LDL Cholesterol", records=[rec_t3, rec_t1, rec_t2])
        assert series.count == 3
        assert series.is_longitudinal is True

        series.sort_chronologically()

        assert series.records[0].id == "r1"
        assert series.records[0].observation_date == "2021-03-15T09:00:00Z"
        assert series.records[0].value_numeric == 112.0

        assert series.records[1].id == "r2"
        assert series.records[1].observation_date == "2022-05-20T08:30:00Z"
        assert series.records[1].value_numeric == 128.0

        assert series.records[2].id == "r3"
        assert series.records[2].observation_date == "2023-09-01T10:00:00Z"
        assert series.records[2].value_numeric == 145.0

    def test_repeated_observations_preserved_not_collapsed(self):
        """Historical observations must remain independently retrievable."""
        recs = [
            ResearchEvidenceRecord(
                id=f"r_{i}",
                dataset="synthea",
                source_patient_id="P2",
                source_encounter_id=f"E_{i}",
                source_record_id=str(i),
                observation_date=f"202{i}-01-01",
                analyte_raw="HbA1c",
                analyte_canonical="HbA1c",
                value_numeric=5.5 + i * 0.3,
            )
            for i in range(1, 5)
        ]

        series = LongitudinalSeries(patient_id="P2", analyte="HbA1c", records=recs)
        series.sort_chronologically()

        assert series.count == 4
        # Assert all 4 distinct historical points exist
        assert [r.value_numeric for r in series.records] == [5.8, 6.1, 6.4, 6.7]
