# Developer Guide — Semantic Retrieval (Phase 3)

1. Default: `USE_EMBEDDING_SEARCH=0` (BM25).
2. Build index: `python models/retrieval/train.py`
3. Evaluate: `python models/retrieval/evaluate.py`
4. Enable: `USE_EMBEDDING_SEARCH=1` then **restart** ai-service.
5. Optional BGE: `RETRIEVAL_ALLOW_HF=1` + `RETRIEVAL_EMBEDDING_BACKEND=bge`
6. Tests: `python -m pytest tests/phase3 -q`
7. Do not start Phase 4 until validation accepted.
