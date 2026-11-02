# Running MediVault locally

This local application extends the existing React/Vite + FastAPI services. It uses
real PostgreSQL persistence, not browser mock data. Hosting is deferred at the
owner's request. Do not use the local development configuration for public access.

## Start

The isolated development database created during this implementation is
`medivault-care-dev`, published only on `127.0.0.1:54329`. The pre-existing
`medivalt` Compose project and its database are separate and have not been migrated.
This separation protects existing data while new migrations are verified.

```powershell
docker start medivault-care-dev
.\.venv\Scripts\python.exe scripts/dev.py
```

For a fresh machine, create the development database once:

```powershell
docker run --name medivault-care-dev -e POSTGRES_PASSWORD=local-development-only -e POSTGRES_USER=medivault_user -e POSTGRES_DB=medivault -p 127.0.0.1:54329:5432 -d pgvector/pgvector:pg16
```

Open **http://127.0.0.1:3000/**. Create an account and personal profile. The
launcher applies migrations, starts auth/health/AI/gateway/web, and writes logs to
`.local-logs/`. Ctrl+C stops the processes it owns. Docker retains the database.

`scripts/dev.py` creates gitignored `.env.local` with random authentication,
internal-service and file-encryption keys. It never overwrites `.env`. Retain
`.env.local` securely: losing its encryption key loses access to encrypted originals.
Restart the launcher after backend changes. Vite reloads frontend changes.

Requirements: Python 3.11, Node.js 22.12+ (or 20.19+), project Python dependencies, `npm ci` in
`apps/web`, PostgreSQL with pgvector, and Tesseract with English/Hindi language
data. The launcher detects Tesseract on PATH or the standard Windows installation.
PDF native-text extraction uses pdfplumber; images use real Tesseract. The
local launcher disables optional remote/experimental ML adapters.

## Patient and doctor workflows

For prepared fictional accounts and the tested upload/review journey, follow the
[prototype demo guide](PROTOTYPE_DEMO_GUIDE.md).

1. Register/sign in. Session credentials live in an HttpOnly, SameSite cookie.
2. Create an adult personal profile; add a child through Family circle.
3. Child medical records remain locked until an operator verifies guardian authority.
4. Upload reports/prescriptions; review originals and extracted values/text.
   Lab test dates and document dates remain separate from upload time.
5. Add medication records with optional original-document links. “Prescribed” and
   “reported taking” are separate fields; extracted text never automatically starts
   a medication. Record suspected reactions as reported; only verified clinicians
   may confirm/refute them.
6. Record visits, appointments, referrals, vaccinations, scheme references and claims.
   These are personal records. They do not book appointments or submit claims.
7. Create an invitation under Sharing & privacy. Select categories, read/write
   permission and duration (up to 90 days). Give the code directly to the intended
   recipient. Caregiver codes are bearer invitations: whoever holds an unused
   code can accept it. Codes are hashed in storage and shown only at creation.
8. Doctors submit professional details under Doctor workspace. After operator
   verification they can accept doctor invitations. There is no global patient search.
9. Revoke permissions immediately at the API. Previously downloaded copies cannot
   be recalled. View access activity and export/print a consultation snapshot.

Adult relatives create their own accounts and explicitly share access. The family
circle displays separate profiles, not a merged clinical record. Turning 18 stops
guardian access; an independently verified operator transition is required.

## Operator verification

This privileged CLI requires database credentials; it is not a public endpoint.
The operator must independently check the registration/guardian evidence. An
opaque reference identifies evidence held in the operator's secure process.
Do not put identity-document contents in command arguments or logs.

```powershell
.\.venv\Scripts\python.exe scripts/verify_identity.py clinician <account-uuid> approve --operator <operator-reference> --evidence-reference <review-reference>
.\.venv\Scripts\python.exe scripts/verify_identity.py guardian <patient-uuid> approve --operator <operator-reference> --evidence-reference <review-reference>
```

Use `revoke` instead of `approve` to withdraw authority. Verification decisions
are retained in the database. Database access is the administrative boundary;
real deployment needs a restricted staff identity and documented review process.

## Verification

No further browser automation is used following the owner's instruction.

```powershell
# Backend-only integration check of the running local stack; synthetic data only.
.\.venv\Scripts\python.exe scripts/smoke_local.py

# Real-database tests use rolled-back transactions in this isolated database.
$env:CARE_TEST_DATABASE_URL='postgresql+asyncpg://medivault_user:local-development-only@127.0.0.1:54329/medivault'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_care_permissions.py tests/security tests/unit/auth-service tests/unit/health-service tests/unit/ai-service/test_anomaly.py tests/unit/ai-service/test_parser.py tests/unit/ai-service/test_rag.py tests/unit/ai-service/test_safety.py tests/phase1 tests/phase1a -p pytest_asyncio.plugin -q --disable-warnings

# Build check (not browser testing)
cd apps/web
node node_modules/vite/bin/vite.js build
```

Smoke-test accounts/documents are clearly synthetic and remain in the development
database for inspection. Never point these scripts at a real patient database.

## Security and operational boundaries

- All new originals are authenticated-encrypted before storage. Old plaintext
  originals remain readable for compatibility and require migration before rollout.
- Extracted text and clinical database rows still require infrastructure/database
  encryption, restricted database access and encrypted backups in deployment.
- Processing uses durable pending rows and leased claims. Interrupted work becomes
  eligible again after five minutes; failed extraction can be retried explicitly.
  The current worker runs in the health process and is not a hostile-file sandbox.
- Record deletion and file cleanup are joined through a transactional deletion
  outbox. The original is removed by the worker after its record is deleted.
- Corrections retain the previous version; optimistic concurrency rejects stale
  edits. Audit events omit clinical payloads; revision snapshots are access-scoped.
- Pediatric report interpretation is deliberately withheld pending validation of
  age-appropriate explanations. Originals, measurements and histories remain usable.
- The responsive layout and web manifest support mobile screens. No service worker
  caches medical records. This is not yet a signed Android/iOS package.
- Live CGHS/ABDM/ABHA, insurer, hospital booking, messaging and notifications are
  not connected. No government affiliation or official eligibility is represented.
- MFA, recovery/email verification, abuse controls, full retention/deletion policy,
  independent penetration testing, clinical validation, restore exercises and
  production monitoring remain release gates. No claim of invulnerability or
  regulatory certification is made.

See [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) for delivery status.
