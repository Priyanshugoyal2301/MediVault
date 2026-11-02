"""
packages/research-data/parsers/mimic_parser.py

MIMIC-IV Demo CSV parser for clinical research cohort ingestion (CP-03).
Maps MIMIC hosp/labevents.csv + hosp/d_labitems.csv into canonical ResearchEvidenceRecord format.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.terminology import ClinicalTerminologyMapper


logger = logging.getLogger(__name__)


class MimicDemoParser:
    """
    Parses MIMIC-IV Clinical Database Demo labevents.csv and d_labitems.csv
    into canonical ResearchEvidenceRecord models.
    """

    def __init__(self, mapper: ClinicalTerminologyMapper | None = None) -> None:
        self.mapper = mapper or ClinicalTerminologyMapper()

    def load_d_labitems(self, d_labitems_path: Path | str) -> dict[str, dict[str, Any]]:
        path = Path(d_labitems_path)
        if not path.exists():
            raise FileNotFoundError(f"MIMIC d_labitems.csv not found: {path}")

        items: dict[str, dict[str, Any]] = {}
        with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = str(row.get("itemid", "")).strip()
                if item_id:
                    items[item_id] = {
                        "label": str(row.get("label", "")).strip(),
                        "fluid": str(row.get("fluid", "")).strip(),
                        "category": str(row.get("category", "")).strip(),
                        "loinc_code": str(row.get("loinc_code", "")).strip() or None,
                    }
        return items

    def parse_labevents_file(
        self,
        labevents_path: Path | str,
        d_labitems_path: Path | str,
        limit: int | None = None,
    ) -> list[ResearchEvidenceRecord]:
        items_dict = self.load_d_labitems(d_labitems_path)
        path = Path(labevents_path)
        if not path.exists():
            raise FileNotFoundError(f"MIMIC labevents.csv not found: {path}")

        records: list[ResearchEvidenceRecord] = []
        with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                labevent_id = str(row.get("labevent_id", "")).strip()
                subject_id = str(row.get("subject_id", "")).strip()
                hadm_id = str(row.get("hadm_id", "")).strip() or None
                itemid = str(row.get("itemid", "")).strip()
                charttime = str(row.get("charttime", "")).strip()
                value_text = str(row.get("value", "")).strip() or None
                valuenum_str = str(row.get("valuenum", "")).strip()
                valueuom = str(row.get("valueuom", "")).strip() or None
                ref_low_str = str(row.get("ref_range_lower", "")).strip()
                ref_high_str = str(row.get("ref_range_upper", "")).strip()
                flag = str(row.get("flag", "")).strip() or None

                numeric_val: float | None = None
                if valuenum_str:
                    try:
                        numeric_val = float(valuenum_str)
                    except ValueError:
                        numeric_val = None
                elif value_text:
                    try:
                        numeric_val = float(value_text)
                    except ValueError:
                        numeric_val = None

                ref_low: float | None = None
                if ref_low_str:
                    try:
                        ref_low = float(ref_low_str)
                    except ValueError:
                        ref_low = None

                ref_high: float | None = None
                if ref_high_str:
                    try:
                        ref_high = float(ref_high_str)
                    except ValueError:
                        ref_high = None

                item_meta = items_dict.get(itemid, {})
                analyte_raw = item_meta.get("label") or f"ITEM_{itemid}"
                loinc_code = item_meta.get("loinc_code")

                term_res = self.mapper.map_analyte(analyte_raw=analyte_raw, provided_loinc=loinc_code)

                rec_id = f"mimic_demo:{subject_id}:{labevent_id}"
                rec = ResearchEvidenceRecord(
                    id=rec_id,
                    dataset="mimic_demo",
                    source_patient_id=subject_id,
                    source_encounter_id=hadm_id,
                    source_record_id=labevent_id,
                    observation_date=charttime,
                    analyte_raw=analyte_raw,
                    analyte_canonical=term_res.analyte_canonical,
                    concept_id=term_res.concept_id,
                    loinc_code=term_res.loinc_code,
                    value_numeric=numeric_val,
                    value_text=value_text,
                    unit=valueuom or term_res.canonical_unit,
                    reference_low=ref_low,
                    reference_high=ref_high,
                    mapping_status=term_res.mapping_status,
                    source_provenance=f"mimic_demo:labevents.csv:labevent_id_{labevent_id}",
                    flag=flag,
                )
                records.append(rec)

                if limit is not None and len(records) >= limit:
                    break

        return records
