"""
packages/research-data/terminology.py

Clinical terminology mapper for longitudinal research evidence (CP-03).
Leverages MediVault's existing vocabulary architecture and strictly rejects
fabrication of fake LOINC codes or concepts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from models.normalizer.vocabulary import (
    CANONICAL_CONCEPTS,
    EXTENDED_CONCEPTS,
    SYNTHETIC_SYNONYMS,
    alias_lookup_table,
    build_full_vocabulary,
    loinc_for,
    unit_for,
)
from packages.research_data.models import MappingStatus


# Direct LOINC code to canonical analyte dictionary
LOINC_TO_CANONICAL: dict[str, dict[str, Any]] = {
    # CBC
    "718-7": {"canonical": "Haemoglobin", "panel": "CBC", "unit": "g/dL"},
    "6690-2": {"canonical": "WBC", "panel": "CBC", "unit": "/µL"},
    "789-8": {"canonical": "RBC", "panel": "CBC", "unit": "million/µL"},
    "777-3": {"canonical": "Platelets", "panel": "CBC", "unit": "/µL"},
    "4544-3": {"canonical": "Hematocrit", "panel": "CBC", "unit": "%"},
    "787-2": {"canonical": "MCV", "panel": "CBC", "unit": "fL"},
    "785-6": {"canonical": "MCH", "panel": "CBC", "unit": "pg"},
    "786-4": {"canonical": "MCHC", "panel": "CBC", "unit": "g/dL"},
    "770-8": {"canonical": "Neutrophils", "panel": "CBC", "unit": "%"},
    "736-9": {"canonical": "Lymphocytes", "panel": "CBC", "unit": "%"},
    "5905-5": {"canonical": "Monocytes", "panel": "CBC", "unit": "%"},
    "711-2": {"canonical": "Eosinophils", "panel": "CBC", "unit": "%"},
    "704-7": {"canonical": "Basophils", "panel": "CBC", "unit": "%"},
    # Lipid
    "2093-3": {"canonical": "Total Cholesterol", "panel": "Lipid Profile", "unit": "mg/dL"},
    "2089-1": {"canonical": "LDL Cholesterol", "panel": "Lipid Profile", "unit": "mg/dL"},
    "2085-9": {"canonical": "HDL Cholesterol", "panel": "Lipid Profile", "unit": "mg/dL"},
    "2571-8": {"canonical": "Triglycerides", "panel": "Lipid Profile", "unit": "mg/dL"},
    "13457-7": {"canonical": "VLDL Cholesterol", "panel": "Lipid Profile", "unit": "mg/dL"},
    "43396-1": {"canonical": "Non-HDL Cholesterol", "panel": "Lipid Profile", "unit": "mg/dL"},
    "9830-1": {"canonical": "TC/HDL Ratio", "panel": "Lipid Profile", "unit": None},
    # Thyroid
    "3016-3": {"canonical": "TSH", "panel": "Thyroid", "unit": "µIU/mL"},
    "3053-6": {"canonical": "T3", "panel": "Thyroid", "unit": "ng/dL"},
    "3026-2": {"canonical": "T4", "panel": "Thyroid", "unit": "µg/dL"},
    "3051-0": {"canonical": "Free T3", "panel": "Thyroid", "unit": "pg/mL"},
    "3024-7": {"canonical": "Free T4", "panel": "Thyroid", "unit": "ng/dL"},
    # Diabetes & Metabolic
    "4548-4": {"canonical": "HbA1c", "panel": "HbA1c", "unit": "%"},
    "27353-2": {"canonical": "eAG (Est. Avg Glucose)", "panel": "HbA1c", "unit": "mg/dL"},
    "2345-7": {"canonical": "Glucose", "panel": "Metabolic", "unit": "mg/dL"},
    # LFT & RFT
    "1742-6": {"canonical": "Alanine Aminotransferase", "panel": "LFT", "unit": "U/L"},
    "1920-8": {"canonical": "Aspartate Aminotransferase", "panel": "LFT", "unit": "U/L"},
    "6768-6": {"canonical": "Alkaline Phosphatase", "panel": "LFT", "unit": "U/L"},
    "1975-2": {"canonical": "Bilirubin Total", "panel": "LFT", "unit": "mg/dL"},
    "2160-0": {"canonical": "Creatinine", "panel": "RFT", "unit": "mg/dL"},
    "3094-0": {"canonical": "Urea", "panel": "RFT", "unit": "mg/dL"},
}


@dataclass
class TerminologyMappingResult:
    analyte_raw: str
    analyte_canonical: str | None
    concept_id: str | None
    loinc_code: str | None
    mapping_status: MappingStatus
    canonical_unit: str | None


class ClinicalTerminologyMapper:
    """
    Deterministic clinical terminology mapper.
    Precedence:
      1. Exact LOINC code match (highest confidence).
      2. Surface alias / text normalization match via MediVault vocabulary.
      3. Unmapped fallback (preserves raw text, does not fabricate concept/LOINC).
    """

    def __init__(self) -> None:
        self._loinc_map = LOINC_TO_CANONICAL
        self._alias_map = alias_lookup_table()
        # Add additional common Synthea and MIMIC descriptions to alias map
        self._extend_common_aliases()

    def _extend_common_aliases(self) -> None:
        extra_aliases: dict[str, str] = {
            "glycated hemoglobin (hba1c)": "HbA1c",
            "glycated haemoglobin (hba1c)": "HbA1c",
            "glycated hemoglobin": "HbA1c",
            "glycated haemoglobin": "HbA1c",
            "glucose": "Glucose",
            "glucose [mass/volume] in serum or plasma": "Glucose",
            "blood glucose": "Glucose",
            "fasting glucose": "Glucose",
            "low density lipoprotein cholesterol": "LDL Cholesterol",
            "high density lipoprotein cholesterol": "HDL Cholesterol",
            "cholesterol [mass/volume] in serum or plasma": "Total Cholesterol",
            "triglyceride [mass/volume] in serum or plasma": "Triglycerides",
            "hemoglobin [mass/volume] in blood": "Haemoglobin",
            "hemoglobin a1c/hemoglobin.total in blood": "HbA1c",
            "leukocytes [#/volume] in blood by automated count": "WBC",
            "platelets [#/volume] in blood by automated count": "Platelets",
            "creatinine [mass/volume] in blood": "Creatinine",
            "thyrotropin [units/volume] in serum or plasma": "TSH",
            "alanine aminotransferase [enzymatic activity/volume] in serum or plasma": "Alanine Aminotransferase",
            "aspartate aminotransferase [enzymatic activity/volume] in serum or plasma": "Aspartate Aminotransferase",
            "alkaline phosphatase [enzymatic activity/volume] in serum or plasma": "Alkaline Phosphatase",
            "bilirubin.total [mass/volume] in serum or plasma": "Bilirubin Total",
            "urea nitrogen": "Urea",
            "blood urea nitrogen": "Urea",
            "bun": "Urea",
            "cholesterol, total": "Total Cholesterol",
            "cholesterol, ldl, calculated": "LDL Cholesterol",
            "cholesterol, hdl": "HDL Cholesterol",
            "platelet count": "Platelets",
            "white blood cells": "WBC",
            "red blood cells": "RBC",
        }
        for alias, canon in extra_aliases.items():
            clean = alias.strip().lower()
            if clean not in self._alias_map:
                self._alias_map[clean] = canon

    def map_analyte(
        self,
        analyte_raw: str,
        provided_loinc: str | None = None,
    ) -> TerminologyMappingResult:
        raw_clean = (analyte_raw or "").strip()
        loinc_clean = (provided_loinc or "").strip() if provided_loinc else None

        # 1. Exact LOINC match
        if loinc_clean and loinc_clean in self._loinc_map:
            meta = self._loinc_map[loinc_clean]
            return TerminologyMappingResult(
                analyte_raw=raw_clean,
                analyte_canonical=meta["canonical"],
                concept_id=f"LOINC:{loinc_clean}",
                loinc_code=loinc_clean,
                mapping_status="exact_loinc",
                canonical_unit=meta.get("unit"),
            )

        # 2. Surface form alias match
        norm_key = re.sub(r"\s+", " ", raw_clean.lower())
        canon: str | None = self._alias_map.get(norm_key)

        # Parenthetical fallback
        if not canon and ("(" in norm_key or "[" in norm_key):
            without_symbols = re.sub(r"[\(\[\)\]]", " ", norm_key)
            without_symbols = re.sub(r"\s+", " ", without_symbols).strip()
            if without_symbols in self._alias_map:
                canon = self._alias_map[without_symbols]

            if not canon:
                # Check stripped of parenthetical phrases
                stripped_parens = re.sub(r"\(.*?\)|\[.*?\]", "", norm_key).strip()
                if stripped_parens in self._alias_map:
                    canon = self._alias_map[stripped_parens]

            if not canon:
                # Check contents inside parentheses
                for inside in re.findall(r"\((.*?)\)|\[(.*?)\]", norm_key):
                    for match_item in inside:
                        m_clean = match_item.strip()
                        if m_clean and m_clean in self._alias_map:
                            canon = self._alias_map[m_clean]
                            break
                    if canon:
                        break

        if canon:
            known_loinc = loinc_for(canon)
            # Check LOINC reverse map if not found
            if not known_loinc:
                for l_code, l_meta in self._loinc_map.items():
                    if l_meta["canonical"].lower() == canon.lower():
                        known_loinc = l_code
                        break

            return TerminologyMappingResult(
                analyte_raw=raw_clean,
                analyte_canonical=canon,
                concept_id=f"LOINC:{known_loinc}" if known_loinc else f"CANONICAL:{canon}",
                loinc_code=known_loinc,
                mapping_status="canonical_normalized",
                canonical_unit=unit_for(canon),
            )

        # 3. Unmapped fallback — preserve raw text, do NOT fabricate concept or LOINC
        return TerminologyMappingResult(
            analyte_raw=raw_clean,
            analyte_canonical=None,
            concept_id=None,
            loinc_code=None,
            mapping_status="unmapped",
            canonical_unit=None,
        )
