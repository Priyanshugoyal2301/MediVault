# datasets/test_normalization

Lab test alias → canonical name (+ LOINC when known).

## Licensing

| Resource | Redistributed? | Notes |
|----------|----------------|-------|
| Curated LOINC codes (`loinc_subset.json`) | Yes (subset identifiers only) | LOINC® is copyright Regenstrief. We ship **only** codes/names used by MediVault panels — not the full LOINC release. See https://loinc.org |
| UMLS Metathesaurus | **No** | Do not commit UMLS RRF files. Optionally merge synonyms offline if you hold a free UMLS license. |
| Synthetic Indian synonyms | Yes | Generated educational fixtures; free to use |

## Files

Materialized by `models.normalizer.dataset.ensure_dataset_files()`:

- `train_pairs.jsonl`
- `eval_benchmark.jsonl`
- `synthetic_indian_synonyms.jsonl`
- `loinc_subset.json`

No PHI. Do not commit real patient labels.
