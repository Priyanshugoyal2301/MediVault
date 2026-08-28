# Model Card — Lab Anomaly Detection (Phase 7)

| Field | Value |
|-------|-------|
| Name | LabAnomalyEngine |
| Primary | Isolation Forest |
| Fallback | LOF |
| Baseline | Robust Z |
| Flags | `USE_ANOMALY_MODEL` / `USE_OUTLIER_MODEL` (default off) |

## Intended use

Unsupervised detection of unusual lab series / multi-marker patterns.

**Not** diagnosis.

## Data

Synthetic normal + injected anomalous profiles. NHANES/MIMIC optional offline.
