# Datasets — `data/datasets`

## Purpose

Training and evaluation data for the anomaly detection model (Feature 2).

## Populated at

Feature 2 build — **dataset choice must be logged in `docs/DEV_LOG.md`** with full reasoning before any data is placed here. Options under consideration: MIMIC-IV subset vs. synthetic. See open question in DEV_LOG.md.

## Requirements per `03_MVP_SCOPE.md`

The chosen dataset must support reporting:
- Precision, Recall, F1 on a held-out test set
- False-alert rate

State in the DEV_LOG entry whether the dataset is real or synthetic, and its known limitations.

## Scripts

Data acquisition / preprocessing scripts go in `data/datasets/scripts/` (to be created at Feature 2).
