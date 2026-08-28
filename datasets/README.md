# datasets/

ML migration offline data root. **Empty layout only** — no datasets were downloaded in Phase 0.

| Subfolder | Intended content |
|-----------|------------------|
| `document_parsing/` | Scanned/typed report images + gold IE fields |
| `risk_prediction/` | Structured metric rows + risk band labels (if ever ethically cleared) |
| `test_normalization/` | Raw alias → canonical test name / unit pairs |
| `retrieval/` | Query → relevant KB chunk ids for Hit@k / MRR |
| `image_quality/` | Pages labeled blur / skew / readable |
| `evaluation/` | Written reports from `models/*/evaluate.py` |

## Rules

- Do **not** commit real patient PHI.
- Prefer synthetic + public/consent fixtures.
- Existing Plan B/C labs remain under `data/datasets/` (do not delete).
- Large files: LFS or external store; keep manifests in git.

## Naming convention

```
datasets/<task>/
  README.md
  splits/{train,val,test}.jsonl   # when ready
  manifests/sources.md
```
