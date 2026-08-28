# models/image_quality — Document Image Quality Assessment (Phase 8)

## Status

| Flag | Path |
|------|------|
| `USE_IMAGE_QUALITY_MODEL=0` (default) | Pass-through (always ok) |
| `USE_IMAGE_QUALITY_MODEL=1` | ML quality gate + OpenCV fallback |

## Architectures

| Role | Model |
|------|-------|
| Primary | MobileNetV3-Small (torchvision) or feature-ML proxy |
| Fallback | EfficientNet Lite0 / B0-compatible |
| Baseline | OpenCV / handcrafted rule checks |

## Commands

```bash
python models/image_quality/train.py
python models/image_quality/evaluate.py
```
