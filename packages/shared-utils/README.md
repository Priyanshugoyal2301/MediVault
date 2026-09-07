# Shared Utils — `packages/shared-utils`

## Purpose

Shared utilities used across services:
- **Logging** (with mandatory health-data redaction — see `logging.py`)
- Error handling helpers
- Config loader

**Rule:** No business logic here. If it belongs to a feature, it goes in the relevant service.

## Key module: `logging.py`

The logger in `logging.py` redacts known health-data fields before emitting any log record.
This enforces `docs/DEVELOPER_RULES.md` §4: "Do not log or print raw health data to application logs."
All services MUST use this logger, never the stdlib logger directly for health-data-touching code paths.
