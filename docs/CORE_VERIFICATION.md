# Core verification — 26 October 2026

All checks used synthetic data and local APIs/processes. No browser automation,
external OCR service or real patient data was used in this verification pass.

## Results

- Selected regression suite: **255 passed, 2 warnings**. Includes real PostgreSQL
  access scoping, child restrictions, clinician suspension, consent expiry and
  revocation, version conflicts, source document isolation and cryptographic tests.
- `scripts/check_ocr.py`: real Tesseract extracted both TIFF frames and both parts
  of a mixed native/scanned PDF, including the specified dose/date. Blank image
  returned no invented text. Fixed the previous whole-PDF decision that could
  omit scanned pages after a selectable-text cover.
- `scripts/smoke_local.py`: real upload/worker/API flow extracted every normalized
  word in the known printed prescription fixture, persisted identical OCR text,
  parsed haemoglobin 13.5 g/dL and retained the test date. English and Hindi
  explanations were present. Original downloads exactly matched uploaded bytes.
- Direct database/filesystem checks confirmed document originals are encrypted
  and patient-linked, and asynchronous deletion removed the stored original.
- Live authorization checks rejected forged identity, another account, untrusted
  write origins and access after consent revocation; logout rejected cookie replay.
- `scripts/smoke_auth.py`: MFA enrollment, encrypted secret, hashed recovery codes,
  replay rejection, single-use recovery, disabling MFA with session revocation,
  and a database-persisted eight-failure/15-minute account limit passed.
- Production interface compilation passed. Browser review is a separate owner-run
  task described in `FRONTEND_TEST_HANDOFF.md`.

## Storage and retrieval

The isolated PostgreSQL database runs on loopback port 54329. Its existing volume
was retained when Windows reserved the former port. The original Compose database
was not modified. Migration head is 013.

Documents use opaque filenames and authenticated Fernet encryption in
`data/local-uploads`; keys stay in gitignored `.env.local`. Authorized downloads
decrypt originals on the server. SQL stores patient ownership, parsed text/results,
dates, care records, consent and audit metadata. **Parsed text and structured
medical fields are not application-encrypted in PostgreSQL.** Database/backup
encryption, managed keys, restore drills and production operator isolation remain
deployment gates. This is not end-to-end encryption against the server operator.

Passwords are bcrypt hashes; session tokens, invitation secrets and recovery
codes are hashed; authenticator seeds are encrypted. MFA is optional. Account
limits persist across restarts; edge/IP abuse controls and verified email recovery
remain outstanding. The local database password is development-only.

## What these results do not establish

Exact extraction of one synthetic printed prescription is not a clinical accuracy
benchmark. Handwriting, poor photos, complex tables, drug-name ambiguity and real
Hindi prescriptions require consented/de-identified examples and clinician labels.
The app currently exposes OCR text for review and manually source-linked medicine
entries; it does not reliably convert every prescription into verified medication
fields. It never assumes a prescription means a medicine is currently taken.

English/Hindi lab explanations are tested deterministic output, not a validated
diagnosis or a complete prescription translation service. Pediatric interpretation
remains withheld. No tests establish that the system is unbreakable; hostile-file
isolation, independent security assessment and clinical comprehension evaluation
remain required before handling real patient data in production.

Reproduce with the local stack running:

```powershell
.\.venv\Scripts\python.exe scripts/check_ocr.py
.\.venv\Scripts\python.exe scripts/smoke_local.py
.\.venv\Scripts\python.exe scripts/smoke_auth.py
```

Smoke checks retain synthetic records for inspection. Do not run them against a
production database. No Supabase account is required for this local configuration.
