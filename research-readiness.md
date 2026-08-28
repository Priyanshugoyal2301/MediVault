# Research Readiness Assessment

## Strengths

- Protocol + registry architecture with feature-flag cutover  
- Train / evaluate / infer entrypoints per model  
- Synthetic datasets + licensing notes for redistribute safety  
- Safety language for risk/forecast/score/anomaly  
- Unified audit + benchmark suite (`models/platform/`)  
- Optional MLflow/W&B experiment hooks (default off)

## Gaps vs clinical research platform

| Gap | Severity | Mitigation path |
|-----|----------|-----------------|
| Primary metrics on synthetic or fixture data | High | Licensed real corpora offline only |
| No multi-site prospective evaluation | High | Institutional IRB study |
| Residual / heuristic confidence calibration | Medium | Conformal / Platt on real holdouts |
| Document quality trained on synthetic blur | Medium | Capture real phone lab photos |
| OCR VLM quality depends on endpoint | High | Private warm Unlimited endpoint |

## Suggested paper/study claims (allowed)

- Architecture for flag-gated medical document ML pipelines  
- Offline synthetic reproducibility recipes  
- Latency of production-safe defaults  

## Disallowed claims without further evidence

- Diagnostic accuracy  
- Clinical outcome benefit  
- Population risk equivalence to validated medical devices  

**Status:** Research-**scaffolding ready**; not clinical-validation ready.
