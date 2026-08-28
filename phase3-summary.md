# Phase 3 Summary — Semantic Medical Retrieval

## Overview

Phase 3 adds embedding-based **SemanticRetriever** behind `USE_EMBEDDING_SEARCH`, with FAISS-compatible vector storage and mandatory BM25 preservation/fallback. Public `/qa` schema unchanged. Default remains BM25.

## Architecture Changes

```
USE_EMBEDDING_SEARCH=0 → BM25Retriever → rag BM25+intent
USE_EMBEDDING_SEARCH=1 → FallbackRetriever(SemanticRetriever, BM25)
Semantic: chunk KB → embed (BGE|MiniLM|char_tfidf) → FAISS/NumPy → top-k
```

## Files Created

- Full `models/retrieval/` package (infer, train, evaluate, dataset, metrics, embeddings, vector_store, chunking, config, model card)
- `tests/phase3/`
- `datasets/retrieval/eval_benchmark.jsonl` (+ licensing notes)
- `docs/benchmark_phase3.md`, validation, phase3-summary

## Files Modified

- `services/ai-service/adapters/retriever.py` — Semantic + Fallback
- `services/ai-service/core/registry.py` — flag branch
- `.env.example`, docs (CHANGELOG, MODEL_REGISTRY, CONFIG, DATAFLOW, etc.)

## Dependencies

- Existing: sklearn, numpy, optional sentence-transformers  
- Optional: `faiss-cpu` (auto-falls back to NumPy)

## Datasets

| Source | Role |
|--------|------|
| MediVault KB | Index corpus |
| Synthetic medical QA | Eval |
| PubMedQA/MedQA | Optional external only (not shipped) |

## Feature Flags

| Flag | Default | Effect |
|------|---------|--------|
| `USE_EMBEDDING_SEARCH` | `0` | BM25 vs Semantic+fallback |
| `RETRIEVAL_EMBEDDING_BACKEND` | `auto` | Embedder choice |
| `RETRIEVAL_ALLOW_HF` | `0` | BGE/MiniLM load |

## Benchmark Results

Semantic MRR **0.958** vs BM25 **0.806**; nDCG@5 **0.969** vs **0.855** (offline char_tfidf).

## Validation Status

**PASS** — `validation/model3-validation.md`

## Documentation Updated

CONFIG, DATAFLOW, ML_ARCHITECTURE, SYSTEM_DESIGN, ROADMAP, migration plan, model registry, changelog, evaluation notes, developer guide, diagrams.

## Known Limitations

- Default offline embedder ≠ production BGE quality until HF allowed.  
- Tiny curated KB only.  
- Safety/synthesizer unchanged (no free-form LLM answer generation).

## Recommendations

1. Keep production flag off until BGE warm path tested in staging.  
2. Install faiss-cpu for larger corpora.  
3. Expand labeled retrieval set before comparing against full Plan B FAQ pack with HF models.

## Migration Progress

| Phase | Status |
|-------|--------|
| 0–2 | Done |
| **3 Semantic Retrieval** | **Done (PASS)** |
| 4+ | Not started |

## Repository Health Score

**8.5 / 10** (modular, deploy-safe, BM25 rollback zero-code)

## Definition of Done

All criteria met → **PHASE 3 COMPLETE**  
**Do not begin Phase 4.**
