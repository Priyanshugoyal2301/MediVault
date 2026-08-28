# Phase 1 tests

Covers Unlimited-OCR integration (preprocess, postprocess, client stub,
fallback, feature flags, dataset infrastructure, API schema freeze).

```bash
pytest tests/phase1 -q
pytest tests/unit/ai-service -q   # regression
```
