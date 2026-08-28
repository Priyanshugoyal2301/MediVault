# model2-validation — Phase 2 Medical Test Normalization

**Date:** 2026-08-11  
**Verdict:** **PASS**

---

## Checklist

| Item | Status |
|------|--------|
| Model loads (`MedicalTestNormalizer`) | ✅ |
| Rule-based fallback preserved (`AliasNormalizer`) | ✅ |
| Feature flag `USE_ML_NORMALIZER` (default 0) | ✅ |
| APIs unchanged (`ParsedValueOut` schema) | ✅ |
| Frontend unchanged | ✅ |
| Canonical mapping correct (HGB→Haemoglobin, SGPT→ALT) | ✅ |
| Confidence generated (detailed `normalize()`) | ✅ |
| LOINC mapping for curated set | ✅ |
| Unknown terms handled gracefully | ✅ |
| No regression (phase1/1a/2 + ai-service unit) | ✅ |
| Train / evaluate pipelines | ✅ |
| Benchmarks written | ✅ |
| Deployable offline (`char_tfidf`) | ✅ |
| Unlimited-OCR package not rewritten | ✅ |
| Retrieval / risk / health score not modified | ✅ |

---

## Test evidence

| Suite | Result |
|-------|--------|
| `tests/phase2` | 30 passed |
| `tests/unit/ai-service/test_ml_infra.py` | included / green |
| Train | 1155 pairs, 33 labels, artifacts saved |
| Eval Top-1 ML | ≈ 0.999 (vs rules ≈ 0.693 on noisy synthetic set) |

---

## Observations (non-blocking)

1. Production offline path uses **char n-gram TF-IDF**, not live ModernBERT weights (architecture swap supported via config).  
2. Eval is synthetic synonym-heavy; real multi-lab OCR surface forms still need labeled production sample.  
3. Public API does not expose LOINC/confidence (backward compatibility).  
4. One rare confusion: HDL ↔ TC/HDL Ratio in NN path.

---

## Final result

**PASS**

Proceed to Phase 3 only with product acceptance. Default flags remain off for production demo path.
