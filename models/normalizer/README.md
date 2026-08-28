# models/normalizer — Medical Test Normalization (Phase 2)

## Status

**Phase 2 integrated.** Maps raw lab test names → canonical concepts + LOINC.

| Flag | Path |
|------|------|
| `USE_ML_NORMALIZER=0` (default) | Rule-based `AliasNormalizer` (never deleted) |
| `USE_ML_NORMALIZER=1` | `MedicalTestNormalizer` (ML) with rule fallback |

## Architecture

| Role | Backend | Notes |
|------|---------|-------|
| Primary | ModernBERT (`answerdotai/ModernBERT-base`) | Optional HF; requires `NORMALIZER_ALLOW_HF=1` |
| Fallback HF | ClinicalBERT | Same allow flag |
| Offline / default | Char n-gram TF-IDF + cosine NN | sklearn; always deployable |

Business logic uses `EncoderBackend` protocol; swap models without changing callers.

## Pipeline

```
raw name → preprocess → exact alias → ML rank → postprocess
         → {canonical, confidence, loinc, alternatives, status}
```

## Train / evaluate / infer

```bash
python models/normalizer/train.py
python models/normalizer/evaluate.py
python -m models.normalizer.infer_cli "HGB" "SGPT" --json
```

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `USE_ML_NORMALIZER` | `0` | Registry switch |
| `NORMALIZER_BACKEND` | `char_tfidf` | `char_tfidf` \| `modernbert` \| `clinicalbert` |
| `NORMALIZER_ALLOW_HF` | `0` | Allow HF weight load |
| `NORMALIZER_MIN_CONFIDENCE` | `0.55` | Below → UNKNOWN pass-through |
| `NORMALIZER_ARTIFACTS_DIR` | `models/normalizer/artifacts` | Artifact path |

## Safety

- Legacy rule normalizer preserved.
- Unknown terms: pass-through, `unknown_term=True` — no invented diagnoses.
- Public `/parse` schema unchanged (only `test_name` value quality improves when applied).
