# AI Service — `services/ai-service`

## What this service owns

- **Report parsing** — OCR + structured value extraction from PDF/image reports (Feature 1)
- **Anomaly detection** — trend detection across 3+ historical points per test type (Feature 2)
- **RAG Q&A pipeline** — retrieval from knowledge base + user history, cited answer generation (Feature 3)
- **Deterministic safety layer** — rule-based red-flag check that runs BEFORE any LLM output on every Q&A request (Feature 4, cross-cutting)

## Tech

FastAPI + pdfplumber/pytesseract (OCR) + scikit-learn (anomaly) + sentence-transformers (embeddings) + pgvector

## Critical safety rule

The deterministic safety layer (red-flag keyword/pattern check) MUST run before any call to an LLM or embedding model on the `/qa` endpoint. If a red-flag triggers, the fixed emergency-guidance message is returned immediately — the LLM is never invoked. This is rule-based code, not model output. Do not refactor this away.

## API contract

| Method | Path | Description |
|---|---|---|
| `POST` | `/parse` | Accept a report file path/reference, run OCR + extraction, return structured values. Called by health-service after upload. |
| `POST` | `/anomaly` | Accept a list of historical values for one test type, return trend flags. |
| `POST` | `/qa` | Accept a user question + user context. Run safety check first. If clean, run RAG and return cited answer. |
| `POST` | `/embed-report` | Embed a user's parsed report values for retrieval in Q&A. Called internally after parsing. |
| `DELETE` | `/embeddings/{owner_id}/{report_id}` | Delete embeddings for a specific report (called by health-service on report deletion). |
| `GET` | `/health` | Service health check. |

## Database tables owned

- `knowledge_documents` — id, title, source_url, content_chunk, embedding (vector), ingested_at
- (User report embeddings also stored in pgvector, scoped by owner_id + report_id)

## Running locally

```bash
cd services/ai-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8003
```
