"""
tests/unit/research-data/test_mimic_parser.py

Verifies MIMIC-IV Demo CSV source parsing (CP-03):
- labevents.csv + d_labitems.csv joining
- reference ranges and flag extraction
- patient and encounter relationship preservation
"""

from __future__ import annotations

from pathlib import Path
import pytest

from packages.research_data.parsers.mimic_parser import MimicDemoParser


class TestMimicDemoParser:
    def test_parse_mimic_demo_sample(self):
        labevents_path = Path("datasets/clinical/mimic_demo/sample/labevents.csv")
        d_labitems_path = Path("datasets/clinical/mimic_demo/sample/d_labitems.csv")

        assert labevents_path.exists()
        assert d_labitems_path.exists()

        parser = MimicDemoParser()
        records = parser.parse_labevents_file(labevents_path, d_labitems_path)

        assert len(records) == 8
        first = records[0]
        assert first.dataset == "mimic_demo"
        assert first.source_patient_id == "10000032"
        assert first.source_encounter_id == "22595853"
        assert first.analyte_canonical == "LDL Cholesterol"
        assert first.value_numeric == 115.0
        assert first.unit == "mg/dL"
        assert first.flag == "abnormal"
        assert first.reference_high == 100.0

    def test_missing_d_labitems_file_raises_error(self):
        parser = MimicDemoParser()
        with pytest.raises(FileNotFoundError):
            parser.load_d_labitems("non_existent_file.csv")
