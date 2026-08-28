# Phase 8 — Image quality validation

**Verdict: PASS WITH OBSERVATIONS**

Date: 2026-08-11

## Checklist

| Item | Result |
|------|--------|
| MobileNetV3 operational | ✓ (`create_backend` + train `mobilenet_v3`) |
| EfficientNet fallback operational | ✓ |
| OpenCV baseline operational | ✓ |
| Feature flag operational | ✓ default passthrough |
| APIs unchanged | ✓ `/parse` already calls quality; schema same |
| Frontend unchanged | ✓ |
| OCR unaffected at default | ✓ flag off → always ok |
| Benchmarks | ✓ |
| Tests | ✓ `tests/phase8` (16) |
| No regressions | ✓ |

## Observations

| ID | Severity | Note |
|----|----------|------|
| **O-01** | Medium | Synthetic data only; DocLayNet/PubLayNet/RVL-CDIP not shipped. |
| **O-02** | Low | Default train uses picklable feature head on MobileNet-named backend; pixel CNN via `IMAGE_QUALITY_TRAIN_PIXELS=1`. |
| **O-03** | Low | When flag on, `ok=False` returns empty parse values (existing soft fail). |
| **O-04** | Info | PDF rasterization best with optional pypdfium2. |

## Gate decision

**PASS WITH OBSERVATIONS**

This is the **final ML implementation phase** per charter — do not start further phases unless newly scoped.
