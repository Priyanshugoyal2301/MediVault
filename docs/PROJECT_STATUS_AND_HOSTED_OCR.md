# MediVault status and hosted OCR decision

Updated 26 October 2026 after local prototype implementation. Latest verification:
267 selected regression tests passing, nine core walkthrough checks passing, and
the retained 8/8 synthetic document acceptance cases. These are historical local
results; the new review UI has build verification only. Current deployment and
verification status is recorded in [DEPLOYMENT.md](DEPLOYMENT.md).
The hosted-service comparisons below are optional research, not setup requirements.
Azure and large-model hosting are deferred at the owner's request.

## Completion assessment

**Stage: functional local alpha; original product vision incomplete; production release blocked.**

The storage/access/recordkeeping foundation exists. The core prescription-to-reviewed-
medication-to-consultation journey now passes a synthetic local walkthrough with
explicit editable review and source-linked persistence. A single completion percentage would
hide the fact that a core missing workflow matters more than several completed forms.
There is no agreed, weighted release backlog from which a defensible percentage can
be calculated. Test pass percentage is not product completion percentage.

Status meanings:

- **Implemented/tested:** passes the specified local checks, not every real-world condition.
- **Partial:** a useful implementation exists but the intended workflow or coverage is incomplete.
- **Missing:** not implemented as an end-user capability.
- **Unverified:** no adequate evidence yet; do not call this either proven working or broken.

## Full feature inventory

| Feature | Current state | Evidence / remaining work |
|---|---|---|
| Adult registration and sign-in | Implemented/tested | API sessions and external browser report; email ownership not verified |
| Sign-out and session revocation | Implemented/tested | Captured session replay denied after logout |
| Optional authenticator MFA | Implemented/tested | Enrollment, challenge, invalid code, TOTP replay, recovery and disable checks |
| Login-code usability | Implemented; build/API verified | Code field appears after valid-password MFA challenge; latest visual change not browser-rechecked |
| Password hashing and attempt limits | Implemented/tested | Hash storage and persistent eight-failure limit checked |
| Email verification/password reset | Missing | No complete verified recovery workflow |
| Session/device management | Partial | Server revocation exists; full user session/device console absent |
| Adult patient profile | Implemented/tested | Account and patient identity separated; basic creation/read tested |
| Family circle and profile switching | Implemented/tested | Separate profiles and loading guard; external browser observations |
| Full family tree | Missing | Current care circle is not a genealogical relationship model |
| Child profiles | Partial | Guardian lock tested; onboarding depends on operator verification |
| Guardian verification lifecycle | Partial | CLI approval/revocation; no complete staff UI, dispute or expiry workflow |
| Child turning 18 | Partial | Guardian cutoff tested; adult account-transfer workflow absent |
| Doctor application | Partial | Application and pending verification exist |
| Doctor authorization | Implemented/tested | Verification alone grants no record access; grants and suspension checked |
| Doctor review lifecycle | Partial | Staff verification UI, expiry and broader consultation workflow incomplete |
| Scoped sharing | Implemented/tested | Categories, expiry, read/write, acceptance and revocation checks |
| Single-use invitation codes | Implemented/tested | Hashed tokens and replay protection |
| Recipient-wide revocation | Implemented/tested | Patient/recipient isolation, audit and repeat-call tests |
| Access/activity history | Implemented/tested | Audit entries; latest-100 view; retention governance outstanding |
| Document upload | Implemented/tested | PDF/image uploads, type/size checks and patient boundaries |
| Encrypted original storage | Implemented/tested | Encryption/tamper/key/path tests and disk inspection |
| Private original download | Implemented/tested | Correct bytes, cross-account denial and grant revocation |
| Document deletion | Implemented/tested | Record removal and asynchronous physical-file cleanup |
| OCR queue and retry | Partial | Durable leases and retry exist; broader crash/concurrency/load tests needed |
| Printed prescription OCR | Implemented on tested samples | PNG/JPEG/scanned PDF/sideways fixtures pass; no general accuracy claim |
| Mixed PDF and TIFF extraction | Implemented/tested | Native/scanned pages and multiple frames checked |
| Blank/malformed document handling | Implemented/tested | Explicit failure and original retained for download |
| Wrong document type fallback | Implemented/tested | Readable prescription text retained when submitted as report |
| Extraction feedback | Implemented; API/build verified | Safe failure notes and processing-detail polling; visual recheck useful |
| Downloadable test documents | Implemented | Fictional fixture ZIP, manifest, generator and API runner |
| Real handwriting recognition | Unverified | No representative clinician-labeled benchmark |
| Structured prescription extraction | Prototype workflow implemented/tested | Conservative drafts, original preview, explicit correction/approval, transactional source-linked medicines; real handwriting and clinical accuracy unvalidated |
| Medication history | Implemented manual records | Taking/stopped/unknown, source links, versioned edits; automatic reconciliation missing |
| Allergies/reactions | Implemented/tested recordkeeping | Reported/confirmed/refuted restrictions and explicit unknown status |
| Drug interaction/allergy decision support | Missing | Do not claim automated prescribing safety or clinical alerts |
| Visit history | Implemented manual records | Encounter entries and persistence tested |
| Lab extraction/history | Partial | Supported patterns and dates tested; arbitrary layout/coverage/unit accuracy unverified |
| Unified clinical timeline | Partial | Separate histories exist; complete reviewed cross-document chronology missing |
| Appointment diary | Implemented manual organizer | CRUD-style create/read/edit flows; no hospital booking integration |
| Vaccination history | Implemented manual organizer | Record fields and access boundaries tested; no clinical schedule engine |
| Referral tracker | Implemented manual organizer | No official referral issuance/provider status feed |
| Bills and claims | Implemented manual organizer | No claim submission/payment/insurer verification integration |
| Benefits wallet | Implemented manual organizer | No government eligibility or beneficiary verification |
| Medication/follow-up notifications | Missing | No reliable background notification delivery |
| Consultation summary | Implemented/tested | Permitted sections only; JSON/print present; exported JSON still contains PHI |
| English lab explanations | Partial | Deterministic templates; clinical comprehension validation outstanding |
| Hindi explanations | Partial | Lab templates exist; Q&A uses limited phrase substitution, not complete translation |
| Pediatric explanations | Intentionally unavailable | Safety response and source review only pending validation |
| Patient Q&A | Partial | References plus recent-50 lab-value payload; prescription/medicine/history retrieval incomplete |
| Longitudinal hybrid retrieval | Research only | Implemented experiments; not the full live Q&A path |
| Responsive web interface | Implemented locally | Recent refinements are build-verified; a full browser and accessibility audit remains open |
| Installed Android/iOS application | Missing | Manifest exists; signed apps/device lifecycle verification absent |
| Supabase integration | Not used | Local PostgreSQL currently supplies persistence |
| CGHS/ABDM/ABHA/insurer connections | Missing | Inspired workflows only; no authorized live connectors |
| Production database/backups/keys | Incomplete | Parsed data not application-encrypted; managed encryption/key/restore controls pending |
| Malicious-file isolation | Incomplete | Bounds exist; isolated hostile-file processing not complete |
| Dependency remediation | Frontend findings resolved | Vite 8 upgrade and fresh npm audit: zero known vulnerabilities; Python/container review pending |
| Production monitoring/deployment | Missing | Hosting deferred; no production operational evidence |
| Independent clinical/security audit | Not performed | Passing development tests do not substitute for it |

## What has actually been verified

1. **267 selected regression tests:** auth/security, real PostgreSQL care permissions,
   parser/report/timeline, RAG/safety and selected OCR phases. Not every research suite.
2. **8/8 document acceptance cases:** clear PNG, compressed JPEG, sideways PNG,
   scanned prescription PDF, lab PDF, blank PDF, malformed PDF and wrong-category
   upload. Blank/malformed cases pass by failing safely. Selected names/strengths/
   dates and lab values are checked; these are not exhaustive transcription scores.
3. **Live storage/security checks:** encrypted originals, database persistence,
   exact downloads, access denial, grant revocation, deletion and logout replay.
4. **Live MFA checks:** encrypted seed, hashed recovery codes, password-only
   challenge, invalid password behavior, single-use recovery, disabling and limits.
5. **Production web build:** compiled successfully after the latest changes.
6. **Browser verification:** Full automated browser, keyboard, and accessibility
   testing remains open. The current workspace validation includes a production
   build but no browser automation.

Known defects fixed in the latest review were sideways extraction and wrong-type
empty results. Known unfinished functionality is listed above. Handwriting and
other untested conditions must not be described as fixed or proven broken without evidence.

## Hosted OCR decision

No 24 GB model needs to be installed on the owner's laptop. The proposed architecture
keeps authentication, storage and access policy in MediVault, with a server-side
provider adapter for OCR and the current local engine as an explicit fallback.
No cloud OCR provider has been integrated or benchmarked in this status update.

### Recommended first hosted evaluation: Azure Document Intelligence F0

Its free tier lists **500 pages/month**, with **4 MB** and **two analyzed pages per
request** limits. A server-side integration must reject/split supported inputs
deliberately and verify analyzed-page counts; it must not silently accept a truncated
result as a complete prescription. This is an evaluation recommendation, not a claim
that it beats Tesseract on MediVault's samples.
[Pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/),
[quotas](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/service-limits?view=doc-intel-4.0.0).

Microsoft documents temporary storage of inputs/results in the resource region,
including 24-hour retention after analysis. Real medical uploads still require an
agreed region, data-handling arrangement and consent flow. A free tier does not by
itself make a service appropriate for medical information.
[Data handling](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security).

### Other free or limited options

| Option | Useful role | Constraint |
|---|---|---|
| SoMark free OXR API | Compare fictional samples without local GPU installation | Publisher does not recommend it for production; do not use it as an assumed reliable medical-data backend |
| OCR.space free API | Lightweight online OCR comparison | Free file limit is 1 MB; free service has no uptime guarantee |
| Hugging Face Inference Providers | Experiment with supported hosted models | Free account credits are currently $0.10/month, subject to change; model hosting does not automatically provide an inference service |

Sources: [OXR](https://huggingface.co/SoMarkAI/OXR-1.0),
[OCR.space API](https://ocr.space/ocrapi), [OCR.space FAQ](https://ocr.space/faq),
[Hugging Face credits](https://huggingface.co/docs/inference-providers/main/pricing).

## Proposed next implementation sequence

**Superseded for the prototype:** no hosted resource is required. The review/approval
and medication-to-consultation steps below are now implemented and tested locally.
Use the [demo guide](PROTOTYPE_DEMO_GUIDE.md); hosted comparison remains future work.

1. Provision a selected hosted test resource; keep its key server-side in local
   ignored configuration. Use synthetic documents first and a hard free-tier limit.
2. Run both engines on the same labeled cases. Record missing/incorrect drug names,
   strength/dose/duration/date errors, latency, failed requests and provider identity.
3. Implement the structured review/approval journey; a better OCR engine alone
   cannot decide whether a medicine is current or a reaction is confirmed.
4. Connect reviewed facts to medication/visit history and scoped consultation/Q&A.
5. Finish account/guardian/doctor lifecycle, then close dependency and production
   security gates before external integrations or real-patient deployment.

For Azure evaluation, the missing setup is an F0 Document Intelligence resource and
its endpoint/key. Configure the secret locally, not in chat, frontend code or Git.
If account creation is undesirable, the no-account OXR comparison should remain
limited to the existing fictional fixtures until its privacy/operational boundary
is explicitly resolved.

Related evidence: [engineering review](ENGINEERING_PRODUCT_REVIEW.md),
[acceptance results](../validation/document_acceptance_latest.json),
[test files](../apps/web/public/test-documents/medivault-test-documents.zip).
