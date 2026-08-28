# Benchmark Report — Phase 1 (Unlimited-OCR)

**Generated:** 2026-08-11  
**Artifact:** `datasets/evaluation/ocr_phase1_latest.json`  
**Command:** `python models/ocr/evaluate.py`

---

## 1. Setup

| Item | Value |
|------|-------|
| Fixtures | Plan C IE (`data/datasets/plan_c/ie_fixtures.py`) — 8 synthetic India-style texts |
| Legacy | `ReportParser` + passthrough text OCR |
| Unlimited path (offline) | Medical JSON **postprocess** on same text (simulates decoded VLM output) |
| Value tolerance | 0.051 |
| GPU weights | Not loaded in this benchmark (see Limitations) |

---

## 2. Performance

| Parser | n | latency_ms (batch) | avg_processing_time_ms | memory_mib | gpu_memory_mib |
|--------|---|--------------------|------------------------|------------|----------------|
| Legacy regex | 8 | 62.7 | 7.8 | ~0* | 0 |
| Unlimited postprocess | 8 | 62.7 | 7.8 | ~0* | 0 |

\*Trace of empty measure during aggregate; process-level RSS not instrumented on Windows for this run.

**Live VLM (not measured offline):** depends on `UNLIMITED_OCR_ENDPOINT` hardware; multi-page PDFs commonly multi-second to tens of seconds per report.

---

## 3. Accuracy

| Metric | Legacy | Unlimited postprocess |
|--------|--------|------------------------|
| Field precision | 0.95 | 0.156 |
| Field recall | 1.00 | 0.156 |
| Field F1 | **0.969** | 0.156 |
| Exact match (doc) | 0.875 | 0.125 |
| Missing field rate | 0.00 | 0.844 |
| False positive rate | 0.05 | 0.594 |
| OCR accuracy (text path) | 1.0 | 1.0 |
| Table accuracy | 1.0 | 0.156 |

---

## 4. Advantages (Unlimited-OCR path)

- End-to-end **vision → document text** without Tesseract language packs once VLM is deployed  
- Multi-page **one-shot** design (upstream R-SWA / long-horizon parsing)  
- Medical JSON with **page numbers**, optional **bounding boxes**, dual confidences  
- Hard **fallback** to regex preserves demos and production when VLM is cold/down  
- Feature flag allows zero-code switch

---

## 5. Limitations

- Offline bake-off evaluates **postprocess only**, not baidu/Unlimited-OCR decoding accuracy  
- Postprocess does **not** apply Phase 2 alias normalization → poor F1 vs canonical gold names  
- Local HF weights are large; default deploy remains lean (HTTP endpoint preferred)  
- No GPU instrumentation on Windows for this package without torch+CUDA  
- Deskew / rotation heuristics are best-effort, not a research-grade pipeline  

---

## 6. Failure cases

| Case | Behaviour |
|------|-----------|
| Empty file | `UnlimitedOCRError` → legacy fallback |
| No endpoint + no weights (`auto`) | Backend exhaust → fallback |
| Empty HTTP response (bad prompt) | Fallback |
| Unsupported MIME | Preprocess `ValueError` → fallback / empty values safety |
| Header-only rows / aliases | Extracted under surface names; miss gold canonical match |

---

## 7. Known issues

1. Canonical name mismatch until Phase 2 normalizer.  
2. True multi-page VLM text often returned as one blob; splitter is heuristic.  
3. Comma decimal Indian formats handled; rare compound units may need fix-ups.  
4. `USE_UNLIMITED_OCR=1` without server silently falls back — monitor `last_path` in logs.

---

## 8. Recommendations

1. Keep **`USE_UNLIMITED_OCR=0`** in prod until Hit@F1 ≥ legacy on a labeled **image** set after VLM warm.  
2. Deploy Unlimited-OCR behind **vLLM/SGLang** with official n-gram logits processor.  
3. Log `parser last_path` and disagreement rate (shadow mode) before cutover.  
4. Phase 2 should add **Normalizer** before treating Unlimited path as accuracy champion.  
5. Collect consented Indian lab scan gold for `datasets/document_parsing/`.

---

## 9. Verdict

| Goal | Status |
|------|--------|
| Integration benchmark complete | **Yes** |
| Ready as production default | **No** (legacy remains default) |
| Ready as experimental flag | **Yes** (with fallback) |
