"""
tests/unit/research-data/test_splits_and_leakage.py

Verifies patient-level split integrity (CP-03):
- patient-disjointness (dev ∩ val = ∅, dev ∩ test = ∅, val ∩ test = ∅)
- deterministic partitioning
- zero cross-split leakage
"""

from __future__ import annotations

import pytest

from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.splits import (
    partition_patients_disjoint,
    split_records_by_patient,
    verify_patient_disjointness,
)


class TestPatientSplits:
    def test_partition_is_strictly_disjoint(self):
        patients = [f"patient_{i:03d}" for i in range(100)]
        splits = partition_patients_disjoint(patients, ratios=(0.6, 0.2, 0.2), seed=42)

        dev_set = set(splits["dev"])
        val_set = set(splits["val"])
        test_set = set(splits["test"])

        assert len(dev_set.intersection(val_set)) == 0, "No overlap between dev and val"
        assert len(dev_set.intersection(test_set)) == 0, "No overlap between dev and test"
        assert len(val_set.intersection(test_set)) == 0, "No overlap between val and test"

        # All 100 accounted for
        assert len(dev_set) + len(val_set) + len(test_set) == 100

    def test_verify_patient_disjointness_raises_on_overlap(self):
        corrupted_splits = {
            "dev": ["P1", "P2", "P3"],
            "val": ["P3", "P4"],  # P3 leaked
            "test": ["P5"],
        }
        with pytest.raises(ValueError, match="Patient leakage detected"):
            verify_patient_disjointness(corrupted_splits)

    def test_split_records_by_patient(self):
        recs = [
            ResearchEvidenceRecord(
                id=f"rec_{p}",
                dataset="synthea",
                source_patient_id=p,
                source_encounter_id="E",
                source_record_id="1",
                observation_date="2023-01-01",
                analyte_raw="Glucose",
            )
            for p in ["P1", "P2", "P3", "P4", "P5"]
        ]
        patient_splits = {
            "dev": ["P1", "P2", "P3"],
            "val": ["P4"],
            "test": ["P5"],
        }

        split_recs = split_records_by_patient(recs, patient_splits)
        assert len(split_recs["dev"]) == 3
        assert len(split_recs["val"]) == 1
        assert len(split_recs["test"]) == 1
        assert {r.source_patient_id for r in split_recs["dev"]} == {"P1", "P2", "P3"}
        assert {r.source_patient_id for r in split_recs["test"]} == {"P5"}

    def test_exact_cardinality_partitioning_policy(self):
        """Verifies exact 36/12/12 cardinality on 60 patients with seed=42 (CP-05.5)."""
        patients = [f"patient_{i:03d}" for i in range(60)]
        splits = partition_patients_disjoint(patients, ratios=(0.6, 0.2, 0.2), seed=42, policy="exact")

        assert len(splits["dev"]) == 36, f"Expected 36 dev patients, got {len(splits['dev'])}"
        assert len(splits["val"]) == 12, f"Expected 12 val patients, got {len(splits['val'])}"
        assert len(splits["test"]) == 12, f"Expected 12 test patients, got {len(splits['test'])}"
        assert len(splits["dev"]) + len(splits["val"]) + len(splits["test"]) == 60

        dev_set = set(splits["dev"])
        val_set = set(splits["val"])
        test_set = set(splits["test"])
        assert len(dev_set & val_set) == 0, "Dev and Val must be disjoint"
        assert len(dev_set & test_set) == 0, "Dev and Test must be disjoint"
        assert len(val_set & test_set) == 0, "Val and Test must be disjoint"

    def test_synthea_processed_artifacts_split_and_evidence_integrity(self):
        """
        End-to-end verification of processed Synthea cohort (CP-05.5):
        - Dev patients ∩ Val patients = ∅
        - Dev patients ∩ Test patients = ∅
        - Val patients ∩ Test patients = ∅
        - Dev query patients ⊆ Dev patients
        - Val query patients ⊆ Val patients
        - Test query patients ⊆ Test patients
        - Dev query evidence ∩ Val patient evidence = ∅
        - Dev query evidence ∩ Test patient evidence = ∅
        - Val query evidence ∩ Test patient evidence = ∅
        """
        import json
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        splits_file = repo_root / "datasets" / "clinical" / "processed" / "synthea" / "splits.json"
        queries_file = repo_root / "datasets" / "clinical" / "processed" / "synthea" / "evaluation" / "queries.jsonl"
        records_file = repo_root / "datasets" / "clinical" / "processed" / "synthea" / "records.jsonl"

        if not (splits_file.exists() and queries_file.exists() and records_file.exists()):
            pytest.skip("Processed Synthea artifacts not found; skipping cohort verification.")

        with open(splits_file) as f:
            splits_data = json.load(f)

        dev_p = set(splits_data["patients"]["dev"])
        val_p = set(splits_data["patients"]["val"])
        test_p = set(splits_data["patients"]["test"])

        # 1. Exact cardinality
        assert len(dev_p) == 36, f"Expected 36 dev patients, got {len(dev_p)}"
        assert len(val_p) == 12, f"Expected 12 val patients, got {len(val_p)}"
        assert len(test_p) == 12, f"Expected 12 test patients, got {len(test_p)}"

        # 2. Mutually disjoint patient sets
        assert len(dev_p & val_p) == 0, "Dev and Val patients must be disjoint"
        assert len(dev_p & test_p) == 0, "Dev and Test patients must be disjoint"
        assert len(val_p & test_p) == 0, "Val and Test patients must be disjoint"

        # 3. Patient to evidence mapping
        records_by_id = {}
        patient_evidence: dict[str, set[str]] = {"dev": set(), "val": set(), "test": set()}
        with open(records_file) as f:
            for line in f:
                rec = json.loads(line)
                records_by_id[rec["id"]] = rec
                pid = rec["source_patient_id"]
                if pid in dev_p:
                    patient_evidence["dev"].add(rec["id"])
                elif pid in val_p:
                    patient_evidence["val"].add(rec["id"])
                elif pid in test_p:
                    patient_evidence["test"].add(rec["id"])

        # 4. Query split and evidence leakage checks
        queries = []
        with open(queries_file) as f:
            for line in f:
                queries.append(json.loads(line))

        dev_queries = [q for q in queries if q["split"] == "dev"]
        val_queries = [q for q in queries if q["split"] == "val"]
        test_queries = [q for q in queries if q["split"] == "test"]

        # All splits have queries
        assert len(dev_queries) > 0, "Dev split must contain queries"
        assert len(val_queries) > 0, "Val split must contain queries"
        assert len(test_queries) > 0, "Test split must contain queries"

        # Query patients subset of split patients
        assert {q["patient_id"] for q in dev_queries}.issubset(dev_p)
        assert {q["patient_id"] for q in val_queries}.issubset(val_p)
        assert {q["patient_id"] for q in test_queries}.issubset(test_p)

        # Collect query evidence by split
        dev_query_evidence = {eid for q in dev_queries for eid in q["relevant_evidence_ids"]}
        val_query_evidence = {eid for q in val_queries for eid in q["relevant_evidence_ids"]}
        test_query_evidence = {eid for q in test_queries for eid in q["relevant_evidence_ids"]}

        # Cross-split evidence disjointness
        assert len(dev_query_evidence & patient_evidence["val"]) == 0, "Dev query references Val evidence"
        assert len(dev_query_evidence & patient_evidence["test"]) == 0, "Dev query references Test evidence"
        assert len(val_query_evidence & patient_evidence["test"]) == 0, "Val query references Test evidence"
        assert len(val_query_evidence & patient_evidence["dev"]) == 0, "Val query references Dev evidence"
        assert len(test_query_evidence & patient_evidence["dev"]) == 0, "Test query references Dev evidence"
        assert len(test_query_evidence & patient_evidence["val"]) == 0, "Test query references Val evidence"

    def test_regression_no_patient_monopoly_and_broad_coverage(self):
        """
        Regression test against CP-03 bug where 75 queries came from only 2 patients (55 test, 20 dev, 0 val).
        Verifies:
        - At least 30 unique patients contribute queries across the benchmark
        - Val split has at least 15 queries and >= 8 unique patients
        - No single patient contributes more than 10% of total queries
        """
        import json
        from collections import Counter
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        queries_file = repo_root / "datasets" / "clinical" / "processed" / "synthea" / "evaluation" / "queries.jsonl"
        if not queries_file.exists():
            pytest.skip("Queries file not found")

        with open(queries_file) as f:
            queries = [json.loads(line) for line in f]

        total_queries = len(queries)
        assert total_queries >= 75, f"Expected at least 75 queries, got {total_queries}"

        unique_patients = {q["patient_id"] for q in queries}
        assert len(unique_patients) >= 30, (
            f"Regression: queries must span broad patient cohort (>= 30), got only {len(unique_patients)}"
        )

        val_queries = [q for q in queries if q["split"] == "val"]
        assert len(val_queries) >= 15, f"Regression: validation queries missing or starved (got {len(val_queries)})"
        val_patients = {q["patient_id"] for q in val_queries}
        assert len(val_patients) >= 8, f"Regression: validation must represent >= 8 patients (got {len(val_patients)})"

        patient_counts = Counter(q["patient_id"] for q in queries)
        max_patient, max_count = patient_counts.most_common(1)[0]
        max_pct = (max_count / total_queries) * 100.0
        assert max_pct < 10.0, (
            f"Regression: patient monopoly detected! Patient {max_patient} has {max_count}/{total_queries} queries ({max_pct:.1f}%)"
        )
