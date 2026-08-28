# Model Card — Semantic Medical Retriever (Phase 3)

## Model details

| Field | Value |
|-------|-------|
| Name | SemanticRetriever |
| Primary | BAAI/bge-small-en-v1.5 |
| Fallback | sentence-transformers/all-MiniLM-L6-v2 |
| Offline | char TF-IDF + SVD |
| Vector store | FAISS (or NumPy) |
| Flag | `USE_EMBEDDING_SEARCH` (default off) |

## Intended use

Retrieve educational KB chunks (+ optional user lab values) for template Q&A.

**Not** a diagnostic model. Answers still come from template synthesizer + safety layer.

## Data

| Source | Note |
|--------|------|
| MediVault `data/knowledge-base` | Curated educational text |
| PubMedQA / MedQA | Not redistributed; optional external paths |
| Synthetic eval | `datasets/retrieval/eval_benchmark.jsonl` |

## Metrics

See `docs/benchmark_phase3.md`.

## Caveats

- Demo default remains BM25 for boot reliability.
- Cold HF download of BGE is intentionally gated by `RETRIEVAL_ALLOW_HF`.
- Similarity scores are ranking signals, not calibrated probabilities.
