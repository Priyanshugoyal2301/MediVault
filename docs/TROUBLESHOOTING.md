# Troubleshooting Guide (ML)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Flag change ignored | Process LRU registry cache | Restart ai-service / `reset_registry_cache()` in tests |
| Unlimited-OCR hangs | Local HF auto path | Keep `USE_UNLIMITED_OCR=0` or use HTTP endpoint; do not enable local weights without opt-in |
| Semantic retrieval slow first call | HF model download | `RETRIEVAL_ALLOW_HF=0` use offline TF-IDF; or pre-warm BGE |
| Risk/forecast/health return unavailable | Flag off (expected) | Enable corresponding `USE_*` only after review |
| Quality gate clears parse values | Flag on + poor image | Re-upload clearer image; or set flag off for demos |
| Torch pickle / train fail (image quality) | Stale artifacts | Re-run train; feature-head path is default |
| MLflow/W&B errors | Tracking env partial | `ML_EXPERIMENT_TRACKING=0` (default) |
| Import `services.ai_service` fails | Hyphen paths | Run from repo root with `conftest`/pytest |

## Health endpoint

`GET /health` → `ml_feature_flags` dumps current flag dict for ops verification.
