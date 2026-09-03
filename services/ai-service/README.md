# AI Service — `services/ai-service`

## What this service owns

- **Report parsing** — OCR + structured value extraction from PDF/image reports  
  - **Default:** Tesseract/pdfplumber + regex IE  
  - **Optional (Phase 1):** Unlimited-OCR → Medical JSON when `USE_UNLIMITED_OCR=1` (legacy fallback always available)
- **Anomaly detection** — z-score trend + causal statistical monitor (causal z / %Δ / CUSUM)
- **RAG Q&A** — BM25+intent retrieval + template synthesizer with citations
- **Deterministic safety layer** — regex red-flag check BEFORE retrieval/synthesis

## Tech (Plan B + Phase 0 ML scaffolding)

FastAPI + pdfplumber/pytesseract (OCR) + pure-Python BM25 + statistical monitor (stdlib).  
Optional: sentence-transformers MiniLM when `MEDIVAULT_USE_DENSE=1` / `USE_EMBEDDING_SEARCH=1`.

ML-swappable components use `packages/ml-interfaces` Protocols and resolve via
`core/registry.py` + feature flags (all **default off**). Defaults wrap the existing
rule/stats implementations — no behaviour change until models are validated.
See `docs/ml-migration-plan.md`.

## Critical safety rule

The deterministic safety layer MUST run before RAG on `/qa`. If a red-flag triggers, return the fixed emergency message immediately.

## API contract

| Method | Path | Description |
|---|---|---|
| `POST` | `/parse` | Quality check → DocumentParser → explain |
| `POST` | `/anomaly/detect` | AnomalyDetector (statistical default) |
| `POST` | `/qa` | Safety → Retriever → template answer |
| `POST` | `/embeddings/embed-report` | Stub vector write path |
| `DELETE` | `/embeddings/{owner_id}/{report_id}` | Stub delete |
| `GET` | `/health` | KB stats + `ml_feature_flags` |

## Running locally

```bash
cd services/ai-service
pip install -r requirements.txt
# from repo root with PYTHONPATH=.
uvicorn services.ai_service.main:app --reload --port 8003
```

Set `MEDIVAULT_FAST_KB=1` (default) for BM25-only demo boot.

### Unlimited-OCR (Phase 1)

```bash
# defaults remain safe for demos
USE_UNLIMITED_OCR=0

# experiment (requires endpoint or local weights; fails over to legacy)
USE_UNLIMITED_OCR=1
UNLIMITED_OCR_BACKEND=http
UNLIMITED_OCR_ENDPOINT=http://127.0.0.1:30000/v1/chat/completions
```

See `models/ocr/README.md` and `docs/model-cards/unlimited-ocr.md`.
