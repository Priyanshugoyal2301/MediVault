# Unified Benchmark Suite — MediVault ML Platform

**Generated:** 2026-08-11T22:27:01  
**Python:** 3.12.10 · **OS:** Windows AMD64

## Host probes

- CPU count: `32`
- Process RSS (MB): `50.12`
- GPU available: `True` (NVIDIA GeForce RTX 5070 Laptop GPU)

## Production-safe path latency (flags default OFF)

| Component | Latency (ms) |
|-----------|--------------|
| `quality_passthrough_ms` | 20.833 |
| `normalizer_alias_ms` | 156.403 |
| `risk_unavailable_ms` | 1.252 |
| `forecast_unavailable_ms` | 1.06 |
| `health_unavailable_ms` | 1.245 |
| `anomaly_statistical_ms` | 9.164 |
| `retriever_bm25_ms` | 9.904 |
| `parser_legacy_ms` | 0.989 |

## Artifact sizes (on-disk MB)

| Package | Size (MB) |
|---------|-----------|
| `ocr` | — |
| `normalizer` | 15.026 |
| `retrieval` | 0.538 |
| `risk` | 0.437 |
| `forecast` | 0.988 |
| `health_score` | 0.175 |
| `anomaly` | 1.368 |
| `image_quality` | 0.796 |

## Component evaluation snapshot

| # | Component | Eval artifact present | Headline metrics (from JSON) |
|---|-----------|----------------------|------------------------------|
| 1 OCR | present=yes | see ocr_phase1_latest (field F1 bake-off) |
| 1A OCR harden | present=yes | hardening timings |
| 2 Normalizer | present=yes | top1/f1 available in JSON keys: model, backend, n_eval, n_known, rule_based, ml_normalizer |
| 3 Retrieval | present=yes | MRR/Recall keys: model, embedding_backend, vector_store, index_chunks, n_queries, bm25 |
| 4 Risk | present=yes | backend=xgboost |
| 5 Forecast | present=yes | macro_mae=4.589474512834373 e2e_ms=13.3552000625059 |
| 6 Health score | present=yes | mae=2.0013701155959667 r2=0.9909036240400039 e2e_ms=1253.1677999068052 |
| 7 Anomaly | present=yes | active=isolation_forest IF_PR-AUC=0.7112153379679302 |
| 8 Image quality | present=yes | active=mobilenet_v3 F1=0.952040816070827 |

## Known failure cases (cross-platform)

| Component | Failure class | Mitigation |
|-----------|---------------|------------|
| OCR | Empty Unlimited response | Legacy fallback |
| Normalizer | Unknown alias | Soft leave original / rules |
| Retrieval | Dense load fail | BM25 fallback |
| Risk / Forecast / Health / Anomaly ML | Init error | Unavailable or statistical path |
| Image quality | Init error | OpenCV rules / passthrough |
| All flags ON | Cumulative latency / memory | Staged enablement |

## Notes

- Default feature flags are OFF — latency figures are production-safe paths.
- Phase metrics come from prior offline synthetic/real-fixture evaluations.
- GPU optional; most models train/infer on CPU.

Per-phase detail: `docs/benchmark_phase*.md`.

Regenerate: `python models/platform/benchmark_suite.py`
