# datasets/clinical/ — Clinical Research Data Provenance

This directory stores reproducible clinical research datasets and development fixtures for longitudinal Information Retrieval experiments (CP-03).

## Provenance Disclosures

1. **Synthea-Compatible Development Cohort (`synthea/sample/`):**
   - **Provenance Category:** Locally generated synthetic cohort conforming to the standard Synthea CSV schema (`DATE, PATIENT, ENCOUNTER, CODE, DESCRIPTION, VALUE, UNITS, TYPE`).
   - **Generation Source:** Generated deterministically via `scripts/generate_synthea_sample.py` (seed=42).
   - **Disclosure:** This data was **not** produced by the official Synthea Java generation engine, nor downloaded from an external Synthea repository. It is a controlled, synthetic longitudinal test cohort designed for pipeline validation.
   - **Scale:** 60 synthetic patients, 330 encounters, 2,790 observations across 2021–2024.

2. **MIMIC-Compatible Synthetic Fixture (`mimic_demo/sample/`):**
   - **Provenance Category:** Locally generated synthetic test fixture conforming to the MIMIC-IV table structure (`hosp/labevents.csv`, `hosp/d_labitems.csv`, `hosp/patients.csv`).
   - **Generation Source:** Generated deterministically via `scripts/generate_mimic_demo_sample.py`.
   - **Disclosure:** This data does **not** contain records from the official PhysioNet MIMIC-IV or MIMIC-IV Demo database. It exists purely as an offline schema validation fixture to verify that MediVault's MIMIC parser correctly handles MIMIC-style headers, units, and item dictionaries without requiring credentialed PhysioNet access.

3. **Information Retrieval Benchmark (`processed/synthea/evaluation/queries.jsonl`):**
   - **Benchmark Category:** Synthetic/generated functional IR benchmark.
   - **Methodology:** Automatically constructed using rule-based temporal heuristics over the longitudinal patient series across 7 clinical intents (`current_value`, `previous_value`, `last_n_observations`, `historical_interval`, `longitudinal_trend`, `date_comparison`, `first_abnormal`).
   - **Disclosure:** These 75 queries are **not** human-annotated clinical questions authored by medical experts. They serve as an automated, functional ground-truth benchmark to verify that the retrieval and temporal ranking pipeline can retrieve multi-point historical evidence.

4. **LOINC Mapping Scope:**
   - **Scope:** 100% LOINC mapping coverage applies strictly to the 11 laboratory analytes present in this controlled development cohort (LDL, HDL, Total Cholesterol, Triglycerides, Haemoglobin, WBC, Platelets, HbA1c, Glucose, Creatinine, TSH). It does **not** represent universal coverage across the broader LOINC terminology space.
