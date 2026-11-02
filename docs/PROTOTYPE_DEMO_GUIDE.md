# MediVault local prototype demonstration

For the newer, fully populated presentation and independent backup accounts, use
[the presentation walkthrough](PRESENTATION_ACCOUNT_WALKTHROUGH.md) and
[private presentation logins](../.local-logs/PRESENTATION_ACCOUNTS.md).

Updated 26 October 2026. The prescription-to-reviewed-medication-to-consultation
workflow runs locally with PostgreSQL and CPU-based Tesseract. No Azure account,
hosted inference key, paid subscription or large GPU model is required.

## Start and sign in

```powershell
docker start medivault-care-dev
.\.venv\Scripts\python.exe scripts/dev.py
```

Open http://127.0.0.1:3000/. Use the fictional accounts in
[local presentation access](../.local-logs/PROTOTYPE_ACCESS.md). This private,
gitignored file contains passwords; do not publish it. Ordinary sign-in needs no
additional key. An authenticator code is requested only for an account that has
explicitly enabled MFA. Sharing invitation codes serve a different purpose:
they grant a selected recipient access to selected record categories.

The prepared patient has two reviewed fictional medicines, a reported fictional
reaction, a visit, a lab report and an isolated child profile. The prepared doctor
has limited, read-only consent. Fixture doctor/guardian approval was performed by
the local setup script and is not a real professional or identity verification.

## Five-minute demonstration

1. Sign in as the patient and open Documents. Download a test document from the
   page or use [the sample folder](../apps/web/public/test-documents/).
2. Upload a fictional prescription image with document type Prescription. Wait for
   processing to finish, then open its extracted text and original.
3. Choose **Review medicines**. Compare each candidate with the original, correct
   transcription errors and select only the rows you intend to save. Enter dose
   and use status only if known. Tablet strength is not automatically a dose;
   document date is not automatically a medication start date.
4. Confirm review and save. Selected rows become source-linked medication records
   together in one database transaction. Re-submitting the same reviewed document
   is rejected. Different documents can still describe the same medicine: reconcile
   existing records rather than approving duplicate courses during a demonstration.
5. Open Medications and Consultation summary to see the approved entries. Open
   Lab history / Understand reports for supported lab values and deterministic
   explanations. These explanations do not diagnose or prescribe.
6. Switch to the child's profile to demonstrate separate records. Return to the
   adult profile, inspect Sharing & privacy and access activity.
7. Sign out and sign in as the fictional doctor. Open the shared adult record and
   consultation summary. Read-only consent must not permit edits. The child is
   not automatically shared. Revoke consent from the patient account when done.

## Reproduce the core functional check

With the local stack running:

```powershell
.\.venv\Scripts\python.exe scripts/prototype_walkthrough.py
```

This creates fresh fictional accounts and exercises actual image OCR, candidate
review, explicit approval, duplicate rejection, medicine persistence, summary
retrieval, doctor denial before consent, read-only access after consent and child
isolation. It rewrites the private access file with the new accounts and writes
[machine-readable results](../validation/prototype_walkthrough_latest.json).
It is restricted to the isolated local development database. It retains its
fictional records for presentation; it is not a production seeding tool.

The separate [document acceptance results](../validation/document_acceptance_latest.json)
cover eight synthetic upload cases, including readable images, rotation and
invalid/empty files. These tests do not establish accuracy on real handwriting.

## Implemented boundary and remaining work

The prototype includes real authenticated persistence, encrypted document originals,
record permissions, revocation, human-reviewed medicine storage and consultation
summaries. Appointments, claims, referrals and benefits are personal organizers;
they do not connect to hospitals, insurers or government systems.

Prescription drafts use conservative rules over OCR text, not a medically validated
entity model. Unclear handwriting can fail or omit fields; users must review the
original. Hindi explanation coverage is partial. A unified cross-record clinical
timeline and full family tree are still incomplete. Clinical evaluation, recovery
and identity lifecycle, production key/backup management, hostile-file isolation,
Python/container dependency audits and independent security assessment remain
release work. Parsed text is readable by the database operator; this is not
end-to-end encryption. Do not present this local prototype as a finished clinical
system or use fictional medicines as treatment advice.

Node.js 22.12+ (or 20.19+) is required by the updated Vite toolchain. Preserve
`.env.local`: losing its encryption key prevents recovery of encrypted originals.
See [local setup](LOCAL_APPLICATION.md) and [retrieval documentation](INFORMATION_RETRIEVAL.md).
