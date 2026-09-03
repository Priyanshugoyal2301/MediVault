# CHANGELOG

## [Phase 9] — 2026-08-11

### Added

- Platform hardening (`models/platform/`): reproducibility audit, unified benchmark suite, e2e validation, optional MLflow/W&B experiment tracking (disabled by default).
- Deliverables: `docs/benchmark_complete.md`, `docs/DEPLOYMENT.md`, `docs/KNOWN_LIMITATIONS.md`, platform tooling under `models/platform/`.
- Docs: expanded `MODEL_REGISTRY.md`, `DATASET_REFERENCE.md`, `FEATURE_FLAGS.md`, `BENCHMARK_GUIDE.md`, `TROUBLESHOOTING.md`.
- OCR `model_card.md` + `requirements.txt` (8/8 package audit pass).
- Tests `tests/phase9/`; validation **PASS** `validation/platform-validation.md`.

### Unchanged

- All public APIs, frontend, model architectures, and production feature-flag defaults (all ML flags off).

## [Phase 8] — 2026-08-11

### Added

- Document image quality (`models/image_quality/`): MobileNetV3 primary, EfficientNet fallback, OpenCV baseline; multi-label problem tags + quality score + OCR recommendation.
- Registry: `USE_IMAGE_QUALITY_MODEL` → ML quality gate; default passthrough (no OCR change).
- Synthetic degraded lab pages; train/eval; tests `tests/phase8/`.
- Validation **PASS WITH OBSERVATIONS** `validation/model8-validation.md`.
- Benchmark `docs/benchmark_phase8.md`.

### Unchanged

- `/parse` request/response schema, frontend, OCR/normalizer/retrieval/risk/forecast/health/anomaly engines.
- Default flag off.

## [Phase 7] — 2026-08-11

### Added

- Lab anomaly detection (`models/anomaly_detection/`): Isolation Forest primary, LOF fallback, Robust Z baseline; Autoencoder/OCSVM stubs.
- Registry: `USE_ANOMALY_MODEL` / alias `USE_OUTLIER_MODEL` → ML + statistical fallback; default statistical path preserved.
- Synthetic anomaly datasets; metrics (Precision@K, Recall@K, ROC-AUC, PR-AUC, FPR, latency).
- Tests `tests/phase7/`; validation **PASS WITH OBSERVATIONS** `validation/model7-validation.md`.
- Benchmark `docs/benchmark_phase7.md`.

### Unchanged

- `/anomaly/detect` request/response schema, frontend, OCR, normalizer, retrieval, risk, forecast, health score engines.
- Default all ML flags off.

## [Phase 6] — 2026-08-11

### Added

- Personalized health score (`models/health_score/`): XGBoost primary, LightGBM fallback, linear baseline; 0–100 score + band + confidence.
- Reusable explainability (`models/explainability/`): SHAP TreeExplainer + fallback local/global importance; per-patient positive/negative contributors.
- Registry: `USE_HEALTH_SCORE_MODEL` → ML scorer + explanations; default unavailable.
- Synthetic train/eval datasets; metrics (MAE, RMSE, MAPE, R², calibration, feature stability).
- Tests `tests/phase6/`; validation **PASS WITH OBSERVATIONS** `validation/model6-validation.md`.
- Benchmark `docs/benchmark_phase6.md`.

### Unchanged

- Existing HTTP APIs, frontend, OCR, normalizer, retrieval, risk, forecasting engines.
- Default all ML flags off.

## [Phase 5] — 2026-08-11

### Added

- Biomarker forecasting (`models/forecasting/`): LightGBM primary, XGBoost fallback, linear baseline; LSTM/Temporal Transformer stubs.
- Registry: `USE_FORECAST_MODEL` → ML longitudinal forecast + prediction intervals + trend; default unavailable.
- Synthetic train/eval datasets; metrics (MAE, RMSE, MAPE, R², PI coverage, calibration, trend accuracy).
- Tests `tests/phase5/`; validation **PASS WITH OBSERVATIONS** `validation/model5-validation.md`.
- Benchmark `docs/benchmark_phase5.md`.

### Unchanged

- Existing HTTP APIs, frontend, OCR, normalizer, retrieval, disease risk packages.
- Default all ML flags off.

## [Phase 4] — 2026-08-11

### Added

- Disease risk engine (`models/risk_prediction/`): XGBoost / LightGBM / logistic / sklearn_gb backends for 5 conditions.
- Registry: `USE_RISK_MODEL` / alias `USE_DISEASE_RISK_MODEL` → ML multi-condition risk + safety disclaimers.
- Synthetic train/eval datasets; metrics (ROC-AUC, PR-AUC, ECE, confusion, importance).
- Tests `tests/phase4/`; validation **PASS** `validation/model4-validation.md`.
- Benchmark `docs/benchmark_phase4.md`.

### Unchanged

- Existing HTTP APIs, frontend, OCR, normalizer, retrieval internals.
- Default flags off (unavailable risk path).

## [Phase 3] — 2026-08-11

### Added

- Semantic medical retrieval (`models/retrieval/`): BGE / MiniLM / offline TF-IDF embedders, FAISS/NumPy vector store abstraction, chunking, train/evaluate/infer.
- Registry: `USE_EMBEDDING_SEARCH=1` → Semantic + BM25 fallback; default BM25 preserved.
- Datasets `datasets/retrieval/`; tests `tests/phase3/`; validation **PASS** `validation/model3-validation.md`.
- Benchmark `docs/benchmark_phase3.md` (MRR improves 0.806 → 0.958 offline).

### Unchanged

- `/qa` API schema, frontend, OCR, normalizer internals, anomaly/risk/health score, BM25 code path.

## [Phase 2] — 2026-08-11

### Added

- Medical Test Normalizer (`models/normalizer/`): preprocess, char-TFIDF / optional ModernBERT / ClinicalBERT backends, LOINC subset, train/evaluate/infer.
- Registry path: `USE_ML_NORMALIZER=1` → ML + rule Fallback; default remains AliasNormalizer.
- `/parse` applies normalizer to `test_name` (schema unchanged).
- Datasets under `datasets/test_normalization/` (synthetic + LOINC subset; no full UMLS).
- Tests: `tests/phase2/`; validation `validation/model2-validation.md` (**PASS**).
- Benchmark: `docs/benchmark_phase2.md`.

### Unchanged

- Unlimited-OCR internals, retrieval, risk, health score, anomaly logic, public API fields, frontend, DB schema.
- Production defaults: all ML flags **off**.

## [Phase 1A] — 2026-08-11

### Hardened (engineering only)

- Fallback: empty labs / malformed JSON / timeouts / crashes → legacy (`O-07`).
- Backend `auto` no longer cascades to local HF load (`O-06`); explicit allow flags for local weights/download.
- Startup config validation + `/health` Unlimited readiness; PHI remote-endpoint warning.
- Richer parse/fallback logs; decoupled legacy map (`CompatibilityLabValue`).
- Tests: `tests/phase1a/`; observation review; `docs/benchmark_phase1a.md`.
- Docs: CONFIGURATION, DEPLOYMENT, ML_ARCHITECTURE, API, SYSTEM_DESIGN, DATAFLOW, TRAINING, ROADMAP, evaluation notes.

### Unchanged

- Public APIs, FE, DB, retrieval, normalizer, anomaly, risk, health score.
- Default `USE_UNLIMITED_OCR=0`. Accuracy not improved (out of scope).

## [Phase 1] — 2026-08-11

### Added

- `models/ocr` Unlimited-OCR package: preprocess, client (http/local/stub), postprocess Medical JSON, metrics, dataset infra, evaluate/train scaffolds.
- `FallbackDocumentParser` — legacy automatic recovery.
- Feature flag operators: `USE_UNLIMITED_OCR`, `UNLIMITED_OCR_*` env vars.
- `tests/phase1/` suite.
- Validation: `validation/model1-validation.md` (**PASS**).
- Benchmark: `docs/benchmark_phase1.md`, evaluation JSON.
- Docs: model card, model registry, phase1 summary.

### Changed

- AI registry selects document parser by flag (default legacy).
- `/parse` logs parser path; wraps unexpected errors without changing response schema.

### Not changed

- Public API contracts, frontend, DB schema, retrieval, anomaly, risk.
