# Ecosystem delivery plan

Updated 24 October 2026. Scope includes patient/doctor care, children and family
cards, with CGHS-inspired administrative workflows. See
[ECOSYSTEM_BLUEPRINT.md](ECOSYSTEM_BLUEPRINT.md) for research and product decisions.

## Starting point

Reuse the existing report upload, parser, bilingual explainer, timeline,
owner-scoped repositories, gateway, default retrieval and safety layer. The
offline research package is useful for later evidence retrieval, but it is not
yet the live Q&A path. Do not promote disease-risk prediction into this product.
Keep existing uncommitted research work intact while evolving the application.

## Sequenced delivery

| Stage | Deliverable | Acceptance gate | Status |
|---|---|---|---|
| 0 | Research, scope reset, threat model and immediate service-boundary fixes | Security regressions checked; configuration changes documented | First increment in this change |
| 1 | Accounts vs patient profiles; doctor verification; guardian/delegation records; family-tree card | Two families and two doctors cannot cross access boundaries; no privilege from self-declared roles | Planned |
| 2 | Durable document pipeline; prescription drafts; visit metadata; source review | Critical fields require review; date ambiguity and unknown values preserved; originals retrievable only with access | Planned |
| 3 | Medication-use reconciliation, reactions/allergies, full visit timeline | Prescribed vs taking distinguished; unknown allergy state explicit; changes attributed and versioned | Planned |
| 4 | Scoped doctor sharing, consent inbox/revocation, consultation summary, access history | Expiry/revocation enforced across reads/downloads/jobs; partial sharing clearly shown | Planned |
| 5 | Grounded explanations, historical Q&A, confirmed reminders, accessibility | No unsupported medical claims; adult/pediatric results use appropriate context; patient comprehension evaluated | Planned |
| 6 | Appointment/referral diary, bills/claims organizer, benefits wallet and facility navigation | Manual vs connected status explicit; no fabricated booking/eligibility | Planned |
| 7 | ABDM/provider/insurer connectors and controlled pilot | Sandbox/profile conformance, contracts, legal/security/clinical gates and operational readiness | Planned |

Stages 1–4 form the first complete ecosystem workflow. Do not launch children or
doctor sharing halfway through the access model. Security work continues through
all stages; stage 0 does not certify the application.

## Concrete implementation backlog

### Identity, profiles and family

- Add patient_profiles with optional account links; backfill existing owner data
  under a reviewed migration and rollback plan. Maintain invariant that each
  resource belongs to exactly one patient, independently of uploader/actor.
- Add practitioner verification records, server-managed status and expiry; no
  self-service verified role. Define the staff verification workflow.
- Add family_relationships, guardian_authorities and caregiver_delegations with
  distinct acceptance, verification and revocation rules.
- Build accessible family-tree/list card, persistent selected-patient banner,
  invitation flow, pending/private states, and authority-management screen.
- Add expiry/dispute handling and an adulthood transition workflow; no silent
  transfer of a child's records to an unrelated adult account.

### Document and care history

- Evolve the existing reports abstraction to support prescription, lab report,
  referral, discharge summary and other clinical document types. Preserve API
  compatibility during migration instead of creating a competing upload stack.
- Use a durable job/outbox with retries, idempotency and worker isolation.
- Add source-bound extraction drafts and a review UI, preserving unknown fields.
- Finish existing concept/date/provenance persistence before using longitudinal
  research results in the product.
- Add encounters, prescription items, medication-use statements, reaction records
  and attributed clinician reviews; compare units and dates explicitly.

### Consent and doctor workspace

- Add scopes and expiry to grants; use one authorization service/policy module
  consistently on every data surface. Add tests against the real database.
- Add doctor consent requests without global patient search or clinical leakage.
- Implement limited consultation views and append-only clinical corrections.
- Add access/export audit events and a patient/guardian activity screen.

### Patient assistance and integrations

- Use confirmed instructions for reminders; support opt-out and private
  notifications. No automatic dose computation, especially for children.
- Add visit preparation and question list, referral tracking, bills/checklists,
  and manual claim status with explicit provenance.
- Build provider booking and official claim status only after authorized APIs
  and operational contracts exist. Keep government eligibility/card information
  separate from MediVault's own patient identity.
- Evaluate ABDM/ABHA, HPR/HFR and current FHIR profiles in a dedicated sandbox
  workstream; do not scrape private government beneficiary portals.

## Evaluation plan

Recruit a consented pilot group covering adult patients, guardians, older adults,
caregivers and doctors. Proposed initial discovery: 8–12 patient/caregiver
interviews and 4–6 clinician interviews, then test representative tasks. These
are proposed sample sizes, not completed research or statistical validation.

Build an appropriately consented/de-identified extraction set spanning printed
and handwritten prescriptions, scanned PDFs, mobile photographs, English/Hindi,
multiple hospitals and pediatric/adult reports. Separate train/development/test
by patient and source/provider where feasible. Have qualified reviewers label
drug identity, strength, dose, route, frequency, duration and clinical dates.

Report field accuracy and critical-error rates, abstention and correction burden,
not just OCR character accuracy. Evaluate look-alike drug names, combination
products, unclear handwriting, PRN use, duplicate documents and conflicting dates.
Publish denominators, uncertainty and failure examples. Choose release thresholds
with clinicians before evaluating the locked test set.

For explanations, measure unsupported numerical/temporal claims, source fidelity,
non-diagnostic tone and comprehension. For family/consent, test wrong-profile
uploads, adult invitation rejection, guardian revocation, disputed authority,
patient turning 18, doctor suspension and stale cached access.

## Current implementation status

The local ecosystem now includes patient/guardian profiles, clinician applications,
scoped consent, encrypted document originals, durable OCR jobs, versioned care
records, historical lab views, consultation summaries, an organizer and optional MFA.
Migrations through 013 have been applied to the isolated local PostgreSQL volume.
The responsive application replaces the original demo interface.

See [implementation checklist](IMPLEMENTATION_CHECKLIST.md) for delivered features
and outstanding gates, [core verification](CORE_VERIFICATION.md) for reproducible
results and limitations, and [local application](LOCAL_APPLICATION.md) to run it.
Hosting and external integrations remain deferred by the owner. Do not assign a
percentage complete to the whole ecosystem or treat test passes as clinical validation.
