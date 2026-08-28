# Benchmark Report — Phase 1A (Hardening)

**Generated:** 2026-08-11  
**Scope:** Engineering metrics only (not IE accuracy improvements)  
**Artifact:** `datasets/evaluation/ocr_phase1a_bench.json`

## Setup

| Item | Value |
|------|-------|
| Host | Windows, Python 3.12 |
| VLM weights | Not loaded |
| Flag default | `USE_UNLIMITED_OCR=0` |

## Engineering performance

| Metric | Value (order of magnitude) | Meaning |
|--------|----------------------------|---------|
| Config load + validate | &lt; 50 ms | Fail-fast config OK |
| Readiness check | &lt; 20 ms | Startup health, no model load |
| Preprocess PNG ~800×600 | few–tens of ms | Deskew/contrast path |
| Fallback recovery (forced crash → legacy) | tens of ms | Failure recovery time |
| GPU memory | 0 | No GPU path exercised |
| Model loading time | N/A (blocked by design in auto) | Hang risk removed |

## Accuracy comparison

**Not re-scored for production cutover.** See Phase 1 bake-off:

| Path | Field F1 (Plan C text) |
|------|------------------------:|
| Legacy | ~0.97 |
| Unlimited postprocess | ~0.16 |

Phase 1A did **not** attempt to improve these numbers (out of scope).

## Failure recovery

| Scenario | Result |
|----------|--------|
| Backend unavailable | Fallback path, labs from legacy when possible |
| Empty structured OCR | Triggers legacy (O-07 fixed) |
| Auto without endpoint | Fast fail, no local HF hang (O-06 fixed) |

## Verdict

Engineering hardening benchmark **complete**. Unlimited remains experimental; default deploy path remains legacy-safe.
