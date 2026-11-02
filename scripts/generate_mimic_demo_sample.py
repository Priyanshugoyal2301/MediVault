"""
scripts/generate_mimic_demo_sample.py

Generates a MIMIC-compatible synthetic fixture for CP-03 (hosp/labevents.csv, hosp/d_labitems.csv, hosp/patients.csv).
Provenance Notice: Locally generated synthetic test fixture designed to emulate MIMIC-IV schema
(does NOT contain records from the official PhysioNet MIMIC-IV or MIMIC-IV Demo distribution).
"""

from __future__ import annotations

import csv
from pathlib import Path


def generate_mimic_demo_sample(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    d_labitems_file = output_dir / "d_labitems.csv"
    labevents_file = output_dir / "labevents.csv"
    patients_file = output_dir / "patients.csv"

    # d_labitems items
    items = [
        {"itemid": "50861", "label": "Alanine Aminotransferase (ALT)", "fluid": "Blood", "category": "Chemistry", "loinc_code": "1742-6"},
        {"itemid": "50878", "label": "Aspartate Aminotransferase (AST)", "fluid": "Blood", "category": "Chemistry", "loinc_code": "1920-8"},
        {"itemid": "50904", "label": "Cholesterol, HDL", "fluid": "Blood", "category": "Chemistry", "loinc_code": "2085-9"},
        {"itemid": "50905", "label": "Cholesterol, LDL, Calculated", "fluid": "Blood", "category": "Chemistry", "loinc_code": "2089-1"},
        {"itemid": "50907", "label": "Cholesterol, Total", "fluid": "Blood", "category": "Chemistry", "loinc_code": "2093-3"},
        {"itemid": "50912", "label": "Creatinine", "fluid": "Blood", "category": "Chemistry", "loinc_code": "2160-0"},
        {"itemid": "50931", "label": "Glucose", "fluid": "Blood", "category": "Chemistry", "loinc_code": "2345-7"},
        {"itemid": "51006", "label": "Urea Nitrogen", "fluid": "Blood", "category": "Chemistry", "loinc_code": "3094-0"},
        {"itemid": "51222", "label": "Hemoglobin", "fluid": "Blood", "category": "Hematology", "loinc_code": "718-7"},
        {"itemid": "51265", "label": "Platelet Count", "fluid": "Blood", "category": "Hematology", "loinc_code": "777-3"},
        {"itemid": "51301", "label": "White Blood Cells", "fluid": "Blood", "category": "Hematology", "loinc_code": "6690-2"},
    ]

    # Patients
    patients = [
        {"subject_id": "10000032", "gender": "F", "anchor_age": "52", "anchor_year": "2180"},
        {"subject_id": "10000084", "gender": "M", "anchor_age": "72", "anchor_year": "2160"},
        {"subject_id": "10000115", "gender": "M", "anchor_age": "24", "anchor_year": "2154"},
    ]

    # Labevents with longitudinal timestamps
    events = [
        # Patient 10000032
        {"labevent_id": "1001", "subject_id": "10000032", "hadm_id": "22595853", "itemid": "50905", "charttime": "2180-03-23 11:51:00", "valuenum": "115", "value": "115", "valueuom": "mg/dL", "ref_range_lower": "0", "ref_range_upper": "100", "flag": "abnormal"},
        {"labevent_id": "1002", "subject_id": "10000032", "hadm_id": "22595853", "itemid": "50907", "charttime": "2180-03-23 11:51:00", "valuenum": "190", "value": "190", "valueuom": "mg/dL", "ref_range_lower": "0", "ref_range_upper": "200", "flag": ""},
        {"labevent_id": "1003", "subject_id": "10000032", "hadm_id": "22841357", "itemid": "50905", "charttime": "2180-05-06 15:30:00", "valuenum": "138", "value": "138", "valueuom": "mg/dL", "ref_range_lower": "0", "ref_range_upper": "100", "flag": "abnormal"},
        {"labevent_id": "1004", "subject_id": "10000032", "hadm_id": "22841357", "itemid": "50907", "charttime": "2180-05-06 15:30:00", "valuenum": "215", "value": "215", "valueuom": "mg/dL", "ref_range_lower": "0", "ref_range_upper": "200", "flag": "abnormal"},
        {"labevent_id": "1005", "subject_id": "10000032", "hadm_id": "22841357", "itemid": "51222", "charttime": "2180-05-06 15:30:00", "valuenum": "13.4", "value": "13.4", "valueuom": "g/dL", "ref_range_lower": "12.0", "ref_range_upper": "16.0", "flag": ""},
        # Patient 10000084
        {"labevent_id": "2001", "subject_id": "10000084", "hadm_id": "23052089", "itemid": "50912", "charttime": "2160-12-28 07:00:00", "valuenum": "1.2", "value": "1.2", "valueuom": "mg/dL", "ref_range_lower": "0.6", "ref_range_upper": "1.3", "flag": ""},
        {"labevent_id": "2002", "subject_id": "10000084", "hadm_id": "23052089", "itemid": "50912", "charttime": "2160-12-29 08:30:00", "valuenum": "1.5", "value": "1.5", "valueuom": "mg/dL", "ref_range_lower": "0.6", "ref_range_upper": "1.3", "flag": "abnormal"},
        {"labevent_id": "2003", "subject_id": "10000084", "hadm_id": "23052089", "itemid": "51222", "charttime": "2160-12-28 07:00:00", "valuenum": "11.1", "value": "11.1", "valueuom": "g/dL", "ref_range_lower": "13.5", "ref_range_upper": "17.5", "flag": "abnormal"},
    ]

    with open(d_labitems_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["itemid", "label", "fluid", "category", "loinc_code"])
        writer.writeheader()
        writer.writerows(items)

    with open(patients_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject_id", "gender", "anchor_age", "anchor_year"])
        writer.writeheader()
        writer.writerows(patients)

    with open(labevents_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["labevent_id", "subject_id", "hadm_id", "itemid", "charttime", "valuenum", "value", "valueuom", "ref_range_lower", "ref_range_upper", "flag"])
        writer.writeheader()
        writer.writerows(events)

    print(f"Generated MIMIC Demo sample: {len(patients)} patients, {len(events)} labevents at {output_dir}")


if __name__ == "__main__":
    out = Path("datasets/clinical/mimic_demo/sample")
    generate_mimic_demo_sample(out)
