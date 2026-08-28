# datasets/document_parsing

Labeled / synthetic documents for Unlimited-OCR evaluation (Phase 1).

## Layout (when populated)

```
document_parsing/
  synthetic/
  indian_lab/
  medical_laboratory_ocr/
  mimic_future/          # placeholder only — no MIMIC download in Phase 1
  index.jsonl
```

## Current source

If `index.jsonl` is empty, `models.ocr.dataset.DocumentParsingDataset` falls back to
Plan C text fixtures (`data/datasets/plan_c/ie_fixtures.py`).

## Rules

- No PHI.
- No automatic downloads.
- MIMIC remains a **future** slot only.
