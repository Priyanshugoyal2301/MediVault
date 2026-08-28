# models/anomaly_detection — ML Lab Anomaly Detection (Phase 7)

## Status

| Flag | Path |
|------|------|
| `USE_ANOMALY_MODEL=0` / `USE_OUTLIER_MODEL=0` (default) | Statistical monitor |
| either flag `=1` | Isolation Forest (+ LOF/Z available) with statistical fallback |

## Architectures

| Role | Model |
|------|-------|
| Primary | Isolation Forest |
| Fallback | Local Outlier Factor (LOF) |
| Baseline | Robust Z-Score |
| Future | Autoencoder / One-Class SVM **stubs** |

## Safety

Always: **"Anomalous laboratory pattern detected"** — never disease labels.

## Commands

```bash
python models/anomaly_detection/train.py
python models/anomaly_detection/evaluate.py
```
