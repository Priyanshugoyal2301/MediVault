"""
scripts/ingest_clinical_cohort.py

Unified CLI ingestion script for longitudinal clinical research cohorts (CP-03).
Ingests Synthea or MIMIC-IV Demo datasets, performs deterministic terminology mapping,
generates patient-disjoint splits, builds Information Retrieval evaluation benchmarks,
and outputs data quality audit reports.

Usage:
    python scripts/ingest_clinical_cohort.py --dataset synthea --input-dir datasets/clinical/synthea/sample --output-dir datasets/clinical/processed/synthea
    python scripts/ingest_clinical_cohort.py --dataset mimic_demo --input-dir datasets/clinical/mimic_demo/sample --output-dir datasets/clinical/processed/mimic_demo
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure root and scripts are in sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bootstrap_imports  # noqa: F401,E402

from packages.research_data.evaluation_builder import EvaluationBenchmarkBuilder
from packages.research_data.parsers.mimic_parser import MimicDemoParser
from packages.research_data.parsers.synthea_parser import SyntheaParser
from packages.research_data.quality_audit import DataQualityAuditor
from packages.research_data.splits import (
    partition_patients_disjoint,
    split_records_by_patient,
    verify_patient_disjointness,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_clinical_cohort")


def ingest_cohort(
    dataset: str,
    input_dir: Path,
    output_dir: Path,
    split_ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    seed: int = 42,
    target_queries: int = 86,
    split_policy: str = "exact",
) -> dict[str, int | float | str]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting ingestion for dataset='%s' from %s", dataset, input_dir)

    # 1. Parsing & Canonical Transformation
    if dataset == "synthea":
        obs_file = input_dir / "observations.csv"
        if not obs_file.exists():
            raise FileNotFoundError(f"Missing observations.csv in {input_dir}")
        parser = SyntheaParser()
        records = parser.parse_observations_file(obs_file)

    elif dataset == "mimic_demo":
        events_file = input_dir / "labevents.csv"
        dict_file = input_dir / "d_labitems.csv"
        if not events_file.exists():
            raise FileNotFoundError(f"Missing labevents.csv in {input_dir}")
        if not dict_file.exists():
            raise FileNotFoundError(f"Missing d_labitems.csv in {input_dir}")
        parser = MimicDemoParser()
        records = parser.parse_labevents_file(events_file, dict_file)

    else:
        raise ValueError(f"Unsupported dataset: {dataset}. Supported: 'synthea', 'mimic_demo'")

    logger.info("Transformed %d records into canonical ResearchEvidenceRecord format", len(records))

    # 2. Patient Partitioning (Patient-Disjoint)
    patient_ids = [r.source_patient_id for r in records]
    patient_splits = partition_patients_disjoint(
        patient_ids, ratios=split_ratios, seed=seed, policy=split_policy
    )
    verify_patient_disjointness(patient_splits)

    record_splits = split_records_by_patient(records, patient_splits)

    # 3. Benchmark Evaluation Queries
    eval_builder = EvaluationBenchmarkBuilder()
    queries = eval_builder.generate_benchmark(records, patient_splits, target_count=target_queries)
    logger.info("Generated %d Information Retrieval benchmark queries across 7 intents", len(queries))

    # 4. Data Quality Audit
    auditor = DataQualityAuditor()
    audit_report = auditor.audit(records, dataset_name=dataset)

    # 5. Write Processed Artifacts
    # All records JSONL
    records_file = output_dir / "records.jsonl"
    with open(records_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict()) + "\n")

    # Patient splits metadata
    splits_meta_file = output_dir / "splits.json"
    with open(splits_meta_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "ratios": {"dev": split_ratios[0], "val": split_ratios[1], "test": split_ratios[2]},
                "patient_counts": {k: len(v) for k, v in patient_splits.items()},
                "record_counts": {k: len(v) for k, v in record_splits.items()},
                "patients": patient_splits,
            },
            f,
            indent=2,
        )

    # Individual split JSONL files
    split_dir = output_dir / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    for s_name in ("dev", "val", "test"):
        with open(split_dir / f"{s_name}_records.jsonl", "w", encoding="utf-8") as f:
            for r in record_splits.get(s_name, []):
                f.write(json.dumps(r.to_dict()) + "\n")

    # Evaluation benchmark queries JSONL
    eval_dir = output_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    queries_file = eval_dir / "queries.jsonl"
    with open(queries_file, "w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q.to_dict()) + "\n")

    # Quality audit JSON
    audit_file = output_dir / "quality_audit.json"
    with open(audit_file, "w", encoding="utf-8") as f:
        f.write(audit_report.to_json(indent=2))

    summary = {
        "dataset": dataset,
        "total_records": len(records),
        "source_patients": audit_report.total_source_patients,
        "longitudinal_patients": audit_report.longitudinal_patients,
        "normalization_coverage_pct": audit_report.normalization_coverage_pct,
        "loinc_mapping_coverage_pct": audit_report.loinc_mapping_coverage_pct,
        "date_range": f"{audit_report.date_range_start} to {audit_report.date_range_end}",
        "dev_patients": len(patient_splits["dev"]),
        "val_patients": len(patient_splits["val"]),
        "test_patients": len(patient_splits["test"]),
        "eval_queries": len(queries),
        "output_directory": str(output_dir),
    }

    print("\n" + "=" * 60)
    print(" CLINICAL COHORT INGESTION REPORT (CP-03)")
    print("=" * 60)
    for k, v in summary.items():
        print(f" {k:<30}: {v}")
    print("=" * 60 + "\n")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest clinical cohort for longitudinal research")
    parser.add_argument("--dataset", choices=["synthea", "mimic_demo"], required=True, help="Cohort dataset source")
    parser.add_argument("--input-dir", type=Path, required=True, help="Input directory containing raw CSVs")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for canonical records and benchmark")
    parser.add_argument("--split-ratios", type=str, default="0.6,0.2,0.2", help="Comma-separated dev,val,test ratios")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--target-queries", type=int, default=86, help="Target number of evaluation benchmark queries")
    parser.add_argument("--split-policy", choices=["exact", "hash"], default="exact", help="Patient split policy")

    args = parser.parse_args()
    ratios = tuple(float(x.strip()) for x in args.split_ratios.split(","))  # type: ignore[assignment]
    if len(ratios) != 3:
        raise ValueError("--split-ratios must contain exactly 3 numbers (dev,val,test)")

    ingest_cohort(
        dataset=args.dataset,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        split_ratios=ratios,  # type: ignore[arg-type]
        seed=args.seed,
        target_queries=args.target_queries,
        split_policy=args.split_policy,
    )


if __name__ == "__main__":
    main()
