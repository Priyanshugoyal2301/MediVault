# Model Card — Document Image Quality

| Field | Value |
|-------|-------|
| Name | ImageQualityEngine |
| Phase | 8 |
| Primary | MobileNetV3-Small |
| Fallback | EfficientNet Lite0 / B0 |
| Baseline | OpenCV rule checks |
| Flag | `USE_IMAGE_QUALITY_MODEL` (default **off**) |

## Intended use

Pre-OCR suitability of uploaded lab report images/PDFs.

## Safety

Scan quality only — not clinical interpretation.
