# Current Pipeline (rule-based / statistical)

This document describes the **live production path** as of Phase 0 ML infrastructure.
All feature flags default **off**; behaviour matches the pre-interface system.

See also: [`ml-pipeline.md`](./ml-pipeline.md), [`ml-migration-plan.md`](./ml-migration-plan.md).

---

## 1. Report upload → structured values

```
User (UploadView)
  → POST /reports (BFF → health-service)
  → Magic-byte MIME check, size ≤ 20 MB
  → LocalStorage save under data/uploads/{owner_id}/...
  → Report row parsed_status=pending
  → BackgroundTasks: POST ai-service /parse
  → ai-service:
       1. resolve path inside STORAGE_LOCAL_PATH
       2. QualityChecker.check()          # PassThrough — always ok (default)
       3. DocumentParser (registry):
            USE_UNLIMITED_OCR=0 (default):
              RegexDocumentParser
                └─ TesseractBackend + ReportParser patterns
            USE_UNLIMITED_OCR=1:
              FallbackDocumentParser
                primary: UnlimitedOCRParser
                  preprocess → Unlimited-OCR client → Medical JSON
                  → map to ParsedValue
                on failure: RegexDocumentParser (legacy)
       4. explainer.explain() per value → status + EN/HI templates
  → health-service persists report_values + timeline_events
  → Frontend polls getReport until done
```

**Demo path:** CBC/Lipid seed buttons write deterministic values **without** OCR.

### Key files

| Step | Path |
|------|------|
| Upload API | `services/health-service/routers/reports.py` |
| Parse route | `services/ai-service/routers/parse.py` |
| Registry | `services/ai-service/core/registry.py` |
| Legacy OCR | `services/ai-service/ocr/tesseract_backend.py` |
| Legacy IE | `services/ai-service/parsers/report_parser.py` |
| Unlimited-OCR | `models/ocr/` |
| Adapters | `services/ai-service/adapters/document_parser.py` |
| Explain | `services/ai-service/explainer/` |

---

## 2. Timeline + trend / anomaly

```
User (TimelineView)
  → GET /timeline
  → GET /timeline/{test_name}/anomaly
  → health loads owner-scoped series
  → POST ai-service /anomaly/detect
       data_points: [{date, value}, ...]
  → AnomalyDetector.detect()  # StatisticalAnomalyDetector
       compute_zscore → trend + whole-series z
       score_anomaly → causal leave-last-out z ∨ CUSUM
       bilingual summary (non-diagnostic tone)
  → AnomalyAnalysisOut + history to UI
```

### Key files

| Step | Path |
|------|------|
| Timeline API | `services/health-service/routers/timeline.py` |
| Anomaly route | `services/ai-service/routers/anomaly.py` |
| Detector | `services/ai-service/anomaly/detector.py` |
| Statistical model | `services/ai-service/anomaly/model.py` |
| Z-score trend | `services/ai-service/anomaly/zscore.py` |

---

## 3. Evidence Q&A

```
User (QAChatView)
  → POST /qa (BFF → health)
  → Load owner report_values (limit 50)
  → POST ai-service /qa with user_report_values + X-User-Id
  → STEP 1 (mandatory): check_safety(question)
       if red-flag → fixed emergency EN/HI, no RAG
  → STEP 2: Retriever.retrieve()  # BM25Retriever → rag.retrieve
       BM25 + intent boost over data/knowledge-base/
       optional hybrid if embeddings warmed
       keyword match against user values
  → STEP 3: synthesize templates + citations
  → QAResponse { answer, answer_hi, citations, safety_triggered }
```

### Key files

| Step | Path |
|------|------|
| QA proxy | `services/health-service/routers/qa.py` |
| QA route | `services/ai-service/routers/qa.py` |
| Safety | `services/ai-service/safety/red_flags.py` |
| BM25 | `services/ai-service/rag/bm25.py` |
| Retriever | `services/ai-service/rag/retriever.py` |
| Bootstrap | `services/ai-service/rag/bootstrap.py` |
| Synthesizer | `services/ai-service/rag/synthesizer.py` |
| KB corpus | `data/knowledge-base/*.txt` |

---

## 4. Auth boundary

```
Browser → BFF require_user_id (JWT)
  BFF strips any client X-User-ID
  BFF injects trusted sub as X-User-ID → health
  health never trusts body owner_id for ownership
  repositories filter by owner_id (DB + ScopedRepository)
```

---

## 5. What is *not* in the current **default** live path

| Feature | Status |
|---------|--------|
| Unlimited-OCR as default | Flag **off**; enable with `USE_UNLIMITED_OCR=1` + endpoint/weights |
| Cloud OCR required | Prefer self-hosted vLLM/SGLang; optional HTTP |
| ML normalizer model | Alias table only (Phase 2) |
| Learned anomaly model | Statistical monitor only |
| Risk score product surface | Interface + unavailable adapter |
| Aggregate health score | Interface + unavailable adapter |
| Image quality ML gate | Pass-through |
| pgvector live retrieval | Schema-ready; not used by default QA |
| Free-form LLM chatbot | Explicitly excluded from MVP |

---

## 6. Frontend mapping

| View | Primary APIs | Backend intelligence |
|------|--------------|----------------------|
| `DashboardView` | reports list, timeline summary | counts only |
| `UploadView` | upload, poll, demo seed | OCR+IE+explain |
| `TimelineView` | timeline, anomaly | trend + anomaly |
| `QAChatView` | askQuestion | safety + BM25 + templates |

Client: `apps/web/src/api.js` — **no** direct AI service calls.
