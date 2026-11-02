"""
tests/unit/research-data/test_synthea_parser.py

Verifies Synthea CSV source parsing (CP-03):
- observations.csv ingestion
- field mappings (DATE, PATIENT, CODE, DESCRIPTION, VALUE, UNITS)
- numeric conversion and missing value handling
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from packages.research_data.parsers.synthea_parser import SyntheaParser


class TestSyntheaParser:
    def test_parse_synthea_sample_file(self):
        sample_path = Path("datasets/clinical/synthea/sample/observations.csv")
        assert sample_path.exists(), "Sample Synthea observations file must exist"

        parser = SyntheaParser()
        records = parser.parse_observations_file(sample_path, limit=50)

        assert len(records) == 50
        first = records[0]
        assert first.dataset == "synthea"
        assert first.source_patient_id != ""
        assert first.observation_date != ""
        assert first.analyte_canonical is not None
        assert first.value_numeric is not None
        assert first.mapping_status in ("exact_loinc", "canonical_normalized")

    def test_missing_required_headers_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_csv = Path(tmp_dir) / "bad.csv"
            bad_csv.write_text("SOME_COL,OTHER_COL\n1,2\n", encoding="utf-8")

            parser = SyntheaParser()
            with pytest.raises(ValueError, match="missing required headers"):
                parser.parse_observations_file(bad_csv)

    def test_non_numeric_values_preserve_value_text(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_file = Path(tmp_dir) / "observations.csv"
            csv_file.write_text(
                "DATE,PATIENT,ENCOUNTER,CODE,DESCRIPTION,VALUE,UNITS,TYPE\n"
                "2023-01-01,P1,E1,718-7,Hemoglobin,NEGATIVE,g/dL,text\n",
                encoding="utf-8",
            )

            parser = SyntheaParser()
            records = parser.parse_observations_file(csv_file)

            assert len(records) == 1
            rec = records[0]
            assert rec.value_numeric is None
            assert rec.value_text == "NEGATIVE"
            assert rec.analyte_canonical == "Haemoglobin"
