# Future ML Pipeline & Plug-in Guide

How trained models attach to MediVault without rewriting APIs or the frontend.

Companions: [`current-pipeline.md`](./current-pipeline.md), [`ml-migration-plan.md`](./ml-migration-plan.md).

---

## 1. Design

```
                    Feature flags (USE_*)
                            │
                    core/registry.py
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   Default adapter    (future) ML adapter   Fallback
   (rule / stats)     models/*/artifacts    → default
         │                  │                  │
         └──────────────────┴──────────────────┘
                            │
                     Protocol methods
                   packages/ml-interfaces
                            │
                    routers (stable JSON)
```

**Rules**

1. Routers depend on **registry getters**, not on sklearn/torch imports.  
2. ML adapters implement the same Protocol as defaults.  
3. Missing weights / load errors → **log + use default**.  
4. Safety layer is **not** behind a quality/risk flag; it always runs first on `/qa`.  
5. Never change public BFF response schemas to “ship” a model.

---

## 2. Interfaces ↔ flags ↔ folders

| Protocol | Flag | Default adapter | Model folder | Dataset folder |
|----------|------|-----------------|--------------|----------------|
| `DocumentParser` (+ OCR) | `USE_UNLIMITED_OCR` | `RegexDocumentParser` | `models/ocr/` | `datasets/document_parsing/` |
| `Normalizer` | `USE_ML_NORMALIZER` | `AliasNormalizer` | `models/normalizer/` | `datasets/test_normalization/` |
| `QualityChecker` | `USE_IMAGE_QUALITY_MODEL` | `PassThroughQualityChecker` | `models/image_quality/` | `datasets/image_quality/` |
| `AnomalyDetector` | `USE_ANOMALY_MODEL` / `USE_OUTLIER_MODEL` | `StatisticalAnomalyDetector` | `models/anomaly_detection/` | `datasets/anomaly_detection/` |
| `Retriever` | `USE_EMBEDDING_SEARCH` | `BM25Retriever` | `models/retrieval/` | `datasets/retrieval/` |
| `RiskPredictor` | `USE_RISK_MODEL` | `UnavailableRiskPredictor` | `models/risk_prediction/` | `datasets/risk_prediction/` |
| `BiomarkerForecaster` | `USE_FORECAST_MODEL` | `UnavailableBiomarkerForecaster` | `models/forecasting/` | `datasets/forecasting/` |
| `HealthScorer` | `USE_HEALTH_SCORE_MODEL` | `UnavailableHealthScorer` | `models/health_score/` | `datasets/health_score/` |

Environment template: `.env.example`.  
Runtime dump: `GET ai-service /health` → `ml_feature_flags`.

---

## 3. How each model plugs in

### 3.1 OCR / document parsing (Phase 1 — implemented)

1. Prefer HTTP endpoint (`UNLIMITED_OCR_ENDPOINT`); **do not** rely on `auto` for local HF (Phase 1A).  
2. Set `USE_UNLIMITED_OCR=1` (restart ai-service).  
3. Registry validates config + builds `FallbackDocumentParser(Unlimited, Regex)`.  
4. Preprocess → Unlimited-OCR → Medical JSON → map to existing `ParsedValue` for `/parse`.  
5. On crash/timeout/malformed/empty labs → **legacy** (O-07). Local weights need explicit allow flags.

Details: `models/ocr/README.md`, `docs/model-cards/unlimited-ocr.md`, `docs/CONFIGURATION.md`, `phase1a-summary.md`.

Evaluation:

```bash
python models/ocr/evaluate.py
```

### 3.2 Image quality

1. Binary or multi-label model in `models/quality/`.  
2. Adapter returns `QualityCheckResult(ok=..., score=..., reasons=...)`.  
3. `/parse` already calls `get_quality_checker().check()`; if `ok` is False it returns empty values (fail soft). Consider future health-service status `failed` with reason **only after** product decision (API impact).

### 3.3 Normalizer (Phase 2 — implemented)

1. Train offline: `python models/normalizer/train.py` (default `char_tfidf`).  
2. Optionally set `NORMALIZER_BACKEND=modernbert` + `NORMALIZER_ALLOW_HF=1`.  
3. Set `USE_ML_NORMALIZER=1` and restart ai-service.  
4. `/parse` calls `get_normalizer().normalize_test_name` after document parse.  
5. Flag off → `AliasNormalizer` only (legacy never deleted).

Details: `models/normalizer/README.md`, `docs/model-cards/medical-test-normalizer.md`.


### 3.4 Anomaly / outlier

1. Train model for short personal series under `models/anomaly/`.  
2. Adapter must return full bilingual summaries **or** call existing `_build_summaries` to keep tone.  
3. Prefer ML only for `is_anomaly` / score; reuse templates for language.  
4. Gate FAR ≤ statistical baseline on gradual-drift synth.

### 3.5 Retrieval / embeddings (Phase 3 — implemented)

1. Build index: `python models/retrieval/train.py`.  
2. Set `USE_EMBEDDING_SEARCH=1` (restart ai-service).  
3. Registry returns `FallbackRetriever(SemanticRetrieverAdapter, BM25Retriever)`.  
4. Compare BM25 vs semantic via `python models/retrieval/evaluate.py`.  
5. Flag off → pure BM25 forever (never deleted).

Details: `models/retrieval/README.md`, `docs/model-cards/semantic-retriever.md`.

### 3.6 Risk & health score (new surfaces)

1. Keep defaults returning `unavailable`.  
2. **Do not** overload existing timeline/anomaly fields.  
3. Add new health-service endpoints later, still behind BFF auth.  
4. Templates must pass tone scrub (no “you have disease X”).

---

## 4. Training & evaluation loop

```
datasets/{task}/raw|labels
        │
        ▼
 models/{task}/train.py --config config.yaml
        │
        ▼
 models/{task}/artifacts/
        │
        ▼
 models/{task}/evaluate.py
        │  uses packages.ml_eval
        ▼
 datasets/evaluation/{task}_latest.json
        │
        ▼  human review + gates
 registry registration + flag on staged env
```

Required report keys:

- `precision`, `recall`, `f1`, `accuracy`  
- `latency_ms`, `model_size_bytes`, `memory_mib`, `inference_time_ms`  

---

## 5. Future end-to-end ML-first path (target)

```
Upload
  → QualityChecker(ML)
  → UnlimitedOCR / layout model
  → Sequence IE model + Normalizer(ML)
  → Explainer (templates or constrained gen)
  → optional RiskPredictor / HealthScorer (non-dx)

Timeline
  → AnomalyDetector(ML) with template summaries

Q&A
  → Safety (rules, always)
  → Hybrid Retriever (BM25 + dense)
  → Synthesizer (templates first; gen only if constrained + cited)
```

Until each step is gated, **partial ML** is expected (e.g. quality ML + regex IE).

---

## 6. Safety & compliance checklist (every model PR)

- [ ] No PHI in committed datasets  
- [ ] Redacting logger used on any new service logs  
- [ ] Safety gate still first on `/qa`  
- [ ] Tone unit tests green  
- [ ] Feature flag default remains `0`  
- [ ] Rollback documented (flag off)  
- [ ] Claims updated in `PRESENTATION_CLAIMS.md` / research site  

---

## 7. Developer quick reference

```bash
# Inspect flags (with ai-service running)
curl http://127.0.0.1:8003/health

# Scaffold eval for a model area
python models/anomaly/evaluate.py

# Unit tests (still must pass with all flags off)
pytest tests/unit/ai-service -q
```

Import interfaces:

```python
from packages.ml_interfaces import DocumentParser, AnomalyDetector, Retriever
from packages.ml_eval import EvaluationRunner, EvaluationReport
```
