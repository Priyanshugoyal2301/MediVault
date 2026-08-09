# Shared Types — `packages/shared-types`

## Purpose

Pydantic schemas / DTOs that are used by more than one service.

**Rule:** If a schema is needed in two or more services, it lives here — never copy-pasted between services. Import from `shared-types`.

## Contents

Schemas are added here as each feature is built:

| Schema | Added at | Used by |
|---|---|---|
| `UserOut` | Feature 1 (auth) | auth-service, api |
| `ReportOut` | Feature 1 | health-service, api |
| `ReportValueOut` | Feature 1 | health-service, ai-service |
| `TimelineEventOut` | Feature 2 | health-service, api |
| `AnomalyFlagOut` | Feature 2 | ai-service, api |
| `QAMessageOut` | Feature 3 | ai-service, api |
