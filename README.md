# MediVault

MediVault is a patient-controlled health-record prototype for organizing medical documents, reviewed medication history, care permissions, and longitudinal lab results. It is designed to help people prepare for conversations with clinicians. It does not diagnose, prescribe, or replace clinical care.

## About

The project combines a React web application with FastAPI services for authentication, health records, and document analysis. Patients can organize family profiles, share selected categories with a clinician or caregiver, inspect extracted text against an original document, and explicitly approve medication details before they enter a medication history. English and Hindi templates provide limited explanations for supported lab values.

The AI service is present in the repository and runs locally. It uses Tesseract OCR, deterministic parsing and safety rules, and evidence retrieval. Optional ML paths are feature-flagged. The default flow does not call a hosted large language model or cloud OCR provider. No hospital, insurer, government health-ID, or appointment-booking integration is connected.

## Current status

**Local alpha; the health-record application is not deployed. Do not enter real patient information.** The [informational project site](https://medivault-project-site.vercel.app/) is live on Vercel; it does not include or connect to the MediVault API, database, or document storage. The application, database migrations, and AI service have local implementations. A Render Blueprint and Vercel product-app configuration are now included, but no application services have been provisioned or connected yet.

| Component | Current state |
|---|---|
| Informational project site | [Live on Vercel](https://medivault-project-site.vercel.app/) |
| Product web app | Vite build passes locally; no public app URL |
| API and service containers | Render Blueprint is prepared; no Render service |
| Database | Free Supabase staging project exists in Mumbai; application schema and migrations are not applied |
| Document storage | Local adapter for development; encrypted S3-compatible adapter is implemented but no cloud bucket/keys are configured |
| Monitoring | No application deployment or production monitoring |
| Release assurance | Clinical review, recovery/restore drills, hostile-file isolation, independent security assessment, and complete security verification remain open |

See [deployment status and release prerequisites](docs/DEPLOYMENT.md), [implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md), and [security and privacy plan](docs/SECURITY_AND_PRIVACY_PLAN.md). The Vercel link above is an informational site only, not an application login or patient-data service.

The product app deployment path and repository settings are documented in [the frontend guide](apps/web/README.md), [Render service Blueprint](render.yaml), and [deployment runbook](docs/DEPLOYMENT.md). Completing this plan still requires provider-side credentials, schema migration, a private object-storage bucket, and approval for the always-on private Render compute required by this architecture.

## Features implemented locally

- Account sign-in, optional authenticator MFA, revocable sessions, and account security controls.
- Patient profiles, family/guardian workflows, clinician applications, and explicit category-scoped consent.
- Document upload, encrypted original storage, extraction status, human review, and private downloads.
- Source-linked medication review, reactions, visits, appointments, vaccinations, referrals, claims, and benefits records.
- Lab history, non-diagnostic explanations, and source-grounded question answering.
- Access activity, consultation summaries, print view, and authorized JSON export.
- Synthetic document and retrieval fixtures for local testing.

These are prototype capabilities. Their implementation does not establish clinical accuracy, regulatory compliance, or production readiness. See the [local demo guide](docs/PROTOTYPE_DEMO_GUIDE.md) for supported workflows and known limits.

## Architecture

```text
React web app
      │ same-origin API client
      ▼
FastAPI gateway (BFF)
      ├── Auth service ───────┐
      └── Health service ─────┼── PostgreSQL + pgvector
                 │            │
                 └── AI service (private internal calls)
```

The browser uses the gateway. The gateway validates the session, removes client-supplied identity headers, and authenticates internal service calls. Auth and health use separate runtime database roles in the local Compose configuration. See [architecture](docs/02_ARCHITECTURE.md) and [security plan](docs/SECURITY_AND_PRIVACY_PLAN.md).

## Run locally

Requirements: Python 3.11, Node.js 20.19+ or 22.12+, Docker with Compose, and Tesseract with English and Hindi language data.

The supported local launcher creates a private local environment file, applies migrations to the isolated development database, and starts the services:

```powershell
docker start medivault-care-dev
.\.venv\Scripts\python.exe scripts/dev.py
```

Open <http://127.0.0.1:3000/>. For a fresh checkout and setup instructions, see [Running MediVault locally](docs/LOCAL_APPLICATION.md). Keep `.env`, `.env.local`, encryption keys, recovery codes, and real medical records out of Git and external tools.

Build the product frontend:

```powershell
cd apps/web
npm ci
npm run build
```

## Verification

Run focused tests from the repository root with the project's Python environment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/auth-service tests/security/test_auth_abuse_controls.py -k "not asyncio" -q
```

This command covers synchronous auth checks only. It is not a substitute for the complete asynchronous, PostgreSQL, browser, dependency, security, and deployment checks described in the verification and deployment documents.

## Repository layout

| Path | Purpose |
|---|---|
| `apps/web/` | Patient and clinician React application |
| `apps/api/` | Browser-facing API gateway |
| `apps/research-site/` | Public project overview and research documentation site |
| `services/auth-service/` | Authentication, sessions, MFA |
| `services/health-service/` | Records, consent, document review, care workflows |
| `services/ai-service/` | OCR, parsing, retrieval, safety and optional ML adapters |
| `infra/migrations/` | PostgreSQL/Alembic schema history |
| `packages/research-data/` | Synthetic cohort tooling and retrieval evaluation |
| `tests/` | Unit, integration, and security regression tests |
| `docs/` | Product, architecture, verification, privacy, and operations documentation |

## Documentation

- [Local setup](docs/LOCAL_APPLICATION.md)
- [Implementation status](docs/IMPLEMENTATION_CHECKLIST.md)
- [Deployment status and prerequisites](docs/DEPLOYMENT.md)
- [Security and privacy plan](docs/SECURITY_AND_PRIVACY_PLAN.md)
- [Product and engineering review](docs/ENGINEERING_PRODUCT_REVIEW.md)
- [Information retrieval design and limitations](docs/INFORMATION_RETRIEVAL.md)
- [Prototype walkthrough](docs/PROTOTYPE_DEMO_GUIDE.md)

## Safety and privacy

Use only fictional test records until the release gates are met. Extracted text can be wrong; users must compare it with the source document. Medication details require explicit human review. The project does not validate handwriting or provide medical advice. Exported summaries may contain sensitive health information. Existing local encryption does not provide end-to-end encryption, and database records still depend on infrastructure access controls and encryption.

## License

No repository license has been published. All rights are reserved unless the maintainers add a license file. Do not assume permission to redistribute the code or data.
