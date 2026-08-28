# MediVault AI — ML Migration Plan

> **Phase 0 (this document):** prepare infrastructure without breaking the live product.  
> **Do not** remove rule-based code, change public APIs, or ship unvalidated models.  
> Companion docs: [`ml-pipeline.md`](./ml-pipeline.md), [`current-pipeline.md`](./current-pipeline.md).  
> Authoritative product facts: [`../BIBLE.md`](../BIBLE.md).

**Status:** Phase 0 + 1 OCR + 1A + **Phase 2 Medical Test Normalizer** (flag default **off**).  
**Date:** 2026-08-11 (Phase 2 complete)

### Phase 2 delta (test name normalization)

| Capability | Implementation | Flag |
|------------|----------------|------|
| Rule aliases | `AliasNormalizer` (never removed) | default |
| ML normalizer | `MedicalTestNormalizer` + LOINC + confidence | `USE_ML_NORMALIZER` |
| Apply site | `services/ai-service/routers/parse.py` post-extract | always via `get_normalizer()` |

See `validation/model2-validation.md`, `docs/benchmark_phase2.md`, `phase2-summary.md`.


### Phase 1 delta (document understanding)

| Capability | Implementation | Flag |
|------------|----------------|------|
| Unlimited-OCR path | `models/ocr` → preprocess → client → Medical JSON → ParsedValue | `USE_UNLIMITED_OCR` |
| Legacy OCR+IE | Tesseract/pdfplumber + regex (unchanged, production default) | always |

### Phase 1A delta (engineering)

| Fix | Observation |
|-----|-------------|
| Empty/malformed/timeout → legacy | O-07 |
| `auto` never loads local HF | O-06 |
| Config/readiness/logs/tests/docs | O-08, O-10, O-12 |

See `validation/model1a-validation.md`, `docs/phase1a-observation-review.md`, `docs/benchmark_phase1a.md`.

---

## 1. Executive summary

MediVault is a **microservices** health vault (auth / health / AI + React BFF) whose “intelligence” is currently:

| Capability | Implementation | Honest ML claim |
|------------|----------------|-----------------|
| OCR | pdfplumber text layer → Tesseract eng+hin | Engine, not a trained model |
| Report extraction | Regex `ALL_PATTERNS` (CBC, lipid, thyroid, HbA1c) | Rule IE; Plan C IE F1 ~0.97 on fixtures |
| Test normalization | Canonical names inside patterns + alias table | Rule-based |
| Explanations | Template + ref-range status | Deterministic, non-diagnostic |
| Trend / anomaly | Z-score + causal-z / CUSUM statistical monitor | Not IsolationForest / not DL |
| Risk / health score | **Not productized** (interfaces reserved) | N/A |
| Retrieval | BM25 + intent (+ optional MiniLM hybrid) | Sparse IR by default |
| Safety | Red-flag regex **before** RAG | Non-negotiable gate |

This plan migrates each component to **ML-swappable interfaces** behind feature flags, with **rule-based defaults** until evaluation gates pass.

---

## 2. Current architecture

### 2.1 Service graph

```
Browser (apps/web :3000)
    │  JWT only — never X-User-ID
    ▼
BFF apps/api :8000
    ├─ /auth/*        → auth-service :8001
    ├─ /reports*      → health-service :8002
    ├─ /timeline*     → health-service :8002
    └─ /qa*           → health-service :8002
                              │
                              │  X-User-ID (trusted) + X-Internal-Key
                              ▼
                        ai-service :8003  (internal; not browser-facing)
                              │
                    OCR │ Parse │ Anomaly │ QA │ Embed
```

### 2.2 Component ownership (audit)

| Concern | Primary code | Called by | Frontend consumer |
|---------|--------------|-----------|-------------------|
| **OCR** | `services/ai-service/ocr/tesseract_backend.py` (`OcrBackend` Protocol exists) | `ReportParser` / `RegexDocumentParser` | Indirect: UploadView poll |
| **Regex parsing / IE** | `parsers/patterns.py`, `parsers/report_parser.py` | `POST /parse` | UploadView / Report detail |
| **Report extraction pipeline** | `routers/parse.py` | health `BackgroundTasks` after upload | UploadView |
| **Test normalization** | Canonical names in patterns; `adapters/normalizer.py` (new) | Future IE post-pass; registry | None (internal) |
| **BM25 retrieval** | `rag/bm25.py`, `rag/retriever.py` | `POST /qa` | QAChatView |
| **Dense retrieval (optional)** | `rag/embedder.py`, bootstrap hybrid | Flag-gated | Same QA path |
| **Trend analysis** | `anomaly/zscore.py` | `anomaly/detector.py` | TimelineView anomaly |
| **Risk analysis** | *Interface only* (`RiskPredictor`) — no live API | Registry (unused by routes) | None |
| **Anomaly / outlier** | `anomaly/model.py` + `detector.py` | `POST /anomaly/detect` | TimelineView |
| **Health score** | *Interface only* (`HealthScorer`) | Registry (unused by routes) | None |
| **Explanations** | `explainer/explainer.py` + `templates.py` | `/parse` response → DB columns | Upload / report views |
| **Safety** | `safety/red_flags.py` | `/qa` first step | QAChatView (`safety_triggered`) |
| **Database schema** | Alembic `001–004`; models in health/auth services | health + auth | Via BFF JSON |
| **API routes** | See §2.4 | BFF proxy | `apps/web/src/api.js` |
| **Frontend consumers** | Dashboard, Upload, Timeline, QAChat | BFF only | — |

### 2.3 Dependency graph

```
                    ┌──────────── apps/web ────────────┐
                    │ api.js → BFF :8000 only         │
                    └───────────────┬──────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │     apps/api      │
                          │ JWT + strip client│
                          │ X-User-ID; reinject│
                          └──┬───────┬───────┘
               auth-service  │       │  health-service
                  users/JWT  │       │  reports, timeline, qa proxy
                             │       │         │
                             │       │    storage (local)
                             │       │         │
                             │       │    background /parse
                             │       │         │
                             │       └────► ai-service
                             │                 │
        Postgres (users, reports,              ├── DocumentParser (OCR+IE)
         report_values, timeline,              ├── Explainer templates
         qa_* tables, pgvector ready)            ├── AnomalyDetector
                                                 ├── Retriever (BM25)
                                                 └── Safety gate

   packages/shared-utils (redacting logger)
   packages/shared-types (Locale etc.)
   packages/ml-interfaces (Protocols — NEW)
   packages/ml-eval (evaluation harness — NEW)
```

### 2.4 API surface (unchanged by Phase 0)

| Entry | Path | Owner |
|-------|------|-------|
| Public | `POST /auth/register`, `/login`, `GET /me` | BFF → auth |
| Public | `POST/GET/DELETE /reports*`, demo seed | BFF → health |
| Public | `GET /timeline*`, `/timeline/{test}/anomaly` | BFF → health → AI anomaly |
| Public | `POST /qa` | BFF → health → AI qa |
| Internal | `POST /parse`, `/anomaly/detect`, `/qa`, embed | ai-service |

**Constraint:** Phase 0 must not change request/response shapes consumed by `apps/web`.

### 2.5 Database (current)

- `users` (001)  
- `reports`, `report_values`, `timeline_events` (002)  
- Q&A / knowledge tables (003)  
- `explanation_en` / `explanation_hi` on `report_values` (004)  
- pgvector image ready; **live QA uses in-memory BM25**, not durable vector search  

No schema migration is required for Phase 0 interfaces/flags.

---

## 3. Target architecture

```
Upload / image
  → [QualityChecker]          # passthrough today; ML later
  → [OcrBackend / DocumentParser]  # Tesseract or Unlimited OCR
  → [Normalizer]              # aliases → canonical
  → Explainer (templates; LLM optional later behind same tone rules)
  → Postgres report_values + timeline_events

Timeline metric series
  → [AnomalyDetector]         # statistical or learned outlier
  → (future) [RiskPredictor] / [HealthScorer]  # new endpoints only after validation

Q&A
  → Safety (always first; never ML-gated away)
  → [Retriever] BM25 or embedding hybrid
  → Template synthesizer (+ future constrained gen)
```

**Design principles**

1. **Interfaces first** — `packages/ml-interfaces` Protocols.  
2. **Adapters wrap old code** — `services/ai-service/adapters/*`.  
3. **Registry + flags** — `core/registry.py` + `USE_*` env vars.  
4. **Fail closed to baseline** — if ML flag on but model missing, use rule/stats path.  
5. **Eval gate before cutover** — `packages/ml-eval` + `models/*/evaluate.py`.  
6. **Safety & tone immutable** — red flags and non-diagnostic language remain code.

---

## 4. Replacement order

Recommended sequence balances **user-visible value**, **labelability of data**, and **blast radius**.

| Phase | Flag | Component | Why this order | Prerequisite |
|-------|------|-----------|----------------|--------------|
| **0** | — | Interfaces, flags, folders, eval harness | Done | — |
| **1** | `USE_UNLIMITED_OCR` | Unlimited-OCR + Medical JSON + fallback | **Done (default off)** | Endpoint/weights for live VLM |
| **1A** | (same) | Fallback/backend/logging/tests hardened | **Done** | ops bake-off / cutover gates |
| **2** | `USE_ML_NORMALIZER` | Normalizer (rules + ML) | **Done (default off)** | staging bake with Unlimited |
| **3** | `USE_EMBEDDING_SEARCH` | SemanticRetriever + FAISS (+ BM25 fallback) | **Done (default off)** | HF BGE warm path |
| **4** | `USE_RISK_MODEL` | Disease risk (multi-condition) | **Done (default off)** | Clinical data + review |
| **5** | `USE_FORECAST_MODEL` | Biomarker forecasting | **Done (default off)** | Longitudinal corpus + review |
| **6** | `USE_HEALTH_SCORE_MODEL` | Health score + SHAP | **Done (default off)** | Labeled orientation scores + review |
| **7** | `USE_ANOMALY_MODEL` | Lab anomaly (Isolation Forest) | **Done (default off)** | Real series FAR control |
| **8** | `USE_IMAGE_QUALITY_MODEL` | Document image quality | **Done (default off) — final ML phase** | DocLayNet / real phones |

**Do not** order risk/health score before OCR/IE/anomaly foundations.

---

## 5. Rollback strategy

| Layer | Mechanism | RTO |
|-------|-----------|-----|
| Single model flag | Set `USE_*=0` in env / redeploy ai-service | Minutes |
| Multiple flags | Restore previous `.env` snapshot | Minutes |
| Bad adapter code | Revert registry registration; default adapters remain | Deploy cycle |
| Schema | Phase 0 adds **no** migrations; later additive-only columns | N/A now |
| Frontend | Unchanged APIs → no FE rollback needed | — |
| Data | Keep writing same `report_values` shape; models don't mutate history | — |

**Rule:** Prefer flag-off over hot binary rollback. Statistical/BM25/Tesseract paths stay in-tree forever until a formal deprecation ADR.

**Shadow mode (recommended before 100% cutover):**  
Log ML vs baseline disagreement rates; never block the user on ML-only failures in phase 1–4.

---

## 6. Validation checkpoints

Before enabling a flag in any shared environment:

### 6.1 Universal gates (every model)

From `packages/ml-eval.EvaluationReport`:

| Metric | Reported | Gate (initial) |
|--------|----------|----------------|
| Precision | required | Meet or beat baseline ± tolerance |
| Recall | required | Meet or beat baseline ± tolerance |
| F1 | required | Primary compare key |
| Accuracy | required | Secondary |
| Latency (ms) | required | ≤ 2× baseline p95 or SLO in BIBLE |
| Model size (bytes) | required | Fit service memory budget |
| Memory (MiB) | required | Fit container limits |
| Inference time (ms/example) | required | p95 budget |

### 6.2 Component-specific gates

| Model | Primary offline metrics | Live canary | Safety |
|-------|-------------------------|-------------|--------|
| Quality | Precision on “OCR-viable” labels | Reject rate < 5% false reject on seed PDFs | No PHI logs |
| Normalizer | Accuracy on alias fixtures | Diff rate vs regex canonicals | — |
| Retrieval | Hit@5, MRR vs Plan B BM25 | Latency; citation presence | Safety still first |
| Anomaly | F1 / FAR on synth + gradual-drift set | Method field still honest | Tone tests |
| OCR | CER/WER vs gold; IE F1 post-OCR | Demo seed still exact | Local-only engines preferred |
| Risk / health | Calibration + clinical review checklist | Feature default off | Never diagnostic language |

### 6.3 Product regression

- Unit: `tests/unit/ai-service/*`, health, auth  
- Demo preflight: `scripts/demo_preflight.ps1`, `scripts/smoke_demo.ps1`  
- Manual: upload demo CBC/lipid seed, timeline ≥3 points, QA citation + red-flag  

---

## 7. Risk assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Silent behaviour change under flag default | High | Low (defaults off) | Defaults False; registry fallbacks |
| Latency regression (OCR/embeddings) | Medium | Medium | Latency gates; FAST_KB remains default |
| False anomalies / alarm tone | High | Medium | Tone tests; FAR budget; soft language |
| PHI in datasets/logs | Critical | Medium | `.gitignore` datasets content; redacting logger; no cloud OCR by default |
| Overclaimed “ML diagnoses” | Critical | Medium | ADR + PRESENTATION_CLAIMS discipline |
| pgvector unused while marketing dense RAG | Low | High today | Honest flags; USE_EMBEDDING_SEARCH only when warm |
| Integration test gap | Medium | High | Add integration tests before phase 5 |

---

## 8. Success metrics

### Phase 0 (infrastructure) — exit criteria

- [x] Interfaces for all planned components  
- [x] Feature flags documented and default off  
- [x] `datasets/` + `models/` scaffolds  
- [x] Evaluation framework with required metric keys  
- [x] Migration + pipeline docs  
- [x] Live path still uses rule/stats defaults  
- [ ] Unit tests green after wiring (run in CI)  

### Later product success (post-model)

| Metric | Target direction |
|--------|------------------|
| IE F1 on real Indian lab scans | ≥ regex baseline |
| Anomaly FAR on stable synthetic series | ≤ statistical monitor |
| QA Hit@5 | ≥ BM25 baseline |
| p95 parse latency | Within agreed SLO |
| Zero safety bypass incidents | Absolute |

---

## 9. Folder map (new)

```
MediVault/
  packages/ml-interfaces/     # Protocols + DTOs
  packages/ml-eval/           # Metrics + EvaluationReport
  services/ai-service/
    adapters/                 # Default implementations
    core/feature_flags.py
    core/registry.py
  datasets/                   # Offline data (empty layout; no download yet)
  models/{ocr,risk,...}/      # train/evaluate/infer/config scaffolds
  docs/ml-migration-plan.md   # this file
  docs/current-pipeline.md
  docs/ml-pipeline.md
```

Note: existing offline lab code remains at `data/datasets/` (Plan C). New `datasets/` is the **ML migration** layout; do not delete `data/datasets/`.

---

## 10. Explicit non-goals (Phase 0)

- Training or downloading models  
- Replacing IsolationForest-era claims with new vanity benches  
- Changing frontend contracts  
- Enabling any `USE_*=1` in production compose defaults  
- Removing Tesseract, regex patterns, BM25, or statistical monitor  

---

## 11. Next phase recommendation

See end of repo readiness report: **Phase 1 — Image quality + normalizer datasets and baseline eval runners wired to Plan C fixtures.**
