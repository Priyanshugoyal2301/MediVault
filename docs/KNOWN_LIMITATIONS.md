# Known Limitations — Platform-Wide

1. **Synthetic primacy** — Phases 4–8 train largely on synthetic longitudinal / degraded data.  
2. **Non-diagnostic** — Risk, forecast, health score, anomaly outputs are informational.  
3. **OCR VLM** — Quality of Unlimited path depends on configured private endpoint / weights; not shipped.  
4. **Embedding HF** — Dense models optional; offline TF-IDF for air-gapped demos.  
5. **Intervals / confidence** — Often residual or heuristic; not rigorously conformal.  
6. **Single-series anomaly API** — Multi-marker profile scoring exists engine-side only.  
7. **Image quality** — Synthetic degradations; PDF raster optional (`pypdfium2`).  
8. **No public API expansion** — Many ML outputs registry-only by design.  
9. **Experiment tracking opt-in only** — No central tracking server in-repo.  
10. **Not medical device software** — Research / educational scaffolding.

See phase validation docs under `validation/model*-validation.md`.
