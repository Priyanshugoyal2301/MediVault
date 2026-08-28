# Model Card — Disease Risk Predictor (Phase 4)

## Model details

| Field | Value |
|-------|-------|
| Name | DiseaseRiskEngine |
| Primary | XGBoost Classifier |
| Fallback | LightGBM |
| Baseline | Logistic Regression |
| Offline | HistGradientBoosting |
| Flag | `USE_RISK_MODEL` / `USE_DISEASE_RISK_MODEL` |

## Intended use

**Non-diagnostic** statistical risk probabilities from structured lab biomarkers.

## Out of scope

- Diagnosis (“you have X”)
- Treatment recommendations
- Emergency triage

## Training data

Synthetic educational lab rows (generated). Optional external MIMIC/NHANES if operator provides licensed dumps.

## Safety language (mandatory)

- Risk estimate only  
- Not a medical diagnosis  
- For informational purposes only  
- Increased statistical risk only  

## Caveats

- Synthetic offline ROC is not transferable to clinical populations without revalidation.  
- Default flag **off**.  
