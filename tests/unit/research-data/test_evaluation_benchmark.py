"""
tests/unit/research-data/test_evaluation_benchmark.py

Verifies Information Retrieval Evaluation Benchmark builder (CP-03):
- coverage across 7 clinical temporal intents
- ground truth relevant evidence ID resolution
- query split alignment with patient splits (no split leakage)
"""

from __future__ import annotations

import pytest

from packages.research_data.evaluation_builder import EvaluationBenchmarkBuilder
from packages.research_data.models import ResearchEvidenceRecord


class TestEvaluationBenchmarkBuilder:
    def test_benchmark_generation_and_intent_coverage(self):
        # Create a longitudinal patient with 4 observations
        records = [
            ResearchEvidenceRecord(
                id=f"rec_p1_{i}",
                dataset="synthea",
                source_patient_id="P1",
                source_encounter_id=f"E{i}",
                source_record_id=str(i),
                observation_date=f"202{i}-04-01T08:00:00Z",
                analyte_raw="Low Density Lipoprotein Cholesterol",
                analyte_canonical="LDL Cholesterol",
                loinc_code="2089-1",
                value_numeric=110.0 + i * 15.0,  # 125, 140, 155, 170
                unit="mg/dL",
                mapping_status="exact_loinc",
            )
            for i in range(1, 5)
        ]

        patient_splits = {"dev": ["P1"], "val": [], "test": []}

        builder = EvaluationBenchmarkBuilder()
        queries = builder.generate_benchmark(records, patient_splits, target_count=10)

        assert len(queries) >= 5
        intents_generated = {q.intent for q in queries}
        assert "current_value" in intents_generated
        assert "previous_value" in intents_generated
        assert "longitudinal_trend" in intents_generated

        # Check current value query
        curr_q = next(q for q in queries if q.intent == "current_value")
        assert curr_q.relevant_evidence_ids == ["rec_p1_4"]
        assert curr_q.split == "dev"

        # Check previous value query
        prev_q = next(q for q in queries if q.intent == "previous_value")
        assert prev_q.relevant_evidence_ids == ["rec_p1_3"]

        # Check trend query (must include all 4 historical points)
        trend_q = next(q for q in queries if q.intent == "longitudinal_trend")
        assert trend_q.relevant_evidence_ids == ["rec_p1_1", "rec_p1_2", "rec_p1_3", "rec_p1_4"]

    def test_query_split_matches_patient_split(self):
        records = [
            ResearchEvidenceRecord(
                id=f"rec_p2_{i}",
                dataset="synthea",
                source_patient_id="P2",
                source_encounter_id=f"E{i}",
                source_record_id=str(i),
                observation_date=f"202{i}-01-01",
                analyte_raw="HbA1c",
                analyte_canonical="HbA1c",
                loinc_code="4548-4",
                value_numeric=5.5 + i * 0.2,
                unit="%",
                mapping_status="exact_loinc",
            )
            for i in range(1, 4)
        ]
        patient_splits = {"dev": [], "val": [], "test": ["P2"]}

        builder = EvaluationBenchmarkBuilder()
        queries = builder.generate_benchmark(records, patient_splits)

        for q in queries:
            assert q.patient_id == "P2"
            assert q.split == "test", f"Query split {q.split} must match patient split 'test'"

    def test_first_abnormal_clinical_thresholds(self):
        """Verifies clinical abnormality recognition across analytes without fabricated flags."""
        builder = EvaluationBenchmarkBuilder()

        # Normal and abnormal records
        normal_hba1c = ResearchEvidenceRecord(
            id="r_norm",
            dataset="synthea",
            source_patient_id="P_abn",
            source_encounter_id="E1",
            source_record_id="1",
            observation_date="2022-01-01",
            analyte_raw="HbA1c",
            analyte_canonical="HbA1c",
            value_numeric=5.4,
        )
        abnormal_hba1c = ResearchEvidenceRecord(
            id="r_abn",
            dataset="synthea",
            source_patient_id="P_abn",
            source_encounter_id="E2",
            source_record_id="2",
            observation_date="2023-01-01",
            analyte_raw="HbA1c",
            analyte_canonical="HbA1c",
            value_numeric=7.2,
        )

        assert not builder.is_clinically_abnormal(normal_hba1c)
        assert builder.is_clinically_abnormal(abnormal_hba1c)

        records = [normal_hba1c, abnormal_hba1c]
        patient_splits = {"dev": ["P_abn"], "val": [], "test": []}
        queries = builder.generate_benchmark(records, patient_splits, target_count=7)

        abn_queries = [q for q in queries if q.intent == "first_abnormal"]
        assert len(abn_queries) == 1
        assert abn_queries[0].relevant_evidence_ids == ["r_abn"]
        assert "first flagged as elevated or abnormal" in abn_queries[0].query

    def test_no_label_leakage_in_query_text(self):
        """Verifies that query text expresses natural clinical needs without leaking internal IDs."""
        import json
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        queries_file = repo_root / "datasets" / "clinical" / "processed" / "synthea" / "evaluation" / "queries.jsonl"
        if not queries_file.exists():
            pytest.skip("Queries file not found")

        with open(queries_file) as f:
            queries = [json.loads(line) for line in f]

        forbidden_tokens = ["synthea:", "mimic:", "row_", "rec_", "00000000-0000-", "LOINC:"]
        for q in queries:
            text = q["query"]
            for token in forbidden_tokens:
                assert token.lower() not in text.lower(), (
                    f"Label leakage detected in query '{text}': contains internal token '{token}'"
                )
            for eid in q["relevant_evidence_ids"]:
                assert eid not in text, f"Label leakage: query text contains evidence ID '{eid}'"
