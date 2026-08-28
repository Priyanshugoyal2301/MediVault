# Benchmark — Phase 8 Document Image Quality

**Date:** 2026-08-11  
**Active backend:** MobileNetV3 (`mobilenet_v3`) — feature-head train by default; pixel train opt-in via `IMAGE_QUALITY_TRAIN_PIXELS=1`  
**Data:** Synthetic degraded lab pages  

## Headline (synthetic feature-head holdout)

| Backend | Subset Acc | F1 macro | Ready ROC-AUC |
|---------|------------|----------|---------------|
| MobileNetV3 | **0.92** | **0.95** | **1.0** |
| EfficientNet Lite0 | **0.92** | **0.95** | **1.0** |
| OpenCV rules | 0.00* | 0.25 | 0.64 |

\*OpenCV multi-label exact subset match is strict; still useful score heuristics.  
E2E assess ~27 ms (warm). Metrics are **synthetic** — not clinical scan cert.

## Failure analysis

1. Synthetic degradations ≠ real phone photos of lab sheets.  
2. Multi-label rare tags (e.g. multiple_pages) underrepresented in generator.  
3. Without torch, named MobileNet/EfficientNet paths use feature-ML proxy (still multi-label).  
4. PDF without pypdfium2 uses placeholder raster (quality may not reflect true page).

## Recommendations

1. Keep **`USE_IMAGE_QUALITY_MODEL=0`** until DocLayNet/PubLayNet bake-off.  
2. Install `torch`+`torchvision` (+ optional `pypdfium2`) for full CNN train.  
3. Product-copy: “Please upload a clearer image” when not OCR-ready.  
4. Do not surface clinical judgments from quality scores.

---

Regenerate: `python models/image_quality/evaluate.py`
