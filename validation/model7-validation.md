# Phase 7 — Anomaly detection validation

**Verdict: PASS WITH OBSERVATIONS**

Date: 2026-08-11

## Checklist

| Item | Result |
|------|--------|
| Isolation Forest operational | ✓ |
| LOF fallback operational | ✓ (`create_backend("lof")` + eval) |
| Robust Z baseline | ✓ |
| Feature flag operational | ✓ `USE_ANOMALY_MODEL` / alias `USE_OUTLIER_MODEL` |
| Default = statistical path | ✓ flag off |
| APIs unchanged | ✓ `/anomaly/detect` schema unchanged |
| Frontend unchanged | ✓ |
| Benchmarks generated | ✓ `docs/benchmark_phase7.md` |
| Tests passing | ✓ `tests/phase7` |
| No regressions | ✓ prior flags default off |

## Observations

| ID | Severity | Note |
|----|----------|------|
| **O-01** | Medium | ROC/PR on **synthetic** injected anomalies only. |
| **O-02** | Low | LOF PR-AUC > IF on this synthetic set; primary remains IF per design. |
| **O-03** | Low | Optional prior-phase features are **proxies**, not live risk/forecast/score engines. |
| **O-04** | Info | HTTP response omits extra DTO fields (probability/category); available on dataclass for internal use. |

## Gate decision

**PASS WITH OBSERVATIONS**

Do **not** begin Phase 8 until scheduled.
