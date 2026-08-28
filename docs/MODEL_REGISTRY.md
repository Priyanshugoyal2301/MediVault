# Model Registry — MediVault ML Platform

All ML flags **default OFF**. Production behavior remains non-ML defaults with graceful fallbacks.

| # | Component | Phase | Flag | Default path | Package | Card |
|---|-----------|-------|------|--------------|---------|------|
| 0 | Legacy OCR / parse | 0 | always | Tesseract + regex | `services/ai-service` | — |
| 1 | Unlimited-OCR | 1/1A | `USE_UNLIMITED_OCR` | Legacy parser | `models/ocr/` | [unlimited-ocr](./model-cards/unlimited-ocr.md) |
| 2 | Test normalizer | 2 | `USE_ML_NORMALIZER` | Alias rules | `models/normalizer/` | [normalizer](./model-cards/medical-test-normalizer.md) |
| 3 | Semantic retrieval | 3 | `USE_EMBEDDING_SEARCH` | BM25 | `models/retrieval/` | [retrieval](./model-cards/semantic-retriever.md) |
| 4 | Disease risk | 4 | `USE_RISK_MODEL` (+ disease alias) | Unavailable | `models/risk_prediction/` | [risk](./model-cards/disease-risk.md) |
| 5 | Biomarker forecast | 5 | `USE_FORECAST_MODEL` | Unavailable | `models/forecasting/` | [forecast](./model-cards/biomarker-forecast.md) |
| 6 | Health score + SHAP | 6 | `USE_HEALTH_SCORE_MODEL` | Unavailable | `models/health_score/` | [health](./model-cards/health-score.md) |
| 7 | Anomaly detection | 7 | `USE_ANOMALY_MODEL` / `USE_OUTLIER_MODEL` | Statistical series | `models/anomaly_detection/` | [anomaly](./model-cards/anomaly-detection.md) |
| 8 | Image quality | 8 | `USE_IMAGE_QUALITY_MODEL` | Passthrough OK | `models/image_quality/` | [quality](./model-cards/image-quality.md) |

---

## 1. Unlimited-OCR

| Field | Value |
|-------|-------|
| Purpose | Vision LLM / HTTP Medical JSON extraction from report images |
| Architecture | HTTP client + postprocess; optional local HF (opt-in) |
| Primary | Unlimited-OCR endpoint / stub |
| Fallback | Regex + Tesseract DocumentParser |
| Input | Image/PDF bytes + mime |
| Output | Structured lab fields (legacy value dicts) |
| Training data | N/A (external VLM); eval text fixtures |
| Evaluation data | `datasets/evaluation/ocr_phase1*.json` |
| Metrics | Field F1 bake-off (fixtures); engineering timings (1A) |
| Feature flag | `USE_UNLIMITED_OCR` |
| Status | Integrated, default off, hardened fallback |
| Limitations | Not a substitute for warm private OCR endpoint; no PHI to public cloud |
| Future | Private endpoint SLA; labeled scan corpus |

## 2. Medical Test Normalizer

| Field | Value |
|-------|-------|
| Purpose | Map OCR free-text test names → canonical names / LOINC subset |
| Primary | char-TFIDF / optional ModernBERT–ClinicalBERT |
| Fallback | Alias table |
| Input | test name string |
| Output | normalized name (+ confidence when ML) |
| Datasets | `datasets/test_normalization/` synthetic + LOINC subset |
| Metrics | Top-1 / Top-3 / latency (`normalizer_phase2_latest.json`) |
| Flag | `USE_ML_NORMALIZER` |
| Status | Integrated, default rules |
| Limitations | No full UMLS; HF backends optional |
| Future | Expand LOINC + human review loop |

## 3. Semantic Retrieval

| Field | Value |
|-------|-------|
| Purpose | Meaning-based ranking over knowledge + user chunks |
| Primary | BGE / MiniLM embeddings + FAISS |
| Fallback | BM25 |
| Input | Query + corpus chunks |
| Output | Ranked `RetrievedDocument` list |
| Datasets | `datasets/retrieval/` |
| Metrics | MRR / Recall / nDCG (`retrieval_phase3_latest.json`) |
| Flag | `USE_EMBEDDING_SEARCH` |
| Status | Integrated, default BM25 |
| Limitations | HF download opt-in; offline TF-IDF path for cold start |
| Future | Hybrid dense-sparse fusion weights |

## 4. Disease Risk Prediction

| Field | Value |
|-------|-------|
| Purpose | Non-diagnostic multi-condition probability signals from labs |
| Primary | XGBoost |
| Fallback | LightGBM → logistic / sklearn_gb |
| Input | Metrics list (+ demographics) |
| Output | Risk band, scores, drivers, disclaimers |
| Datasets | Synthetic; optional MIMIC/NHANES paths offline |
| Metrics | ROC-AUC, ECE (`risk_phase4_latest.json`) |
| Flag | `USE_RISK_MODEL` |
| Status | Integrated, default unavailable |
| Limitations | Synthetic training; not clinical diagnosis |
| Future | Clinician-calibrated labels |

## 5. Biomarker Forecasting

| Field | Value |
|-------|-------|
| Purpose | Future lab value forecast + interval + trend |
| Primary | LightGBM regressor |
| Fallback | XGBoost → linear |
| Input | Longitudinal history series |
| Output | Predicted value, PI, confidence, trend |
| Datasets | `datasets/forecasting/` synthetic |
| Metrics | MAE/RMSE/MAPE/R²/PI coverage |
| Flag | `USE_FORECAST_MODEL` |
| Status | Integrated, default unavailable |
| Limitations | Residual-std intervals; synthetic |
| Future | Quantile / conformal intervals; wearables |

## 6. Personalized Health Score

| Field | Value |
|-------|-------|
| Purpose | 0–100 orientation score + SHAP contributors |
| Primary | XGBoost regressor |
| Fallback | LightGBM → linear |
| Input | Labs + demographics + trend/risk proxies |
| Output | Score, band, confidence, ± contributors |
| Datasets | `datasets/health_score/` synthetic |
| Metrics | MAE/RMSE/R² + SHAP method |
| Flag | `USE_HEALTH_SCORE_MODEL` |
| Status | Integrated, default unavailable |
| Limitations | Synthetic heuristic labels |
| Future | Real orientation labels; cached TreeExplainer |

## 7. Anomaly Detection

| Field | Value |
|-------|-------|
| Purpose | Unsupervised unusual lab patterns |
| Primary | Isolation Forest |
| Fallback | LOF → Robust Z |
| Input | Series (API) / multi-marker profile |
| Output | Anomaly score, category, contributors; language: “Anomalous laboratory pattern” |
| Datasets | `datasets/anomaly_detection/` synthetic |
| Metrics | PR-AUC / Precision@K / FPR |
| Flag | `USE_ANOMALY_MODEL` |
| Status | Integrated, default statistical |
| Limitations | Synthetic injections; API is single-series |
| Future | Real FAR evaluation |

## 8. Image Quality Assessment

| Field | Value |
|-------|-------|
| Purpose | Pre-OCR suitability of report images |
| Primary | MobileNetV3-Small |
| Fallback | EfficientNet Lite0/B0 → OpenCV rules |
| Input | JPEG/PNG/TIFF/PDF bytes |
| Output | ok, quality score, problems, recommendation |
| Datasets | Synthetic degradations; DocLayNet offline optional |
| Metrics | Multilabel F1 / ready ROC-AUC |
| Flag | `USE_IMAGE_QUALITY_MODEL` |
| Status | Integrated, default passthrough |
| Limitations | Synthetic; PDF needs pypdfium2 for true raster |
| Future | Phone photo corpus |

---

**Platform tools:** `models/platform/` (audit, unified benchmark, e2e validation, optional MLflow/W&B).  
**Unified benchmark:** [benchmark_complete.md](../benchmark_complete.md) · [docs/benchmark_complete.md](./benchmark_complete.md)
