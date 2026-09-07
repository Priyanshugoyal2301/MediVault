# Tests — `tests/`

## Structure

```
tests/
  unit/
    auth-service/     # unit tests scoped to auth-service
    health-service/   # unit tests scoped to health-service
    ai-service/       # unit tests scoped to ai-service
    api/              # unit tests scoped to api gateway
  integration/        # tests that span service boundaries
```

## Mandatory coverage rule (docs/DEVELOPER_RULES.md §5)

Every endpoint or function that touches user health data **must** have a test that verifies it is scoped to the requesting user — i.e. it cannot return another user's data (cross-user data leakage test).

This is not optional polish. It is the actual privacy enforcement verification point.

## Running

```bash
# From repo root
pytest tests/unit/
pytest tests/integration/
```

Test tooling (`pytest`, `httpx` test client) to be configured at Feature 1.
