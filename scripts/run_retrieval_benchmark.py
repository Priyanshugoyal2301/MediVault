"""
scripts/run_retrieval_benchmark.py

Convenience script to execute the MediVault CP-06 Evidence Retrieval Benchmark.
Usage:
    python scripts/run_retrieval_benchmark.py [--splits dev val test]
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure root is on sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import scripts.bootstrap_imports  # noqa: F401
from packages.research_data.evaluation.runner import run_benchmark_suite


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run MediVault CP-06 Evidence Retrieval Benchmark")
    parser.add_argument("--splits", nargs="+", default=["dev", "val", "test"], choices=["dev", "val", "test"])
    parser.add_argument("--mode", default="both", choices=["oracle", "end_to_end", "both"], help="Evaluation mode (oracle, end_to_end, or both)")
    args = parser.parse_args()

    mode_list = ["oracle", "end_to_end"] if args.mode == "both" else [args.mode]
    print(f"Starting MediVault CP-06 Retrieval Benchmark on splits: {args.splits}, modes: {mode_list}")
    run_benchmark_suite(splits=args.splits, modes=mode_list)
    print("Benchmark completed successfully.")


if __name__ == "__main__":
    main()`n