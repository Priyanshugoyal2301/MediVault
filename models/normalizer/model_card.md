# Model Card — Medical Test Normalizer (Phase 2)

## Model details

| Field | Value |
|-------|-------|
| Name | MedicalTestNormalizer |
| Primary architecture | ModernBERT (optional) |
| Fallback architecture | ClinicalBERT (optional) |
| Offline architecture | Char n-gram TF-IDF + cosine NN |
| Task | Lab test name → canonical name + LOINC |
| Flag | `USE_ML_NORMALIZER` (default off) |

## Intended use

Canonicalize laboratory analyte nomenclature for vault consistency and future ML.

**Not** for diagnosis, drug dosing, or clinical decision support.

## Data

| Source | Content | License note |
|--------|---------|--------------|
| Curated LOINC codes | Minimal codes for MVP + LFT/RFT panels | LOINC® Regenstrief; subset identifiers only — not full LOINC release |
| Synthetic Indian lab synonyms | Generated aliases / abbreviations | Internal synthetic; free to use |
| UMLS | **Not redistributed** | Use local UMLS license offline if expanding synonyms |

## Metrics (typical offline eval)

See `docs/benchmark_phase2.md` / `datasets/evaluation/normalizer_phase2_latest.json`.

## Ethical considerations

- Mis-normalization can split time series or attach wrong explanations.
- Low-confidence matches return UNKNOWN / pass-through by design.
- Operators must not treat LOINC assignment as billable coding without review.

## Caveats

- Default offline backend is TF-IDF, not live ModernBERT weights.
- Product canonical spelling uses **Haemoglobin** (British) to match existing patterns/explainer.
