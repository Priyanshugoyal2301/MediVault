"""
tests/unit/research-data/test_terminology_mapper.py

Verifies clinical terminology mapping rules (CP-03):
- exact LOINC matching
- surface form alias normalization
- non-fabrication of LOINC codes for unknown analytes
- canonical unit extraction
"""

from __future__ import annotations

import pytest

from packages.research_data.terminology import ClinicalTerminologyMapper


class TestClinicalTerminologyMapper:
    @pytest.fixture
    def mapper(self) -> ClinicalTerminologyMapper:
        return ClinicalTerminologyMapper()

    def test_exact_loinc_mapping(self, mapper: ClinicalTerminologyMapper):
        """Standard LOINC code directly maps to canonical concept."""
        res = mapper.map_analyte(
            analyte_raw="Low Density Lipoprotein Cholesterol",
            provided_loinc="2089-1",
        )
        assert res.analyte_canonical == "LDL Cholesterol"
        assert res.loinc_code == "2089-1"
        assert res.concept_id == "LOINC:2089-1"
        assert res.mapping_status == "exact_loinc"
        assert res.canonical_unit == "mg/dL"

    def test_alias_normalization_without_loinc(self, mapper: ClinicalTerminologyMapper):
        """Surface alias resolves canonical concept and known public LOINC code."""
        res = mapper.map_analyte(
            analyte_raw="Serum Hemoglobin",
            provided_loinc=None,
        )
        assert res.analyte_canonical == "Haemoglobin"
        assert res.loinc_code == "718-7"
        assert res.mapping_status == "canonical_normalized"
        assert res.canonical_unit == "g/dL"

    def test_hba1c_alias_resolution(self, mapper: ClinicalTerminologyMapper):
        res = mapper.map_analyte(analyte_raw="Glycated Hemoglobin (HbA1c)")
        assert res.analyte_canonical == "HbA1c"
        assert res.loinc_code == "4548-4"
        assert res.mapping_status == "canonical_normalized"

    def test_unknown_analyte_does_not_fabricate_concept_or_loinc(self, mapper: ClinicalTerminologyMapper):
        """
        CP-03 Rule: If an observation cannot be confidently mapped,
        preserve raw analyte, record mapping status, do not fabricate concept.
        """
        res = mapper.map_analyte(
            analyte_raw="Special Rare Research Marker 99",
            provided_loinc=None,
        )
        assert res.analyte_canonical is None
        assert res.loinc_code is None
        assert res.concept_id is None
        assert res.mapping_status == "unmapped"
        assert res.analyte_raw == "Special Rare Research Marker 99"
