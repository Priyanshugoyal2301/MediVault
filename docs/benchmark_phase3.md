# Benchmark Report — Phase 3 Semantic Medical Retrieval

**Date:** 2026-08-11  
**Artifact:** `datasets/evaluation/retrieval_phase3_latest.json`  
**Semantic backend under test:** `char_tfidf` + NumPy IP index (FAISS-compatible; faiss optional)  
**Primary/fallback HF models (config):** BGE-small-en-v1.5 / all-MiniLM-L6-v2 (gated by `RETRIEVAL_ALLOW_HF`)

## Setup

| Item | Value |
|------|-------|
| KB | MediVault `data/knowledge-base` (13 chunks) |
| Queries | 12 synthetic medical/synonym/abbrev/misspell/long |
| Flag default | `USE_EMBEDDING_SEARCH=0` → BM25 production path |

## Performance comparison

| Metric | BM25+intent | Semantic |
|--------|------------:|---------:|
| Keyword hit rate | 1.00 | 1.00 |
| Recall@5 | 1.00 | 1.00 |
| Recall@10 | 1.00 | 1.00 |
| Precision@5 | 0.225 | 0.200 |
| **MRR** | **0.806** | **0.958** |
| **nDCG@5** | **0.855** | **0.969** |
| Mean latency (ms) | ~0.58 | ~0.89 |
| p95 latency (ms) | ~0.84 | ~1.82 |

### Resource notes

| Metric | Approx |
|--------|--------|
| Index chunks | 13 |
| Embed build | sub-second offline TF-IDF |
| GPU | not used (offline path) |
| Index footprint | small (numpy vectors in `models/retrieval/artifacts/`) |

## Failure analysis

- Precision@5 slightly lower for semantic on this tiny gold-to-panel labeling — multi-chunk sources dilute precision.
- MRR/nDCG improve: better first-rank placement for synonym / abbreviation queries.
- Misspellings (e.g. “triglicerides”) assisted by char n-grams offline; BGE would strengthen when HF allowed.

## Recommendations

1. Production default remains **BM25** (`USE_EMBEDDING_SEARCH=0`) for cold-boot reliability.  
2. Stage semantic with private warm artifacts; optional `RETRIEVAL_ALLOW_HF=1` + BGE for production-quality dense vectors.  
3. Expand labeled query set with operator PubMedQA/MedQA offline dumps.  
4. Install `faiss-cpu` when index size grows past toy KB.

## Verdict

Semantic path is **operational**, **BM25 preserved**, and offline eval shows **higher MRR/nDCG** on the MediVault synthetic benchmark without changing `/qa` APIs.
