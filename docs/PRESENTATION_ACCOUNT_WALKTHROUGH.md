# Ready-to-use MediVault presentation

Prepared and checked 27 October 2026. This scenario contains invented identities,
medicines and results. The clinic-style documents are visibly labelled fictional.

## Accounts and startup

Open http://127.0.0.1:3000/. All three logins are in
[PRESENTATION_ACCOUNTS.md](../.local-logs/PRESENTATION_ACCOUNTS.md), a private,
gitignored file. No MFA code is needed for these accounts.

- **Patient:** main presentation account for Aarav Sharma and his child Mira.
- **Backup:** independent account with the same populated scenario. Keep it for
  restarting a presentation after changing records in the primary account.
- **Doctor:** Dr Kavya Mehta, with read-only access to the primary adult's documents,
  medicines, reactions and visits. The child and backup account are not shared.

The fictional clinician and guardian approvals were recorded by the local fixture
operator. They are not verification of real identities or qualifications. Doctor
consent expires 89 days after setup; renew explicitly before a later presentation.

If the application is stopped:

```powershell
docker start medivault-care-dev
.\.venv\Scripts\python.exe scripts/dev.py
```

An expired session returns to sign-in on the next protected request. Sign in again
with the saved credentials; no accounts or records need to be recreated.

## What is already populated in each patient account

| Area | Presentation content |
|---|---|
| Adult documents | Two prescriptions and two laboratory panels |
| Child documents | One separate child visit record |
| Medication history | Three approved, source-linked fictional medicines; two stopped, one use unknown |
| Reactions | One patient-reported fictional rash; not clinician-confirmed |
| Adult visits | Three dated encounters in September and October |
| Lab history | Eight measurements, each with two dated observations |
| Appointment | One planned follow-up with preparation notes |
| Referral | One fictional nutrition-desk referral |
| Bills and claims | INR 1,450 draft claim, not submitted to any insurer |
| Benefits wallet | Fictional employee-plan reference, not a valid entitlement |
| Vaccinations | One illustrative historical entry for the adult and one for the child |
| Child visits | One visit, isolated from the adult record |
| Consultation | Medicines, reactions, encounters and appointment snapshot |

The dashboard's **Reported taking** count is deliberately zero: a prescription
does not prove current medication use. The remaining medicine is marked unknown.

## Suggested presentation sequence

1. **Overview:** introduce the patient and show populated record counts and the
   planned visit. Explain that this is persisted application data, not UI mock data.
2. **Documents:** open the October 15 prescription. Show patient/clinician details,
   dates, medicine names, strengths, schedules and the reported reaction in OCR
   text. Download the original to compare. The sample's decorative header produces
   a small OCR artifact; critical names and instructions are checked separately.
3. **Review medicines:** the saved document shows its two approved medicines and
   blocks repeat approval. To demonstrate a fresh upload, use a copy from
   `output/pdf/presentation/`; do not approve duplicate courses accidentally.
4. **Medications:** show source linkage, stopped/unknown use and the literal
   instructions. Missing OCR instructions discovered during this test were restored
   through versioned record updates; the original review and corrections are retained.
5. **Lab history:** select Haemoglobin. It shows 13.2 g/dL on 15 September and
   13.6 g/dL on 20 October. Test dates come from reports, not upload timestamps.
6. **Understand reports:** ask “What does haemoglobin mean?” Show the relevant
   definition and the two recorded values. This is an explanation, not diagnosis.
7. **Visit timeline / Allergies / Consultation summary:** explain how the patient
   prepares for a visit. Print/export controls are available; keep exported copies private.
8. **Appointments, referrals, bills, benefits, vaccinations:** show the saved
   organizer entries. These do not book hospitals or submit insurance claims.
9. **Family circle:** switch to Mira to demonstrate separate child records and
   guardian-controlled access. Adult relatives require their own accounts and consent.
10. **Doctor:** sign out and use the doctor login. Show the shared adult profile and
    summary, with no editing rights. Return to the patient account after the demo.

## Verification and limits

[API acceptance](../validation/presentation_acceptance_latest.json) records actual
uploads, image OCR, PDF extraction, reviewed saves, download byte equality, encrypted
file storage, all organizer sections, dated lab history, explanations, summary and
cross-account denials. Setup was repeated without duplicate records.
[Follow-up checks](../validation/presentation_followup.json) cover instruction
corrections, relevant definition output and revoked-session denial.
Browser observations are recorded separately in
[presentation browser checks](../validation/presentation_browser_checks.json).

The presentation checks found and repaired three concrete defects: instructions
separated by OCR blank lines were omitted; expired sessions could leave a stuck
screen; simple definition questions could surface unrelated reference fragments.
The definition fix covers explicit definitions present in the curated corpus; it
does not make general medical Q&A or Hindi translation clinically validated.

The browser checks are a focused walkthrough, not every combination of forms,
devices, file formats or security attacks. MFA enrollment, all destructive actions,
real handwriting accuracy, production infrastructure and independent clinical/security
validation are not certified by this demonstration.

## Preserve and reuse

The private state file `.local-logs/presentation-state.json` holds account credentials
and fixture IDs. `scripts/seed_presentation.py` resumes missing setup without resetting
user edits; it is not a factory-reset command. Existing earlier prototype accounts
were preserved. The independent backup account protects the presentation scenario
from edits in the primary account, not from disk/database loss. Preserve the Docker
database volume, encrypted uploads and `.env.local` encryption key together.

The generated PDFs and the combined five-page pack are in
[presentation documents](../output/pdf/presentation/). Regenerate the PDFs with
`scripts/generate_presentation_documents.py` using Python with reportlab.
