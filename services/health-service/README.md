# Health Service — `services/health-service`

## What this service owns

Report metadata, extracted health values, health timeline events, and all user health data CRUD — including hard deletion (cascade).

**This service is the privacy enforcement point.** Every query must be scoped to `owner_id`. No global read endpoints exist here.

## Tech

FastAPI + SQLAlchemy (asyncpg) + Alembic + boto3 (S3-compat storage)

## API contract

| Method | Path | Description |
|---|---|---|
| `POST` | `/reports` | Upload a new report. Stores file, creates report record, enqueues parsing job to AI service. |
| `GET` | `/reports` | List all reports for the authenticated user. |
| `GET` | `/reports/{report_id}` | Get report metadata + extracted values for one report. |
| `DELETE` | `/reports/{report_id}` | Hard delete: report file, report record, extracted values, timeline events, and any embeddings for this report (via AI service). |
| `GET` | `/timeline` | Get timeline of extracted values for the authenticated user (all test types, or filtered). |
| `GET` | `/health` | Service health check. |

## Database tables owned

- `reports` — id, owner_id, filename, storage_path, upload_at, parsed_status, parsed_at
- `report_values` — id, report_id, owner_id, test_name, value, unit, reference_range_low, reference_range_high, date_of_test
- `timeline_events` — id, owner_id, test_name, value, unit, date_of_test, source_report_id

## Running locally

```bash
cd services/health-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```
