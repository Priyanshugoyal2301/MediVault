# MediVault engineering and product review

> Follow-up, 26 October 2026: the findings below describe the earlier review.
> The local prototype now has editable prescription drafts with explicit approval,
> atomic medication persistence and duplicate-submission protection. Its synthetic
> upload-to-doctor-summary walkthrough passed; the selected regression suite is
> now 267 passing tests. Vite/react-plugin upgrades resolved the three recorded npm
> findings; a fresh npm audit reports zero. The earlier approval block no longer
> applies. Clinical validation and other production gates remain open. See the
> [current demo guide](PROTOTYPE_DEMO_GUIDE.md) for the implementation boundary.

Review date: 26 October 2026. Scope: the existing local application and its alignment
with the owner's patient–doctor–family healthcare-record vision.

## Verdict

**MediVault is a functional local alpha, not a completed healthcare ecosystem.**
Its storage, basic care records and authorization foundation are useful. The
central promise—turning varied prescriptions into a reviewed, understandable,
dated medication history—is only partially implemented. Earlier test counts and
the external browser report did not establish that promise. The owner's concern
is supported by failures reproduced in this review.

The immediate priority is the core document-to-review-to-history journey.
Adding more dashboard sections does not close that gap. “Implemented locally,”
“passes a synthetic test” and “ready for real patients” must be separate statuses.

## Scope and evidence

Reviewed: login/MFA, upload UI and API, OCR selection and processing worker,
database models/migrations, document feedback and downloads, care authorization,
sharing, current Q&A/retrieval, existing delivery/security plans and dependency
metadata. Reused the previously reviewed AntiGravity report as externally reported
UI evidence; did not repeat its entire browser suite.

New evidence:

- Eight API-level upload cases using reproducible, visibly fictional documents.
- Direct checks of encrypted stored originals and byte-identical private downloads.
- Real Tesseract runs on a clear image, compressed JPEG, sideways image and scanned PDF.
- Updated live MFA enrollment/challenge/recovery/replay/lockout checks.
- Selected database/security/parser/service regression suite: **261 passed, 2 warnings**.
- Updated production web compilation passed.
- `npm audit` reported **3 vulnerabilities: 2 high, 1 moderate** in the installed
  web tooling dependency tree. This is not a full Python/container dependency audit.

This review is neither an independent penetration test nor clinical validation.
No real patient documents were used or sent to an external OCR service.

## 1. Problems reproduced and repaired

| Finding | Prior behavior | Repair | Evidence |
|---|---|---|---|
| Confusing login key | Authenticator/recovery field appeared for every login | Show the field only after a correct-password MFA challenge; explain it is not an API key | Live MFA check; web build |
| Sideways prescription | Required names/strengths/dates were missing | Confidence-gated Tesseract orientation correction plus EXIF handling | Failed before; passes the same fixture afterward |
| Wrong document category | Prescription uploaded as default Lab report could complete with no usable text | Require explicit type selection in UI; retain reviewable text when no supported lab fields are found | Failed before; passes afterward |
| Empty extraction looked successful | Empty parsed-value list could be returned as complete | Check readability; blank documents fail explicitly instead of inventing results | Blank fixture and new regression tests |
| Unhelpful failure message | User saw a generic failure without a next step | Persist safe processing feedback for unreadable/invalid/oversized input, service errors and timeouts | Migration 014, API checks and UI build |
| Open upload dialog could look stale | List polling did not refresh the open processing-detail view | Poll that view while queued/processing, stopping on completion or closure | Code review and build; targeted browser recheck remains useful |
| No owner-facing test files | Smoke fixtures were generated only inside scripts | Provide a downloadable ZIP, expected-result manifest and reproducible generator | Files available in upload form and public test-documents directory |

No extraction result is automatically converted into a confirmed current medicine.
Uncertain text still requires review against the original.

## 2. Reproducible acceptance result

Baseline: **6/8 passing**. After repairs: **8/8 passing**.

| Case | Expected outcome | Before | After |
|---|---|---|---|
| Clear prescription PNG | Preserve specified fictional medicine names, strengths and dates | Pass | Pass |
| Compressed prescription JPEG | Preserve the same required fragments | Pass | Pass |
| Sideways prescription PNG | Recover required fragments | Fail | Pass |
| Scanned prescription PDF | Recover required fragments | Pass | Pass |
| Native lab PDF | Correct haemoglobin value of 13.5 with matching name | Pass | Pass |
| Blank PDF | Explicit failure; original remains retrievable | Pass | Pass |
| Malformed PDF | Explicit failure; original remains retrievable | Pass | Pass |
| Prescription submitted as Lab report | Preserve readable text rather than empty success | Fail | Pass |

The pass criterion checks specified fragments/values, terminal processing state,
private original download and encrypted storage. It is not a claim of every-character
accuracy, general handwriting support or correct clinical interpretation. These
are eight cases, including reuse of one document under a second type; they are
not eight independently sourced real prescriptions.

The observed per-case elapsed times in this run ranged from 2.33 to 7.27 seconds.
They include upload, polling and retrieval on this laptop and are not a latency SLA.

Evidence: [baseline](../validation/document_acceptance_before_review.json),
[latest results](../validation/document_acceptance_latest.json).

## 3. Working, partial and missing product capabilities

| Product area | Status | What exists | What is still needed |
|---|---|---|---|
| Adult accounts and MFA | Working locally, incomplete lifecycle | Registration, login, revocable sessions, optional TOTP and recovery codes, attempt limits | Verified email, secure password reset, session-management UX, recovery support |
| Private document vault | Working on tested local cases | Encrypted originals, authenticated download, delete cleanup, patient scoping | Backup/restore validation, production key lifecycle, malware/hostile-file isolation |
| Prescription understanding | **Partial; core product blocker** | OCR text and source-linked manual medicine entries | Field extraction for name/strength/dose/route/frequency/duration/date, original-text highlights, correction and approval workflow |
| Lab extraction | Partial | Pattern-based extraction for supported tests/layouts, dated results | Broader layout coverage, reference-range pairing evaluation, reliable unit handling and unknown-field reporting |
| Medication reconciliation | Partial | Manually recorded taking/stopped/unknown state, source link | Review queue, duplicates/conflicts, prescribed-versus-reported reconciliation, changes across encounters |
| Reaction/allergy history | Working recordkeeping, not clinical decision support | Reported reactions, clinician confirmation restriction, explicit unknown state | Clinical workflow validation, missing-history reconciliation and source review |
| Patient timeline | Partial | Documents, lab history and manual encounters | Unified reviewed chronology across prescriptions, visits, medication changes and corrections |
| Family circle | Partial | Distinct profiles and explicit grants | Actual genealogical relationships, adult transfer, guardian disputes and staff workflow |
| Child access | Fail-closed local implementation | Pending verification and adulthood cutoff | Usable verification service, adult-account transition, expiry/revalidation and pediatric clinical review |
| Doctor workspace | Partial | Application, operator verification, scoped invitations | Staff review UI, rejection/appeal/expiry states, consultation workflow acceptance |
| Plain-language explanations | Partial | Deterministic lab explanations and cited reference snippets | Comprehension testing, complete Hindi translation, prescription-specific explanations tied to reviewed facts |
| Q&A | Partial | BM25 references plus up to 50 recent lab rows | Whole-history analyte/date retrieval; medication/prescription evidence; stable record-level citations |
| Appointments/referrals/claims/benefits | Working manual organizers | Entries and status tracking | Actual provider booking, insurer/CGHS status feeds and verified directory; currently no such integrations |
| Reminders | Missing background delivery | Dates can be recorded | Consent, timezone rules, delivery channel, retry/idempotency and user controls |
| Mobile application | Responsive web only | Small-screen interface and manifest | Device lifecycle, secure packaging, distribution and app-level acceptance |
| Production operation | Not ready | Local launcher and isolated database | Chosen hosting, monitoring, incident response, recovery drills and external assessment |

## 4. Security and reliability review

### Existing strengths

Server-side patient/category authorization; internal service authentication;
revocable sessions; HttpOnly cookies; write-origin checks; constrained sharing;
guardian and clinician checks; encrypted new originals; document path checks;
audit records; optimistic record versions; database queue leases and storage
deletion outbox. These controls have targeted tests and should be retained.

### Open release blockers and risks

| Priority | Finding | Required remediation / acceptance |
|---|---|---|
| Release blocker | Structured health fields and extracted text are not application-encrypted in PostgreSQL | Decide threat model; encrypt database/backups, restrict operators, manage keys and demonstrate restore |
| Release blocker | Document parsing still runs inside the service trust boundary | Isolate untrusted parser work; enforce memory/CPU/page/time budgets; test corrupt/hostile files and scanner policy |
| Release blocker | Dependency audit reports Vite/high, source-map-js/high and esbuild/moderate findings | Compatible dependency upgrades, repeat audit, rebuild and retest dev/proxy behavior; review Python/container dependencies too |
| Release blocker | No independent clinical or security assessment | Agree scope and assess before using real records in production |
| High | Password/email recovery and staff verification are incomplete | Implement and test legitimate recovery, abuse prevention and accountable operator workflows |
| High | Worker has a 5-minute lease while multi-page OCR can be slow | Align job timeout with lease, add heartbeat/cancellation/resource limits and test restart/reclaim behavior |
| High | Current test fixtures underrepresent real prescriptions | Add consented/de-identified handwritten, multilingual, blurred, cropped and varied-layout cases with clinician labels |
| High | Unsupported lab fields can be absent even when some fields parse | Report extraction coverage/uncertainty; provide original comparison and correction without implying completeness |
| High | Q&A and language limitations can produce misleading confidence | Restrict claims to retrieved evidence, fix text-only value handling, validate translations and expose unsupported questions |
| Medium | Legacy plaintext compatibility and development secrets are not production controls | Inventory/migrate legacy originals; production secret isolation and key rotation plan |
| Medium | Retry, storage failure and deletion interactions need broader fault injection | Test interrupted database commits, service outages, duplicate retries and deletion during processing |
| Medium | Care endpoints and optional research functionality share a large repository | Separate deployment surface from experiments; remove misleading stub-success contracts and stale claims |

The known npm findings were recorded under `scratch/npm-audit-review.json`.
Automatic approval review blocked the subsequent compatibility-inspection command
because its usage limit was reached. The command did not run and dependencies were
not upgraded. This was an approval-service failure, not a security rejection of
the proposed check. Dependency remediation remains open.

## 5. OXR and alternative extraction engines

The owner's links identify **SoMark OXR-1.0**. Its documented setup specifies Linux,
BF16-capable NVIDIA hardware and at least 24 GB GPU memory. This laptop exposes an
RTX 4060 Laptop GPU with approximately 8 GB. Its custom licence and operational
requirements need review before deployment. The vendor does not recommend its free
API for production. No medical files were sent to that API.
[Official model/deployment documentation](https://huggingface.co/SoMarkAI/OXR-1.0),
[source repository](https://github.com/SoMarkAI/OXR).

OXR is a particular document-understanding model, not proof that all OCR methods
are obsolete. A stronger reader can improve transcription/layout while still
requiring patient identity checks, medication-field validation and human review.

| Candidate | Appropriate evaluation role | Decision in this review |
|---|---|---|
| Current Tesseract + native PDF extraction | Lightweight local baseline for printed documents | Retained; repaired measured failures; not claimed sufficient for handwriting |
| SoMark OXR | Document layout/recognition comparison on suitable infrastructure | Researched, not installed or benchmarked; current laptop below documented GPU requirement |
| PaddleOCR / PaddleOCR-VL | Alternative multilingual/document-parsing evaluation | Candidate only; benchmark on the same labeled corpus before switching |

PaddleOCR's official project documents multilingual OCR and structured document
parsing. That capability claim is not a MediVault prescription accuracy result.
[Official PaddleOCR project](https://github.com/PaddlePaddle/PaddleOCR).

No Hugging Face account token is needed for the current local fixes or to read the
public model documentation. If a private deployment is later selected, agree its
hardware, cost and data-retention boundary first. Open weights do not eliminate
compute, storage, operations or validation costs.

## 6. Engineering plan ordered by patient value

### Stage A — Finish the upload-and-review journey

Keep a visible downloadable test pack; show pending/progress/failure states; display
original and extracted content together; permit correction; retain source spans,
engine identity and review status. Save only user-approved structured medication
details, with taking/stopped/unknown recorded separately from what was prescribed.

Acceptance: the owner can use the provided samples without credentials supplied
by a developer, compare every extracted field to its source, correct an error,
save the reviewed result and retrieve it in the correct patient's history after reload.

### Stage B — Compare extraction engines using a fixed benchmark

Freeze labeled cases and score drug names, strengths, schedules, duration and dates
separately. Include abstentions, missing fields, invented fields, reading-order errors
and processing time. Add real de-identified handwriting only with a valid data workflow.
Choose an engine from measured critical-field accuracy and deployment fit, not a headline.

Acceptance: publish per-case errors and backend identity; no unreviewed medical fact
enters the current-medication list. Clinical reviewers approve the release threshold.

### Stage C — Connect reviewed information into consultation history

Unify prescriptions, reports and encounters; reconcile duplicate/contradictory
medications and reported reactions; support clinically dated retrieval beyond the
recent-50-lab-row shortcut. Clearly distinguish recorded facts from reference explanations.

Acceptance: an authorized doctor can find previous medicines and reactions with
source/date/review status; revoked or wrong-patient access is denied at every endpoint.

### Stage D — Complete account, family and operator lifecycle

Implement verified recovery, guardian/doctor review, expiry, adult transition and
family relationships without treating relationship as authorization.

Acceptance: ordinary users can finish onboarding through supported workflows without
manual database edits or unexplained codes; recovery and disputes are auditable.

### Stage E — Production gates

Resolve dependency findings; isolate document processing; deploy database/key/backup
controls; test disaster recovery, service outages and resource exhaustion; commission
independent assessments. Add paid/external integrations only when authorized and needed.

Acceptance: agreed operational and security evidence exists. Do not mark the entire
ecosystem complete because the local acceptance pack or regression suite passes.

## 7. Files the owner can use now

- [Downloadable sample pack](../apps/web/public/test-documents/medivault-test-documents.zip)
- [Clear fictional prescription](../apps/web/public/test-documents/prescription-clear.png)
- [Sample lab report](../apps/web/public/test-documents/lab-report.pdf)
- [Expected outcomes](../apps/web/public/test-documents/manifest.json)
- [Current retrieval documentation](INFORMATION_RETRIEVAL.md)
- [Full delivery checklist](IMPLEMENTATION_CHECKLIST.md)

The upload form also links the sample ZIP. It includes deliberately blank and
malformed files that should fail; those expected rejections count as successful tests.

Reproduce the sample generation and actual upload verification:

```powershell
.\.venv\Scripts\python.exe scripts/generate_acceptance_samples.py
.\.venv\Scripts\python.exe scripts/check_document_acceptance.py
.\.venv\Scripts\python.exe scripts/smoke_auth.py
```

Use only the isolated local development database. The scripts retain fictional
accounts/records for inspection. They do not certify real-world prescription accuracy.
