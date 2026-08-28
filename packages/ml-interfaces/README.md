# ml-interfaces

Protocol contracts for MediVault's ML-swappable components.

| Protocol | Default adapter (ai-service) | Feature flag |
|----------|------------------------------|--------------|
| `DocumentParser` | Regex + Tesseract `ReportParser` | `USE_UNLIMITED_OCR` (OCR stage) |
| `Normalizer` | Alias / unit table | `USE_ML_NORMALIZER` |
| `AnomalyDetector` | Statistical monitor + z-score | `USE_ANOMALY_MODEL` / `USE_OUTLIER_MODEL` |
| `Retriever` | BM25 + intent | `USE_EMBEDDING_SEARCH` |
| `RiskPredictor` | Unavailable (no-op) | `USE_RISK_MODEL` |
| `BiomarkerForecaster` | Unavailable (no-op) | `USE_FORECAST_MODEL` |
| `HealthScorer` | Unavailable (no-op) | `USE_HEALTH_SCORE_MODEL` |
| `QualityChecker` | Pass-through (always ok) | `USE_IMAGE_QUALITY_MODEL` |

Runtime selection lives in `services/ai-service/core/registry.py`.
Do **not** import model weights from this package — only contracts and DTOs.
