# Phase 1A Observation Review

Source: `validation/model1-validation.md` (PASS WITH OBSERVATIONS).

| ID | Summary | Root cause | Severity | Action now? | Disposition |
|----|---------|------------|----------|-------------|-------------|
| O-01 | Flag switch needs restart | `@lru_cache` on registry/flags | Medium | Doc + log on startup | **Deferred** full hot-reload; **Documented** restart requirement |
| O-02 | Flag on ≠ always Unlimited path | Fallback by design | Low | Clarify docs | **Not a bug** — by design |
| O-03 | Confidence not on public API | API freeze for BC | Medium | Log confidence internally | **Deferred** API expand (would break BC) |
| O-04 | Parse exceptions → empty values | Outer safety net | Low | Keep + better logs | **Accepted** soft recovery |
| O-05 | Unlimited post F1 ≪ legacy | No normalizer / no VLM bake | High (cutover) | No accuracy work | **Deferred** Phase 2+ ML |
| O-06 | auto→local hang/OOM | Auto cascaded to HF local | **High** | Remove local from auto; explicit opt-ins | **Fixed** Phase 1A |
| O-07 | Empty [] skips fallback | Soft-success empty list | **High** | Empty → failure → legacy | **Fixed** Phase 1A |
| O-08 | No true integration tests | Unit-only suite | Medium | Add `tests/phase1a/` | **Fixed** Phase 1A |
| O-09 | Remote endpoint PHI egress | Operator config freedom | High (privacy) | Log PHI warning | **Mitigated** (docs + logs) |
| O-10 | Docs checklist incomplete | Missing named guides | Med | Add CONFIG/DEPLOY/etc | **Fixed** Phase 1A |
| O-11 | True VLM accuracy unmeasured | No endpoint/weights in CI | Medium | Keep experimental | **Deferred** ops bake-off |
| O-12 | Eval can mislead | Postprocess labeled “unlimited” | Low | Disclaim in docs | **Fixed** evaluation notes |
| Arch | models→services import | legacy map coupled | Low | CompatibilityLabValue | **Fixed** Phase 1A |

## Fallback scenarios (documented)

| Condition | Behavior |
|-----------|----------|
| Crash / exception | → legacy |
| HTTP timeout | → legacy |
| Malformed JSON | → legacy |
| Empty OCR text | → legacy |
| Empty laboratory list | → legacy (O-07) |
| Backend unavailable / auto no endpoint | → fail fast → legacy |
| Invalid config at init | → registry uses legacy only |
| Success with ≥1 lab value | → Unlimited path |

## Backend safety policy (Phase 1A)

- `auto`: HTTP only if `UNLIMITED_OCR_ENDPOINT` set; **never** auto-selects local weights  
- `local`: requires `UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS=1`  
- Download: requires `UNLIMITED_OCR_ALLOW_LOCAL_DOWNLOAD=1` else `local_files_only=True`  
- Default production: `USE_UNLIMITED_OCR=0`
