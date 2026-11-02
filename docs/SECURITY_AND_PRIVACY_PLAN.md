# Security and privacy plan

Research date: 24 October 2026. Applies to the proposed India-first patient,
family and doctor product. This is an engineering plan and legal-review input,
not a security certification or legal opinion.

## Security objective

Prevent unauthorized access and alteration, detect failures, limit their impact,
and recover safely. No application can promise that nobody can ever compromise
it. Role-based navigation and a login screen are insufficient. Enforce explicit
resource authorization server-side, consistent with OWASP's object-level access
guidance. Use ASVS 5.0 as a traceable verification baseline, targeting Level 2
plus selected higher-assurance controls for sensitive operations; have an
independent assessor agree the final scope.
[OWASP API object authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/),
[OWASP ASVS 5.0](https://github.com/OWASP/ASVS/tree/master/5.0)

## Threats and required controls

| Threat | Control to implement / verify |
|---|---|
| Patient changes an ID to read another record | Deny-by-default object and field authorization on list, detail, download, search, export and mutations |
| Relative assumes family-wide access | Distinct relationship and authority records; no transitive sharing |
| Doctor grants themselves access | Verified professional identity plus current patient/guardian grant |
| Caller forges internal identity headers | Authenticate services; strip client identity claims; bind owner/subject to authorized actor |
| Stolen token or account takeover | MFA/passkeys, rate limits, secure recovery, short sessions, revocation, session inventory, step-up for sharing/export |
| Upload attacks | Allowlist and signature checks, quarantine, malware scan, sandboxed parser, page/pixel/time/size budgets, private file delivery |
| Malicious instructions inside documents | Treat OCR text as data; no tool execution or authorization decisions by the model |
| Leaked storage/log/backup | Private buckets, encryption, separate KMS permissions, PHI-free operational logs, controlled backup access |
| Stale consent in caches/workers | Recheck grant at execution and download; invalidate authorization caches; bind jobs to actor/patient |
| Doctor/device keeps exported copy | Warn before export, audit export, scope it explicitly; no false promise of remote deletion |
| Insider misuse | Least privilege, time-limited support access with reason and review, audited exports, protected audit sink |
| Wrong patient or erroneous OCR | Patient banner, source review, no silent record merging, versioned corrections |
| Data loss or ransomware | Encrypted isolated backups, restore exercises, documented recovery objectives |

Use private authenticated endpoints for originals; object keys and UUIDs are not
authorization. Avoid long-lived bearer share URLs or public QR codes. A QR card
may initiate a short-lived authenticated request; it must not contain raw medical
data or a reusable grant. An emergency card, if later added, is explicit opt-in
with minimal reviewed information and clearly different privacy tradeoffs.

OWASP's upload guidance supports layered checks and isolation. Existing magic
bytes and a 20 MB limit are only a beginning. Add streaming limits before buffering
and constrain decompression, rasterization, OCR and all parser subprocesses.
[OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

## Identity and browser sessions

Before a real-user pilot: replace persistent bearer tokens in localStorage with
a reviewed BFF session design using Secure/HttpOnly cookies, appropriate SameSite
settings, CSRF defenses and server-side revocation. Require MFA for doctors and
privileged operations, offer passkeys to patients, and secure recovery at the
same assurance level. NIST describes phishing-resistant authentication options;
OTP alone is not phishing resistant. Using the guidance does not certify this
application as NIST compliant.
[NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)

Use workload identities/mTLS or audience-bound service credentials for a broader
deployment. The current shared internal key is an interim boundary: any service
holding it can impersonate the trusted caller. It is not a complete zero-trust
architecture. Remove public health/AI/DB ingress in production and rotate secrets.

## Encryption and data handling

TLS at all exposed boundaries, managed encryption for database/objects/backups,
and managed key rotation are required deployment work. Use envelope encryption
with separate data/key permissions where warranted; no home-grown cryptography.
Server-side OCR necessarily needs controlled plaintext processing access. Do
not market this architecture as end-to-end encrypted against the operator.

Operational logs exclude report text, medicines, patient questions, access tokens,
object URLs and identity documents. Audit records retain the minimum identifiers
needed for accountability, with restricted access and a separate retention policy.
App operators must not casually browse patient documents through support tools.

Deletion must cover originals, revisions where legally deletable, extraction
artifacts, embeddings, caches, exports under our control and processing jobs.
Define backup expiry and prevent deleted data reappearing after restore. Explain
lawful retention exceptions; do not promise immediate erasure from every backup.
Use an outbox/transactional workflow so deletion and index invalidation are
reliable. Access/audit retention needs a documented lawful basis.

## India-specific requirements to resolve before launch

The **final DPDP Rules, 2025** have phased commencement: some provisions apply on
publication, Rule 4 after one year, and the listed remaining provisions after
eighteen months. The December corrigendum adjusts wording. As of this research
date, do not assume every provision is already operative or rely on the January
draft. The rules cover notices, security safeguards, breach handling, rights and
parent/guardian verification. Plan for them now and have Indian counsel map the
Act, commencement notifications and other applicable health/IT obligations to the
actual operating model. A consumer vault must not assume that healthcare-specific
child exemptions apply to it.
[Final Rules, Gazette G.S.R. 846(E)](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf),
[December corrigendum](https://www.meity.gov.in/static/uploads/2025/12/3c7ebbae0e5456f493f486e6845df86b.pdf)

Create an applicability register for: notices and purpose limits; data processors
and transfer locations; security/breach response; rights and grievance handling;
child/guardian verification; medical-record retention and confidentiality;
CERT-In reporting/log obligations where applicable; any medical-device or
telemedicine classification if later functionality changes. Do not equate a
HIPAA badge or India hosting alone with compliance. Keep real patient data out
of development, analytics, public AI endpoints and training unless a separately
reviewed lawful process permits it.

For ABDM, align with its consent-based exchange and privacy policies and complete
the relevant onboarding before claiming integration. An internal sharing screen
does not make MediVault a registered DPDP Consent Manager. Separate consent to
process records, share with a doctor, delegate to a caregiver, receive reminders
and participate in research.
[Government HDM policy overview](https://www.india.gov.in/category/health-wellness/subcategory/health-care-promotion-products/details/health-data-management-policy-of-ayushman-bharat-digital-mission-abdm),
[ABDM citizen brochure](https://abdm.gov.in/strapicms/uploads/ABHA_Brochure_Piano_final_b972459053.pdf)

## Current repository: security increment and remaining gaps

The first ecosystem increment adds authenticated BFF-to-health calls, fail-closed
internal authentication, coverage for AI Q&A/embedding routes, required JWT
claims, current account checks at the gateway, removal of client-supplied service
identity headers and no-store on proxied responses. Protected routes reject a
missing, short or placeholder internal key. Health liveness remains public.

Configure the same randomly generated INTERNAL_SERVICE_KEY (32+ characters) in
BFF, health and AI; generate locally with `secrets.token_urlsafe(48)`. Existing
demo placeholder keys must be replaced. The BFF now calls auth `/auth/me` for each
protected request, so an auth outage denies access instead of silently permitting
it. This adds latency and an availability dependency; measure before scaling.

Still required: doctor verification, patient/family/guardian policy enforcement,
consent persistence, audit infrastructure, MFA and secure sessions, recovery and
rate limiting, production key management, file quarantine, durable workers,
database least privilege/RLS evaluation, backup/restore and independent testing.
Account checks do not provide per-session logout/revocation. Shared-key checks
do not authorize doctors to view other patients.

## Release gates

1. A complete authorization matrix and tests for patient A/B, doctor with/without
   consent, expired/revoked grants, caregiver scope and disputed guardianship.
2. Browser-to-database tests for every PHI surface, including downloads, exports,
   search, caches, OCR jobs, notifications and deleted records.
3. Account recovery/MFA/session revocation tested; patient-visible access history.
4. Malicious upload and resource exhaustion tests in a contained environment.
5. Restore and deletion drills; incident-response runbook and processor inventory.
6. Independent penetration test, remediation verification, legal applicability
   review and clinician review before collecting real patient data in a pilot.

Record evidence and residual risks per control. A passing unit test suite or a
document claiming “secure” does not satisfy these gates.
