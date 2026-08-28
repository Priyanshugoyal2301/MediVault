# Architecture — Lab Anomaly Detection (Phase 7)

```
/anomaly/detect (unchanged schema)
  → get_anomaly_detector()
      flag off: StatisticalAnomalyDetector (z/CUSUM)
      flag on:  LabAnomalyEngine (Isolation Forest)
                → fallback StatisticalAnomalyDetector on error
```

### Sequence

```
Client → POST /anomaly/detect (stable body/response)
  → registry.get_anomaly_detector()
  → detect(test_name, series)
  → AnomalyDetectResponse (same fields)
```

No frontend changes.
