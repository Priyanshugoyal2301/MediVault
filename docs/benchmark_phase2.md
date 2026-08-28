# Benchmark Report — Phase 2 Medical Test Normalization

**Date:** 2026-08-11  
**Artifact:** `datasets/evaluation/normalizer_phase2_latest.json`  
**Backend under test:** `char_tfidf` (offline deploy default)

## Setup

| Item | Value |
|------|-------|
| Train pairs | ~1155 synonym/variant strings |
| Eval size | 942 rows (synthetic noisy + unknown) |
| Known-class rows | 937 |
| Labels | 33 canonical concepts |
| HF ModernBERT | Not loaded (deploy-safe offline path) |

## Performance (known-class)

| System | Top-1 Acc | Top-3 Acc | P / R / F1 | Mean latency |
|--------|----------:|----------:|------------|-------------:|
| Rule-based (`AliasNormalizer`) | **0.693** | — | 0.693 | ~0.28 ms |
| ML (`MedicalTestNormalizer`) | **0.999** | **1.000** | 0.999 | ~2.6 ms |

### Other ML metrics

| Metric | Value |
|--------|------:|
| Unknown-term accuracy | 0.999 |
| LOINC mapping accuracy | 0.999 |
| p95 latency | ~8.7 ms |
| Max latency | ~16 ms |

## Failure analysis

Compact confusion (ML):

| True | Pred | Count |
|------|------|------:|
| HDL Cholesterol | TC/HDL Ratio | 1 |

Almost all alias exact matches score conf ≥ 0.99; residual error is rare nearest-neighbor confusion on ratio-like lipids.

Rule path fails more often on:

- Trailing context (`… (blood)`)
- Mixed punctuation / spacing variants  
- Long multi-word labels with extra noise  

ML recovers these via char n-gram cosine nearest neighbor.

## Memory / GPU

| Resource | char_tfidf offline |
|----------|--------------------|
| GPU | not used |
| Peak extra RSS | low (sklearn TF-IDF matrix for dozens of prototypes/train strings) |
| Model artifacts | `models/normalizer/artifacts/` (vectorizer + matrix + labels) |

## Recommendations

1. Keep production **`USE_ML_NORMALIZER=0`** until unlimited-OCR + labeled reports are re-evaluated with flag on.  
2. Default backend stays **`char_tfidf`** for demo/laptop deploy.  
3. Optional ops path: `NORMALIZER_ALLOW_HF=1` + `NORMALIZER_BACKEND=modernbert` for encoder swap **without** changing call sites.  
4. Expand synonym table for remaining lipid ratio confusions.  
5. Phase 3 retrieval must query on **canonical** stored names produced here.

## Verdict

ML normalizer **beats** expanded rules on the synthetic benchmark while keeping legacy rules as flag-off / fallback path.
