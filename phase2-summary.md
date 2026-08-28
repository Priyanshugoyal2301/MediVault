# Phase 2 Summary — Medical Test Normalization

## Overview

Phase 2 adds an ML-capable **Medical Test Normalization** engine that maps lab name aliases (e.g. HGB, SGPT) to canonical concepts and curated LOINC codes. Legacy rule mapping is preserved. Default flag **`USE_ML_NORMALIZER=0`**.

## Architecture Changes

```
Extracted test name
  → get_normalizer()
       flag 0: AliasNormalizer (rules)
       flag 1: FallbackNormalizer(MedicalTestNormalizer, Alias)
  → canonical test_name on /parse values (schema unchanged)
```

Encoder backends (swappable):

| Priority | Name | Deploy default |
|----------|------|----------------|
| Primary | ModernBERT | optional HF |
| Fallback | ClinicalBERT | optional HF |
| Offline | char_tfidf | **yes** |

## Files Created

- `models/normalizer/` — train, evaluate, infer, dataset, preprocess, postprocess, metrics, vocabulary, encoder_backends, config, artifacts, model card, requirements  
- `datasets/test_normalization/*`  
- `tests/phase2/`  
- `docs/benchmark_phase2.md`, `docs/benchmark-results/phase2-normalizer.md`  
- `validation/model2-validation.md`  
- `phase2-summary.md`, `benchmark_phase2.md`

## Files Modified

- `services/ai-service/adapters/normalizer.py`  
- `services/ai-service/core/registry.py`  
- `services/ai-service/routers/parse.py` (apply normalizer)  
- `packages/ml-interfaces/normalizer.py`  
- `.env.example`  
- Documentation set (CHANGELOG, MODEL_REGISTRY, migration plan, CONFIG, DATAFLOW, etc.)

## Dependencies Added

- Uses existing `scikit-learn` / `numpy` / `PyYAML`  
- Optional: `torch`, `transformers` for ModernBERT/ClinicalBERT (`NORMALIZER_ALLOW_HF=1`)

## Datasets Integrated

| Dataset | Role |
|---------|------|
| Curated LOINC subset | Canon ↔ LOINC |
| Synthetic Indian synonyms | Train/eval aliases |
| Generated noisy eval | Abbreviations, casing, punctuation, unknowns |
| Full UMLS | **Not** redistributed (licensing) |

## Feature Flags

| Flag | Default | Effect |
|------|---------|--------|
| `USE_ML_NORMALIZER` | `0` | Rules vs ML+fallback |
| `NORMALIZER_BACKEND` | `char_tfidf` | Encoder choice |
| `NORMALIZER_ALLOW_HF` | `0` | HF weights opt-in |

## Benchmark Results

- ML Top-1 ≈ **0.999**, Top-3 = **1.0**, LOINC acc ≈ **0.999**  
- Rules Top-1 ≈ **0.693** on same noisy synthetic eval  
- See `docs/benchmark_phase2.md`

## Validation Status

**PASS** — `validation/model2-validation.md`

## Documentation Updated

README, docs/* CONFIG/DATAFLOW/ML_ARCHITECTURE/CHANGELOG/ROADMAP/MODEL_REGISTRY/migration plan, model card, evaluation notes, BIBLE normalizer note.

## Known Limitations

- Offline default is not live ModernBERT.  
- LOINC not on public API.  
- Synthetic eval ≠ real scan distribution.  
- Explainer templates still keyed to MVP canons (extended LFT canons may lack templates).

## Recommendations

1. Enable ML normalizer in staging with Unlimited-OCR flag on and remeasure field F1.  
2. Keep production default flags off until gates pass.  
3. Expand lipid/ratio edge cases.  
4. Phase 3 retrieval should assume canonical storage after this phase.

## Migration Progress

| Phase | Status |
|-------|--------|
| 0 Infra | Done |
| 1 OCR | Done |
| 1A Hardening | Done |
| **2 Normalizer** | **Done (PASS)** |
| 3 Retrieval | Not started |

## Repository Health Score

| Dimension | Score / 10 |
|-----------|------------|
| Modularity | 9 |
| Deploy safety | 9 |
| Tests | 8 |
| Benchmark honesty | 8 |
| Docs | 8 |
| **Overall** | **8.5 / 10** |

## Definition of Done

All required items met → **PHASE 2 COMPLETE**  
**Do not begin Phase 3 automatically.**
