# Model Card — Unlimited-OCR (MediVault Phase 1 / 1A)

## Model details

| Field | Value |
|-------|-------|
| Name | Unlimited-OCR |
| Upstream | baidu/Unlimited-OCR (DeepSeek-OCR lineage) |
| License | See upstream HF/GitHub (MIT per project README) |
| MediVault role | Document understanding (PDF / PNG / JPG / TIFF multi-page) |
| Adapter | `models.ocr.infer.UnlimitedOCRParser` |
| Flag | `USE_UNLIMITED_OCR` |

## Intended use

- Transcribe medical **lab reports** to intermediate text / structured Medical JSON.  
- **Not** for diagnosis, risk scores, or treatment recommendations.

## Out-of-scope

- Clinical decision making  
- Identity verification  
- Handwriting primary pathology slides  

## Training data

Upstream model trained by Baidu (public report/weights). MediVault **does not** retrain in Phase 1.

## Evaluation data (MediVault)

- Plan C synthetic India-style fixtures (text proxy)  
- Metrics: field P/R/F1, exact match, missing/FP rates, runtime  

## Ethical considerations

- PHI must not be committed to `datasets/`.  
- Prefer self-hosted endpoint; avoid sending PHI to third-party cloud OCR without DPA.  
- Legacy fallback prevents silent empty vaults when model is down.

## Caveats

- Default flag **off**.  
- Surface test names without Phase 2 normalizer underperform regex on canonical gold.  
- Phase 1A: empty laboratory → treatment as failure → legacy; `auto` never loads multi-GB local weights.  
- Confidences stay internal (not on public `/parse` for BC).  
