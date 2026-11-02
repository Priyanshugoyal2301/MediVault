"""
tests/unit/research-data/test_ingest_cli.py

Verifies end-to-end clinical cohort ingestion pipeline (CP-03):
- deterministic execution
- file artifact generation (records.jsonl, splits.json, queries.jsonl, quality_audit.json)
- reproducible metrics verification
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from scripts.ingest_clinical_cohort import ingest_cohort


class TestIngestClinicalCohortCLI:
    def test_synthea_sample_ingestion_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "processed_synthea"
            in_dir = Path("datasets/clinical/synthea/sample")

            summary = ingest_cohort(
                dataset="synthea",
                input_dir=in_dir,
                output_dir=out_dir,
                split_ratios=(0.6, 0.2, 0.2),
                seed=42,
                target_queries=50,
            )

            assert summary["dataset"] == "synthea"
            assert summary["total_records"] == 2790
            assert summary["source_patients"] == 60
            assert summary["longitudinal_patients"] == 60
            assert summary["normalization_coverage_pct"] == 100.0
            assert summary["dev_patients"] == 36
            assert summary["val_patients"] == 12
            assert summary["test_patients"] == 12

            # Verify files exist on disk
            assert (out_dir / "records.jsonl").exists()
            assert (out_dir / "splits.json").exists()
            assert (out_dir / "splits" / "dev_records.jsonl").exists()
            assert (out_dir / "splits" / "val_records.jsonl").exists()
            assert (out_dir / "splits" / "test_records.jsonl").exists()
            assert (out_dir / "evaluation" / "queries.jsonl").exists()
            assert (out_dir / "quality_audit.json").exists()

            # Verify quality audit JSON
            audit_data = json.loads((out_dir / "quality_audit.json").read_text(encoding="utf-8"))
            assert audit_data["total_observations"] == 2790
            assert audit_data["missing_dates_count"] == 0

    def test_mimic_demo_sample_ingestion_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "processed_mimic"
            in_dir = Path("datasets/clinical/mimic_demo/sample")

            summary = ingest_cohort(
                dataset="mimic_demo",
                input_dir=in_dir,
                output_dir=out_dir,
                split_ratios=(0.6, 0.2, 0.2),
                seed=42,
                target_queries=20,
            )

            assert summary["dataset"] == "mimic_demo"
            assert summary["total_records"] == 8
            assert (out_dir / "records.jsonl").exists()
            assert (out_dir / "quality_audit.json").exists()
