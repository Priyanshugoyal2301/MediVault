# models/ocr — Unlimited-OCR document understanding (Phase 1 + 1A)

## Status

**Phase 1 integrated; Phase 1A hardened.** Production default remains legacy.

| Flag | Path |
|------|------|
| `USE_UNLIMITED_OCR=0` (default) | Legacy Tesseract + regex `ReportParser` |
| `USE_UNLIMITED_OCR=1` | Unlimited-OCR pipeline → Medical JSON → API mapping; **auto-fallback to legacy on failure/empty/timeout** |

See `docs/CONFIGURATION.md`, `docs/phase1a-observation-review.md`.

## Model

Upstream: [baidu/Unlimited-OCR](https://huggingface.co/baidu/Unlimited-OCR) (VLM document parsing).

MediVault does **not** vendor multi-GB weights. Operators supply:

1. **HTTP** (recommended): SGLang/vLLM OpenAI-compatible endpoint  
   `UNLIMITED_OCR_ENDPOINT=http://host:port/v1/chat/completions`  
   Prompt recipe: leading space + `" document parsing."` / `" Multi page parsing."`  
   Custom n-gram logits processor required on the server (see model card).

2. **Backend `auto` (Phase 1A):** HTTP **only** if endpoint is set. **Never** auto-selects local HF weights (prevents hang/OOM).

3. **Local (explicit):** `UNLIMITED_OCR_BACKEND=local` **and** `UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS=1`.  
   Downloads require `UNLIMITED_OCR_ALLOW_LOCAL_DOWNLOAD=1`; otherwise `local_files_only=True`.

4. **Stub**: `UNLIMITED_OCR_BACKEND=stub` for offline smoke tests (Tesseract or injected stub text).

## Pipeline

```
PDF/PNG/JPG/JPEG/TIFF
  → preprocess (page extract, deskew, contrast, denoise, resize)
  → Unlimited-OCR client
  → postprocess → Medical JSON
  → map to CompatibilityLabValue / ParsedValue (unchanged /parse API)
```

Empty laboratory list is treated as failure → legacy (Phase 1A / O-07).

Medical JSON shape:

```json
{
  "patient": {},
  "laboratory": [
    {
      "test_name": "...",
      "value": 13.5,
      "unit": "g/dL",
      "reference_range": "12.0–17.0",
      "flag": null,
      "page_number": 1,
      "bounding_box": null,
      "ocr_confidence": 0.9,
      "extraction_confidence": 0.8
    }
  ],
  "metadata": {},
  "confidence": {}
}
```

## Scripts

| File | Purpose |
|------|---------|
| `infer.py` | `UnlimitedOCRParser` |
| `evaluate.py` | Legacy vs Unlimited bake-off |
| `train.py` | Scaffold (no training in Phase 1) |
| `preprocess.py` | Document image prep |
| `postprocess.py` | Medical JSON builder |
| `dataset.py` | Dataset catalog infrastructure |
| `metrics.py` | Field F1 / runtime metrics |
| `client.py` | HTTP / local / stub backends |
| `schema.py` | Medical JSON dataclasses |

## Evaluation

```bash
# from repo root
python models/ocr/evaluate.py
```

Writes `datasets/evaluation/ocr_phase1_latest.json`.

## Safety

- Never throws away the legacy parser — outer adapter falls back.
- No API contract changes.
- No hardcoded clinical reference values invented by the model path.
- Config validates at startup when flag is on; `/health` exposes Unlimited readiness.
- Logging: backend, duration, fallback, confidence when present, failure reason.
