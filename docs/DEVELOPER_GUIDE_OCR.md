# Developer Guide — Unlimited-OCR (Phase 1A)

1. Keep `USE_UNLIMITED_OCR=0` for local day-to-day demos.
2. CI: use `UNLIMITED_OCR_BACKEND=stub` when exercising flag=1 without weights.
3. Restart ai-service after any `USE_UNLIMITED_OCR` / `UNLIMITED_OCR_*` change (`@lru_cache`).
4. Tests: `python -m pytest tests/phase1a tests/phase1 tests/unit/ai-service -q`
5. Config details: `docs/CONFIGURATION.md`. Deploy: `docs/DEPLOYMENT.md`.
6. Do not start Phase 2 (normalizer) until Phase 1A validation is accepted as PASS.
