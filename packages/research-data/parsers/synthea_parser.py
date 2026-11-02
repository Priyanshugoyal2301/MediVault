"""
packages/research-data/parsers/synthea_parser.py

Synthea CSV parser for clinical research cohort ingestion (CP-03).
Maps standard Synthea observation exports into canonical ResearchEvidenceRecord format.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Generator

from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.terminology import ClinicalTerminologyMapper


logger = logging.getLogger(__name__)


class SyntheaParser:
    """
    Parses Synthea observations.csv (+ optional encounters.csv, patients.csv)
    into canonical ResearchEvidenceRecord models.
    """

    def __init__(self, mapper: ClinicalTerminologyMapper | None = None) -> None:
        self.mapper = mapper or ClinicalTerminologyMapper()

    def parse_observations_file(
        self,
        observations_csv_path: Path | str,
        limit: int | None = None,
    ) -> list[ResearchEvidenceRecord]:
        path = Path(observations_csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Synthea observations file not found: {path}")

        records: list[ResearchEvidenceRecord] = []
        with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = [c.strip().upper() for c in (reader.fieldnames or [])]
            required = {"DATE", "PATIENT", "CODE", "DESCRIPTION", "VALUE"}
            if not required.issubset(set(fieldnames)):
                raise ValueError(
                    f"Synthea observations.csv missing required headers. "
                    f"Expected subset of {required}, got {fieldnames}"
                )

            for idx, row in enumerate(reader, start=1):
                # Standardize keys to uppercase
                row_upper = {k.strip().upper(): v.strip() if v else "" for k, v in row.items()}

                date_val = row_upper.get("DATE", "")
                patient_val = row_upper.get("PATIENT", "")
                code_val = row_upper.get("CODE", "")
                desc_val = row_upper.get("DESCRIPTION", "")
                value_str = row_upper.get("VALUE", "")
                units_val = row_upper.get("UNITS", "") or None
                encounter_val = row_upper.get("ENCOUNTER", "") or None

                # Extract numeric value if valid
                numeric_val: float | None = None
                if value_str:
                    try:
                        numeric_val = float(value_str)
                    except ValueError:
                        numeric_val = None

                # Terminology normalization
                term_res = self.mapper.map_analyte(analyte_raw=desc_val, provided_loinc=code_val)

                rec_id = f"synthea:{patient_val}:row_{idx}"
                record = ResearchEvidenceRecord(
                    id=rec_id,
                    dataset="synthea",
                    source_patient_id=patient_val,
                    source_encounter_id=encounter_val,
                    source_record_id=f"row_{idx}",
                    observation_date=date_val,
                    analyte_raw=desc_val,
                    analyte_canonical=term_res.analyte_canonical,
                    concept_id=term_res.concept_id,
                    loinc_code=term_res.loinc_code,
                    value_numeric=numeric_val,
                    value_text=value_str if value_str else None,
                    unit=units_val or term_res.canonical_unit,
                    reference_low=None,
                    reference_high=None,
                    mapping_status=term_res.mapping_status,
                    source_provenance=f"synthea:observations.csv:row_{idx}",
                    flag=None,
                )
                records.append(record)

                if limit is not None and len(records) >= limit:
                    break

        return records
