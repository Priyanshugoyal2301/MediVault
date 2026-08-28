# Model Card — Unlimited-OCR (Phase 1 / 1A)

| Field | Value |
|-------|-------|
| Name | Unlimited-OCR DocumentParser |
| Package | `models/ocr/` |
| Flag | `USE_UNLIMITED_OCR` (default **off**) |
| Primary | HTTP Unlimited-OCR / Medical JSON |
| Fallback | Legacy Tesseract + regex |
| Version | 1.A (hardened) |

## Intended use

Document image → structured lab fields. Default production path remains legacy parser.

## Caveats

Local HF weights require explicit opt-in. Empty/failed Unlimited path falls back to legacy.
