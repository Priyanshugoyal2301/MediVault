# Model Card — Document Image Quality (Phase 8)

| Field | Value |
|-------|-------|
| Name | ImageQualityEngine |
| Primary | MobileNetV3-Small |
| Fallback | EfficientNet Lite0 / B0 |
| Baseline | OpenCV rules |
| Flag | `USE_IMAGE_QUALITY_MODEL` (default off) |

## Intended use

Pre-OCR gate: is the lab report image suitable for OCR?

## Safety

Quality of scan only — not clinical content evaluation.
