# Datasets — `data/datasets`

## Purpose

Synthetic evaluation scripts and fixtures used by Plan B/C anomaly experiments and related tooling.

Prefer the curated fixtures under [`datasets/`](../../datasets/) for ML phase train/eval JSONL files and licensing notes.

## Scripts

Evaluation helpers live alongside this folder (for example `evaluate_rag.py`, `generate_synthetic_anomaly_data.py`). Run from the **repository root**. Synthetic anomaly eval accepts `--no-devlog` and skips writing if `docs/DEV_LOG.md` is absent.

## Requirements

Datasets used for claims should support reporting precision, recall, F1, and false-alert rate where applicable, and must state whether data is real or synthetic (see `docs/KNOWN_LIMITATIONS.md` and `docs/PRESENTATION_CLAIMS.md`).
