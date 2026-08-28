# Phase 1 Validation Report — Unlimited-OCR Integration

**Role:** Independent QA / ML Validation Lead (non-author of Phase 1)  
**Date:** 2026-08-11  
**Scope:** Phase 1 only (document understanding)  
**Method:** Static code review, configuration inspection, functional probes, automated test runs, evaluate harness re-run  
**Constraints:** No code fixes, no refactors, no new features (this document only)

---

## Executive Summary

Phase 1 delivers a **scaffold + flag-gated integration** of Unlimited-OCR into MediVault's document-understanding path, keeps the **legacy parser as default and as exception fallback**, and freezes the **public `/parse` API**. Automated tests for Phase 1 modules **pass**. Offline accuracy bake-offs show the Unlimited **postprocess** path does **not** yet approach legacy IE quality on Plan C fixtures. End-to-end inference of upstream **baidu/Unlimited-OCR** weights was **not** observed in this audit (no live GPU/vLLM endpoint in the test environment); backend “auto/local” can attempt heavy model load.

**Verdict for Phase 1 gate (integrate safely + preserve product):**  
# PASS WITH OBSERVATIONS

**Not approved for:** enabling `USE_UNLIMITED_OCR=1` as a default/production cutover.  
**Approved for:** proceeding to Phase 2 work **only if** Unlimited stays default-off and stakeholders accept the observation list below.

---

## Final Decision

```
PASS WITH OBSERVATIONS
```

Phase 2 (Normalization) may begin under the constraint that Phase 1 Unlimited path remains **experimental**, legacy remains production default, and blocking issues listed under §Known Issues (non-blocking for phase gate / blocking for cutover) are tracked.

If stakeholders require **“Unlimited-OCR production-ready”** before Phase 2, reclassify this as **FAIL** for that stricter definition — evidence of live VLM accuracy gates is currently missing.

---

## 1. Architecture Review

| Check | Result | Evidence |
|-------|--------|----------|
| Unlimited-OCR package exists | **PASS** | `models/ocr/` (`infer.py`, `client.py`, `preprocess.py`, `postprocess.py`, `schema.py`, `dataset.py`, `metrics.py`, `evaluate.py`, `config.yaml`, …) |
| DocumentParser protocol respected | **PASS WITH NOTES** | `packages/ml-interfaces/document_parser.py` Protocol; `UnlimitedOCRParser` / `RegexDocumentParser` expose `parse()`. Adapter also adds `parse_as_legacy()` (service concern, not on Protocol). |
| Legacy parser exists | **PASS** | `services/ai-service/parsers/report_parser.py`, `ocr/tesseract_backend.py`, adapter `RegexDocumentParser` |
| No duplicate conflicting product paths | **PASS WITH NOTES** | Single `/parse` entry; dual implementations selected by registry (by design, not duplication). |
| Repository architecture fit | **PASS** | Logic under `models/ocr` + `services/ai-service/adapters` + `core/registry` matches ML packages + service adapters pattern. |
| Modular structure | **PASS** | Preprocess / client / postprocess / schema separated. |
| Circular dependencies | **PASS** (static) | Service adapters import models; models/postprocess imports `services.ai_service.parsers.report_parser` only for legacy mapping (one-way service pull from models layer — coupling smell, not a runtime cycle found). |
| Hardcoded absolute paths | **PASS** | Paths relative (`../../datasets/...` in YAML); config loader uses package-local `config.yaml`. |
| Hardcoded API keys | **PASS** | None found under `models/ocr`; OCR config endpoint empty by default. |
| Configuration driven | **PASS** | `config.yaml` + `USE_UNLIMITED_OCR` / `UNLIMITED_OCR_*` env overrides. |

### Architecture findings

1. **Layering:** `medical_json_to_legacy_values` imports **health-service-adjacent** `services.ai_service.parsers` from `models/ocr` — violates pure “models package independence”; works via repo `PYTHONPATH`/conftest but couples packages.  
2. **“Unlimited-OCR” brand vs implementation:** Live path is a **client abstraction** (HTTP OpenAI-compatible / optional local transformers / stub). Actual baidu weights are **not vendored**.  
3. **Production parse path** uses `parse_as_legacy` only — Medical JSON is internal and discarded on the wire (by API design).

---

## 2. Feature Flag Validation

| Expected | Observed |
|----------|----------|
| `USE_UNLIMITED_OCR=0` → legacy | **PASS** — registry returns `RegexDocumentParser` |
| `USE_UNLIMITED_OCR=1` → Unlimited primary + fallback shell | **PASS** — registry returns `FallbackDocumentParser(UnlimitedOCRDocumentParser, RegexDocumentParser)` |
| Zero-code switch | **PASS** — env/flag only (with process restart) |
| Instant rollback | **PASS WITH NOTES** — set flag `0` and restart process; `@lru_cache` on `get_feature_flags` / `get_document_parser` means mid-process flag flip **will not** apply without cache clear/restart |

**Tests:** `tests/phase1/test_unlimited_ocr.py::TestFeatureFlag` exercises 0/1.

**Observation O-01:** Rollback is “instant” only after **service restart** (or explicit cache clear). Not hot-reload.

**Observation O-02:** Flag `true` means “attempt Unlimited first,” **not** “guaranteed Unlimited path used.” Failures fail over to legacy (by design); empty soft-success does not (see §7).

---

## 3. Functional Validation

### 3.1 Covered by automated tests / probes

| Scenario | Result | Notes |
|----------|--------|-------|
| PNG preprocess | **PASS** | Tests + preprocess path |
| JPEG / JPG alias | **PASS** | `image/jpg` normalized |
| TIFF preprocess | **PASS** | Unit test present |
| Multi-page client (stub pages) | **PASS** | Stub multipage returns 2 page results |
| Multi-page **PDF** preprocess | **NOT RE-VERIFIED live in this audit after hang kill** | Code uses PyMuPDF; environment previously had fitz capability in prior session |
| Empty bytes | **PASS** | Raises `UnlimitedOCRError` (HTTP misconfig path) |
| Unsupported MIME | **PASS** | `ValueError` from preprocess |
| Corrupt image bytes | **PASS** (raises) | Preprocess/open fails rather than silent success |
| Rotated / low quality / large / GPU unavailable | **PARTIAL / UNTESTED end-to-end** | Heuristic deskew/rotate exists; no golden image e2e suite |
| Live baidu/Unlimited-OCR HTTP | **NOT RUN** | No `UNLIMITED_OCR_ENDPOINT` in audit env |
| Live local VLM load | **NOT COMPLETED** | Audit probe on `backend=auto` proceeded toward weight load and **risk of long hang** — process stopped by auditor |

### 3.2 Correct JSON (internal Medical JSON)

Internal schema supports:

- `patient`, `laboratory`, `metadata`, `confidence`  
- Lab entries: test_name, value, unit, reference_range, flag, page_number, bounding_box, ocr_confidence, extraction_confidence  

Verified via dataclass definitions + unit tests around roundtrip / extraction.

### 3.3 Public API JSON

**Unchanged** `ParseResponse` / `ParsedValueOut`:

- Does **not** include patient block, confidences, page numbers, bounding boxes  
- This is **required for backward compatibility** but means Phase 1 requirement language about “output contains confidence” applies only to **internal** Medical JSON, not the BFF/API contract

---

## 4. JSON Schema vs API Contract

| Layer | Schema |
|-------|--------|
| Internal Medical JSON | patient / laboratory[] / metadata / confidence — full Phase 1 fields |
| Public `POST /parse` | `{ report_id, values: [ test_name, panel, value_*, unit, reference_range_*, status, explanation_* ] }` |

| Check | Result |
|-------|--------|
| Public contract stable | **PASS** (regression test freezes field sets) |
| Frontend contract | **PASS** (no `apps/web` Phase 1 edits observed) |
| Medical JSON fields present in code | **PASS** |
| Medical JSON exposed to clients | **N/A / by design NO** |
| Confidence on public API | **FAIL against literal “output contains confidence” if “output” means HTTP** — **PASS if internal only** |

**Observation O-03:** Product requirement dualism: must keep public schema **and** deliver Medical JSON confidence — currently only internal; not persisted to DB either.

---

## 5. Backward Compatibility

| Surface | Result |
|---------|--------|
| Existing parse request/response models | **PASS** |
| Frontend | **PASS** (unchanged) |
| DB schema / migrations | **PASS** (no Phase 1 migrations) |
| Default behavior (`USE_UNLIMITED_OCR=0`) | **PASS** — same legacy path class as pre-Phase 1 intent |
| Demo seed path | **PASS** (seed bypasses OCR; not modified in Phase 1 scope files listed) |
| Retrieval / anomaly / auth | **PASS** (not rewired by design) |

**Observation O-04:** `parse.py` now wraps all parser exceptions and can return **empty `values=[]`** instead of 5xx — mild behavior change vs “hard fail to failed report” depending on health-service handling of empty parse (pre-existing empty-results pattern also exists for quality gate).

---

## 6. Performance Benchmarks

Re-ran: `python models/ocr/evaluate.py`  
Artifact: `datasets/evaluation/ocr_phase1_latest.json`

### 6.1 Accuracy (Plan C text fixtures, n=8)

| Metric | Legacy regex | Unlimited postprocess\* |
|--------|-------------:|------------------------:|
| Field Precision | 0.95 | 0.156 |
| Field Recall | 1.00 | 0.156 |
| Field F1 | **0.969** | **0.156** |
| Exact Match (doc) | 0.875 | 0.125 |
| Missing Field Rate | 0.00 | 0.844 |
| False Positive Rate | 0.05 | 0.594 |
| OCR Accuracy (text path proxy) | 1.0 | 1.0 |
| Table Accuracy | 1.0 | 0.156 |

\*This is **not** decoded baidu/Unlimited-OCR output. It is structural postprocess on **fixture text** (proxy of VLM markdown). True VLM CER/F1 is **unknown**.

### 6.2 Runtime (batch of 8, offline text bake-off)

| Metric | Observed (≈ shared batch wall) |
|--------|--------------------------------|
| latency_ms (batch) | ~37 |
| avg_processing_time_ms | ~4.6 |
| memory_mib (tracemalloc) | reported ~0 (weak instrumentation) |
| cpu_seconds | 0.0 reported (weak / platform) |
| gpu_memory_mib | 0.0 (no CUDA path exercised) |

### 6.3 Failure rate

| Path | Offline bake-off crash rate |
|------|------------------------------|
| Evaluate harness | 0 crashes |
| Live VLM | Not measured |

**Observation O-05:** Benchmark proves **legacy remains stronger** on current gold; Unlimited path is **not** ready to replace default on accuracy grounds.

---

## 7. Error Handling

| Failure mode | Behavior | Assessment |
|--------------|----------|------------|
| Exception in Unlimited primary | Log warning → legacy fallback | **PASS** |
| Missing HTTP endpoint + auto → local weight load | May attempt transformers/HF download (long hang / OOM risk) | **FAIL-ish for ops safety** (O-06) |
| Empty successful list from primary (`[]`) | **No fallback** on hot path `parse_as_legacy` | **FAIL vs strict reading of “failure must use legacy”** (O-07) |
| `parse()` path treats `None` as failure, not `[]` | Inconsistent with `parse_as_legacy` | **OBSERVATION** |
| Empty file_bytes | `UnlimitedOCRError` | **PASS** |
| Unsupported format | Preprocess ValueError → outer try/except → empty values | **PASS** (graceful; may lose better legacy extract if exception bubbled wrong—outer catches) |
| Model load failure during infer | Should raise and fallback | **PASS by design**; local load not fully proven |
| Logging | `get_logger`; warnings on fallback | **PASS** (PHI still subject to redacting logger culture) |

### O-06 — Auto backend hang risk (critical for ops)

With `USE_UNLIMITED_OCR=1` and no `UNLIMITED_OCR_ENDPOINT`, `backend=auto` tries **local** load after HTTP skip. Audit session observed process progress into sklearn/numpy import stack consistent with heavy ML dependency load; process was terminated by auditor after ~40s. Deployments can **stall first request** without explicit `UNLIMITED_OCR_BACKEND=http` + endpoint or intentional local GPU setup.

### O-07 — Empty result does not trigger fallback

`FallbackDocumentParser.parse_as_legacy` returns empty lists from Unlimited as success. A failing VLM that returns empty markdown therefore **suppresses** legacy IE that might still extract values. This is a **material product risk** when the flag is on.

---

## 8. Test Coverage

### 8.1 Suite results (this audit)

| Suite | Result |
|-------|--------|
| `tests/phase1` + `tests/unit/ai-service` | **136 passed** (earlier full-scope run) |
| Re-check phase1+ai-service | Previously **136 passed, 0 failed** |
| `tests/unit` (full) | **137 passed, 8 failed** auth-service JWT/password tests — **failues appear environment/passlib related, not attributed to Phase 1 OCR** (outside Phase 1 scope; still report) |
| `tests/integration` | **Empty** (`.gitkeep` only) |

### 8.2 Phase 1 test inventory (collected = 18)

| Category | Present? |
|----------|----------|
| Unit (schema, postprocess, metrics) | **Yes** |
| Feature flag | **Yes** |
| Fallback on exception | **Yes** |
| Dataset | **Yes** |
| Multi-page (stub) | **Yes** |
| Image preprocess | **Yes** |
| API schema freeze | **Yes** |
| Integration (real HTTP Unlimited-OCR) | **No** |
| Real multipage PDF e2e + parse | **No dedicated** |
| Timeout simulation | **No** |
| GPU unavailable path | **No** |
| Huge document stress | **No** |

### 8.3 Coverage %

`pytest-cov` **not installed** in this environment (`unrecognized arguments: --cov=...`). **Coverage %: N/A**.

**Observation O-08:** Phase 1 claims “integration / API tests” are mostly **unit-level**; no true service integration test for flag=on with filesystem fixture through `/parse`.

---

## 9. Security Review

| Check | Result |
|-------|--------|
| Secrets in `models/ocr` | **PASS** — none found |
| API keys hardcoded | **PASS** |
| Credentials in Phase 1 code | **PASS** |
| File access on parse | **PASS** — `resolve_safe_storage_path` enforces storage root |
| Temp storage cleanup | **PARTIAL** — in-memory images / no durable temp files observed in Unlimited path; local model cache (HF) is external |
| Logging PHI | **NOT FULLY AUDITED** for new paths; relies on `shared_utils` culture — recommend log review for raw OCR text |

**Observation O-09:** Sending report images to a remote `UNLIMITED_OCR_ENDPOINT` is a **PHI egress**; docs say prefer self-host, but no hard guardrails in code (allowed by config — operator risk).

---

## 10. Documentation Review

| Document | Status |
|----------|--------|
| `models/ocr/README.md` | **Updated** |
| `phase1-summary.md` | **Present** |
| `docs/benchmark_phase1.md` | **Present** |
| `docs/benchmark-results.md` | **Present** |
| `docs/MODEL_REGISTRY.md` | **Present** |
| `docs/model-cards/unlimited-ocr.md` | **Present** |
| `docs/CHANGELOG.md` | **Present** |
| `docs/ml-migration-plan.md` | **Updated** |
| `docs/ml-pipeline.md` / `current-pipeline.md` | **Updated** |
| `docs/02_ARCHITECTURE.md` | **Partial update** |
| `BIBLE.md` | **Partial IE/OCR update** |
| `00_PROJECT_STATE.md` | **Updated** |
| `.env.example` | **Updated** |
| `services/ai-service/README.md` | **Updated** |
| Root `README.md` | **Not verified as Phase-1-updated** (risk of stale setup copy) |
| `docs/ML_ARCHITECTURE.md` | **Missing** |
| `docs/API.md` | **Missing** |
| `docs/SYSTEM_DESIGN.md` | **Missing** |
| `docs/DATAFLOW.md` | **Missing** |
| `docs/ROADMAP.md` | **Missing** |
| `docs/evaluation/` directory guide | **Missing** (artifact under `datasets/evaluation`) |
| Diagrams (architecture/sequence for Unlimited path) | **Mostly ASCII only** — no new diagram assets |
| Deployment / Training / Configuration dedicated guides | **Embedded in README/model card, not standalone** |

**Observation O-10:** Documentation is **sufficient for engineers who already know the repo**, incomplete relative to the exhaustive checklist in the validation charter.

---

## 11. Regression Analysis

### Before → After (default flag off)

| Area | Change |
|------|--------|
| Legacy IE | Intact as default |
| Router parse | Tries quality gate + registry parser; exception → empty list |
| New deps | PyYAML in ai-service requirements |
| Startup | No forced model download when flag off |

### Breaking changes

**None** observed for public API/frontend/DB with default config.

### Behavior changes (subtle)

1. Empty exception swallow → possibly more “complete with 0 values” outcomes.  
2. When flag on: path logging `last_path`.  
3. Optional PHI transfer if endpoint configured.

### Performance regressions (default)

**None measured** (flag off; no VLM load).

### Unexpected side effects

- `@lru_cache` on parsers + flags.  
- Coupling models → services for legacy mapping.  
- Auth unit failures in full suite (likely environmental; not Phase 1 OCR).

---

## 12. Known Issues (do not fix — track)

| ID | Severity | Issue |
|----|----------|-------|
| O-01 | Medium | Flag/registry switch requires process restart (`lru_cache`) |
| O-02 | Low | Flag on ≠ guaranteed Unlimited path (fallback by design) |
| O-03 | Medium | Confidences/Medical JSON not on public API or DB |
| O-04 | Low | Parse exceptions become empty arrays |
| O-05 | **High (cutover)** | Unlimited postprocess F1 ~0.16 vs legacy ~0.97 |
| O-06 | **High (ops)** | `auto` backend may hang/OOM loading local VLM |
| O-07 | **High (correctness when flag on)** | Empty Unlimited result skips legacy |
| O-08 | Medium | No real integration test vs live Unlimited-OCR service |
| O-09 | High (privacy if misconfigured) | Remote endpoint PHI egress unchecked |
| O-10 | Low–Med | Missing several named documentation artifacts |
| O-11 | Medium | True Unlimited-OCR model accuracy **unmeasured** in this repo |
| O-12 | Low | Evaluate “unlimited” metrics can mislead non-technical readers if presented as VLM quality |

---

## 13. Risk Assessment

| Risk | Likelihood | Impact | Mitigation (recommendation only) |
|------|------------|--------|----------------------------------|
| Production enables flag without endpoint | Medium | Stall / empty extracts | Keep default 0; require http backend + healthcheck |
| Soft-empty suppress legacy | Medium | Silent data loss when flag on | Treat empty as soft-fail later |
| PHI to third-party OCR | Medium | Compliance | Policy + network egress controls |
| Accuracy claims in demos | Medium | Credibility | Present only legacy F1 as default quality |

**Residual risk with default flag off: Low** for ship of existing product.  
**Residual risk with flag on blindly: High.**

---

## 14. Deployment Readiness

| Config | Ready? |
|--------|--------|
| Deploy app with `USE_UNLIMITED_OCR=0` | **Yes** |
| Deploy with Unlimited HTTP endpoint validated | **Not proven in this audit** |
| Deploy with local HF weights default auto | **No** (ops risk) |
| Promote Unlimited as default parser | **No** |

Repository remains **deployable** under existing demo/production practices if flag remains off.

---

## 15. Repository Health (Phase 1 lens)

| Dimension | Score (/20) |
|-----------|------------:|
| Backward compatibility | 18 |
| Test evidence (unit) | 15 |
| Integration / e2e OCR proof | 6 |
| Accuracy readiness of ML path | 5 |
| Docs completeness vs charter | 12 |
| Ops safety of flag-on path | 8 |
| **Total (normalized /100)** | **≈ 64 / 100** for ML path readiness; **≈ 82 / 100** for “integration + default product safety” |

---

## 16. Recommendations (advisory — not implemented)

1. Keep `USE_UNLIMITED_OCR=0` in all shared environments until O-05/O-07/O-06 addressed.  
2. Before any enablement: require `UNLIMITED_OCR_BACKEND=http` + readiness probe on endpoint.  
3. Phase 2 Normalizer is the **right** next feature for field-name F1 — consistent with gap O-05.  
4. Add integration test: PDF fixture on disk → `/parse` with flag on and mock HTTP OCR.  
5. Consider empty primary result as soft-failure trigger for legacy (future fix).  
6. Do not market offline postprocess F1 as Unlimited-OCR model quality.  
7. Fill root README + missing docs named in charter when convenient.

---

## 17. Definition-of-Pass Checklist (charter)

| Criterion | Met? |
|-----------|------|
| Unlimited-OCR works | **PARTIAL** — integration works; live model not proven; accuracy poor offline |
| Legacy parser preserved | **YES** |
| Feature flag works | **YES** (with restart) |
| APIs unchanged | **YES** |
| Frontend unchanged | **YES** |
| Tests passing (phase1+ai) | **YES** (136); full unit has 8 auth fails out of scope |
| Benchmarks generated | **YES** |
| Validation report generated | **YES** (this file replaces prior implementer checklist) |
| Documentation updated | **PARTIAL** |
| Repository deployable | **YES** with flag default off |

Because two critical cutover/ops items (O-05 accuracy; O-06/O-07 flag-on safety) block full production Unlimited activation, but the phase goal of **safe, reversible integration without breaking default product** holds:

# PASS WITH OBSERVATIONS

**Phase 2 may proceed** only under continued **legacy-default** operation.  
**Do not** treat this as approval to enable Unlimited-OCR by default.  
**Do not** claim Phase 1 Unlimited accuracy leadership over legacy.

---

## 18. Audit Evidence Log

| Action | Outcome |
|--------|---------|
| `pytest tests/phase1 tests/unit/ai-service` | 136 passed |
| `pytest tests/unit` | 137 passed, 8 failed (auth) |
| `python models/ocr/evaluate.py` | Legacy F1 0.969; Unlimited post F1 0.156 |
| Code review registry/adapters/parse/client | Notes O-06, O-07 |
| Secret grep models/ocr | Clean |
| pytest-cov | Unavailable |
| Live VLM e2e | Not executed; local auto path interrupt |

---

*End of independent validation report.*
