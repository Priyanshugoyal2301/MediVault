# models/risk_prediction — Personalized Disease Risk (Phase 4)

## Status

| Flag | Path |
|------|------|
| `USE_RISK_MODEL=0` / `USE_DISEASE_RISK_MODEL=0` (default) | `UnavailableRiskPredictor` |
| either flag =1 | `DiseaseRiskEngine` (ML multi-condition) |

## Architecture

| Role | Model |
|------|-------|
| Primary | XGBoost (if installed) |
| Fallback | LightGBM (if installed) |
| Baseline | Logistic Regression |
| Offline | sklearn HistGradientBoosting |

## Conditions

Type 2 Diabetes · Anemia · CKD · Liver Dysfunction · Thyroid Dysfunction

## Safety

Outputs are **risk probabilities only** — never diagnoses.  
Always includes: “Risk estimate only / not a medical diagnosis / informational only.”

## Commands

```bash
python models/risk_prediction/train.py
python models/risk_prediction/evaluate.py
```

## Env

| Variable | Default |
|----------|---------|
| `USE_RISK_MODEL` | `0` |
| `USE_DISEASE_RISK_MODEL` | alias of above |
| `RISK_MODEL_BACKEND` | `auto` |

## Data

Synthetic educational dataset shipped. MIMIC/NHANES/eICU not redistributed —
optional offline paths per `datasets/risk_prediction/LICENSING.md`.
