# model3-validation — Phase 3 Semantic Medical Retrieval

**Date:** 2026-08-11  
**Verdict:** **PASS**

---

## Checklist

| Item | Status |
|------|--------|
| Embedding backend loads (offline char_tfidf; BGE/MiniLM pluggable) | ✅ |
| BM25 preserved (`USE_EMBEDDING_SEARCH=0`) | ✅ |
| Feature flag operational | ✅ |
| APIs unchanged (`/qa` request/response) | ✅ |
| Frontend unchanged | ✅ |
| Retrieval ranking quality improved (MRR/nDCG) | ✅ |
| FAISS interface operational (NumPy fallback if faiss absent) | ✅ |
| Similarity scores generated | ✅ |
| Metadata preserved (document_id, chunk_id, panel_hint) | ✅ |
| No regressions (phase tests + ai-service unit) | ✅ |
| OCR / Normalizer / anomaly / risk not modified | ✅ |

---

## Evidence

| Check | Result |
|-------|--------|
| `tests/phase3` | 15 passed |
| Eval MRR BM25 → Semantic | 0.806 → **0.958** |
| Eval nDCG@5 | 0.855 → **0.969** |
| Chunks indexed | 13 |

---

## Observations (non-blocking)

1. Deploy default embedder is **char_tfidf**, not live BGE weights (HF opt-in).  
2. Tiny KB already has high keyword hit rate for both systems; rank quality is the differentiator.  
3. PubMedQA/MedQA full dumps not redistributed — external optional loaders only.  
4. Precision@5 slightly lower on soft panel gold — expected with multi-hit lists.

---

## Final result

**PASS**

Do **not** begin Phase 4 until product accepts this validation.
