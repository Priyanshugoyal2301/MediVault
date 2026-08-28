# Database notes — test names (Phase 2)

No schema migration in Phase 2.

`report_values.test_name` / `timeline_events.test_name` remain `String` columns.  
Phase 2 improves **values written** (more often canonical) via AI `/parse` normalizer.

LOINC codes are **not** persisted in Phase 2 (internal only on `NormalizationResult`).
