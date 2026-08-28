# datasets/retrieval

Query → relevant KB sources for Hit@k / MRR.

| File | Notes |
|------|-------|
| `eval_benchmark.jsonl` | Synthetic medical / synonym / misspell queries |
| `LICENSING.md` | PubMedQA/MedQA not redistributed |

Build with: `python models/retrieval/train.py` also calls `ensure_dataset_files()`.
