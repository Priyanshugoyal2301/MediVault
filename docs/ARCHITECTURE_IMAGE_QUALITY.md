# Architecture — Image Quality (Phase 8)

```
Upload → /parse
  → get_quality_checker()
      flag off: PassThrough (ok=True)
      flag on:  ImageQualityEngine → ok / score / problems / recommendation
  → if not ok: empty values (existing soft fail)
  → else: DocumentParser (OCR unchanged)
```

### Sequence

```
file_bytes → QualityChecker.check
  → decode (JPEG/PNG/TIFF/PDF page)
  → features + ML/rules
  → QualityCheckResult
```

No new public endpoints. Frontend unchanged.
