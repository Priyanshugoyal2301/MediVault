# Benchmark Report — Phase 4 Disease Risk Prediction

**Date:** 2026-08-11  
**Artifact:** `datasets/evaluation/risk_phase4_latest.json`  
**Backend:** XGBoost (primary architecture; LightGBM available; sklearn_gb offline fallback)

## Setup

| Item | Value |
|------|-------|
| Train | ~900 synthetic educational patients |
| Eval | 250 synthetic patients |
| Conditions | diabetes, anemia, CKD, liver, thyroid |
| Flag default | `USE_RISK_MODEL=0` |

## Macro performance

| System | Macro ROC-AUC | Mean latency |
|--------|--------------:|-------------:|
| Rule thresholds | 0.962 | ~0.01 ms |
| **ML (XGBoost)** | **0.984** | ~2.7 ms |

ML improves average discrimination vs fixed thresholds on the synthetic benchmark.

## Per-condition (ML highlights)

See full JSON for precision/recall/F1/PR-AUC/ECE/confusion/ROC points/feature importance per disease.

Typical strong signals:

| Condition | Key contributors |
|-----------|------------------|
| Type 2 Diabetes | HbA1c, fasting glucose, BMI |
| Anemia | Hemoglobin, RBC, sex |
| CKD | eGFR, creatinine, urea |
| Liver | ALT, AST, ratio |
| Thyroid | TSH, Free T4 |

## Safety

All summaries include non-diagnostic framing. No “you have disease X” language in engine output.

## Recommendations

1. Keep production `USE_RISK_MODEL=0` until clinician review + real labeled data.  
2. Install `xgboost`/`lightgbm` in deploy images for primary/fallback; sklearn_gb always works.  
3. Re-train on licensed MIMIC/NHANES offline dumps before clinical claims.  
4. Do not expose scores on patient UI without disclaimer UX review.

## Verdict

Engineering complete: swappable backends, flags, calibration metrics, safety language, BM25/OCR/normalizer untouched.
