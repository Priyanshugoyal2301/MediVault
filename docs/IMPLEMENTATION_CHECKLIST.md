# MediVault implementation checklist

Status as of 26 October 2026. A checked item means implemented locally; verification
evidence is listed separately. This does not certify production readiness.

**Latest prototype update:** the local prescription-to-reviewed-medication-to-
consultation journey now passes its synthetic API/database walkthrough. See the
[demo guide](PROTOTYPE_DEMO_GUIDE.md). The broader healthcare vision and production
release remain incomplete; historical findings are in the engineering review.

## Implemented local workflows

- [x] Separate account and patient identities, one personal profile per adult account.
- [x] Family-circle cards, profile switching and explicit adult sharing.
- [x] Child profiles, operator-controlled guardian approval/revocation, age-18 cutoff.
- [x] Clinician application and operator verification; no self-declared verified role.
- [x] Shared authorization policy for care records, documents, downloads, timelines and Q&A.
- [x] Category-scoped, expiring, read/write grants; hashed single-use invitations and revocation.
- [x] HttpOnly/SameSite login cookies, origin checks and revocable server-side sessions.
- [x] Gateway identity-header stripping and fail-closed internal service authentication.
- [x] Encrypted new document originals, private downloads and bounded uploads.
- [x] Report/prescription/discharge/other document types and distinct document/upload dates.
- [x] Durable document processing leases and explicit retry of failed extraction.
- [x] PDF lab extraction and prescription OCR text for human review.
- [x] Source-linked medication entries; prescribed vs reported use; unknown use retained.
- [x] Suspected reactions, severity, clinician confirmation/refutation and explicit unknown status.
- [x] Visits, follow-up notes, appointment diary and historical lab results.
- [x] Versioned corrections with retained snapshots and conflict detection.
- [x] Patient access history and permission management.
- [x] Limited doctor/caregiver consultation summary, print and JSON export.
- [x] Existing English/Hindi explanations and deterministic emergency safety handling retained.
- [x] Pediatric automated interpretation withheld; source documents remain reviewable.
- [x] Manual referral tracking, bills/claims diary, benefits wallet and vaccination history.
- [x] Responsive light interface, mobile navigation, labelled forms, dialogs and reduced motion.
- [x] Web manifest, no PHI browser persistence or offline cache, error and empty states.
- [x] Local launcher, isolated database, migration chain and operator instructions.

## Verification

- [x] Expanded synthetic upload acceptance: 6/8 before review, 8/8 after orientation and empty-result fixes; downloadable test pack available.
- [x] Latest selected regression suite: 271 passed, 2 warnings; prescription review permissions and transactional persistence included.
- [x] Editable prescription candidates, original-document preview, explicit selection/confirmation and atomic source-linked medication approval; repeat submissions rejected.
- [x] Fictional patient/doctor presentation accounts and nine-check local walkthrough; no cloud OCR prerequisite.
- [x] Vite 8 dependency upgrade; npm audit reports zero known vulnerabilities. Python/container audit remains separate.
- [ ] Resolve 3 npm audit findings and complete Python/container dependency audit; package compatibility check was blocked by approval-service usage limit.

- [x] Reviewed owner-supplied AntiGravity browser report; addressed narrow-screen search and recipient-wide revocation observations. See [review and qualifications](FRONTEND_VERIFICATION_REVIEW.md).

- [x] Migration chain applied to isolated PostgreSQL, preserving the existing Compose database.
- [x] Real PostgreSQL cross-account, read-only, category, expiry and revocation tests.
- [x] Guardian restrictions, adulthood cutoff and clinician suspension tests.
- [x] Child-document separation across report, download, timeline and Q&A routes.
- [x] Correction-version conflict and retained-history tests.
- [x] Encryption authentication, key mismatch and storage traversal checks.
- [x] Combined regression run: 255 passed, 2 warnings; see CORE_VERIFICATION.md.
- [x] Regression rerun after OCR, MFA and persisted authentication limits.
- [x] Backend-only live smoke: exact synthetic OCR, storage/retrieval/deletion, consent and logout replay denial.
- [x] Frontend production compilation (no browser automation).

## Remaining engineering and launch gates

- [ ] Verified adulthood account-transfer flow and guardian disputes with staff review.
- [ ] Verification expiry/revalidation and a production staff review interface.
- [ ] Full genealogical relationships independent of clinical sharing; current view is a care circle.
- [ ] Clinically evaluated structured prescription extraction; current rule-generated drafts require human correction and approval.
- [ ] Clinically validated pediatric explanations, multilingual UI and comprehension evaluation.
- [ ] Confirmed medication reminders and consented background notifications.
- [x] Optional authenticator MFA, single-use recovery codes and persisted account attempt limits.
- [ ] Verified email/account recovery and deployed edge/IP abuse prevention.
- [ ] Patient deletion/export governance across backups and retained audit records.
- [ ] Hostile-file isolation/scanning, dependency review and independent security assessment.
- [ ] India-region deployment, secret management, database encryption and restore/monitoring validation.
- [ ] Authorized CGHS/ABDM/ABHA/provider/insurer connectors and sandbox conformance.
- [ ] Signed mobile packaging and device-specific lifecycle testing.

External services and hosting were explicitly deferred by the owner. The remaining
engineering gates above are not described as completed or replaced by simulated integrations.

## Presentation scenario (27 October 2026)

- [x] Populated primary patient, independent backup and read-only doctor accounts.
- [x] Five clinic-style fictional source documents per patient account, real uploads and encrypted original verification.
- [x] Versioned corrections for OCR instruction spacing, relevant definition retrieval and expired-session recovery.
- [x] Focused browser walkthrough with separate evidence; see [presentation guide](PRESENTATION_ACCOUNT_WALKTHROUGH.md).
