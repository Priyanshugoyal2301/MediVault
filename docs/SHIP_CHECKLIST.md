# MediVault — Final Ship Checklist

Use this the morning of the event. Check every box.

## Environment

- [ ] Python 3.11+ available
- [ ] Node 18+ available (`npm -v`)
- [ ] Docker available for Postgres (or local Postgres 16 + pgvector)
- [ ] Repo at known path; `cd` works
- [ ] `.env` exists (copied from `.env.example`) — **not** committed

## Secrets (must match across processes)

- [ ] `POSTGRES_PASSWORD` set (not left as CHANGE_ME in a shared room)
- [ ] `AUTH_SECRET_KEY` ≥ 32 chars — **same** for auth-service and `apps/api`
- [ ] `INTERNAL_SERVICE_KEY` — **same** for health-service and ai-service (or empty on both)
- [ ] `MEDIVAULT_FAST_KB=1` for live demo
- [ ] `AI_SERVICE_URL=http://127.0.0.1:8003` for local processes
- [ ] `AUTH_SERVICE_URL` / `HEALTH_SERVICE_URL` point at local ports for BFF

## Dependencies

- [ ] `pip install -r services/auth-service/requirements.txt` (includes `email-validator`)
- [ ] `pip install -r services/health-service/requirements.txt`
- [ ] `pip install -r services/ai-service/requirements.txt`
- [ ] `pip install -r apps/api/requirements.txt` (includes `python-jose`)
- [ ] `cd apps/web && npm install`

## Database

- [ ] `docker-compose up -d postgres`
- [ ] `cd infra/migrations && alembic upgrade head` (through **004**)
- [ ] Can connect with configured user/password

## Services up

- [ ] Auth `:8001` `/health`
- [ ] Health `:8002` `/health`
- [ ] AI `:8003` `/health` → **`kb_ready`: true**, `kb_chunks` > 0
- [ ] BFF `:8000` `/health`
- [ ] Web `:3000`

## Automated checks

- [ ] `powershell -File scripts/demo_preflight.ps1` → PREFLIGHT PASSED
- [ ] `powershell -File scripts/smoke_demo.ps1` → SMOKE PASSED

## Browser smoke test (mandatory)

- [ ] Register `judge@example.com` / `password123` (or login)
- [ ] Dashboard empty state → CTA to Upload (before seeding)
- [ ] LIPID Demo completes with values + explanations
- [ ] Dashboard shows real report count (not hardcoded 4)
- [ ] Timeline shows LDL with trend/anomaly text
- [ ] Q&A chip “What does high LDL mean?” returns citations
- [ ] Q&A chip “What was my LDL?” mentions 165
- [ ] Safety chip returns emergency message (`safety_triggered`)
- [ ] Browser Network: Bearer token present; no client `X-User-ID`

## Demo data / backup

- [ ] Know login credentials for a pre-seeded account (backup)
- [ ] Screenshot of Lipid + Timeline + Safety as slide backup
- [ ] Curl commands ready if UI fails

## Presentation files

- [ ] `docs/DEMO_SCRIPT.md` open on second screen
- [ ] `docs/JUDGE_QA.md` open for questions
- [ ] `00_PROJECT_STATE.md` if judges ask scope
- [ ] Architecture one-liner memorized

## Git / hygiene

- [ ] No `.env` in git status
- [ ] Do not demo from a dirty broken branch mid-edit
- [ ] README status matches “hackathon prototype”

## Day-of don’ts

- [ ] Do not enable dense MiniLM on stage without warming (`MEDIVAULT_USE_DENSE=1` + `FAST_KB=0`)
- [ ] Do not upload unrehearsed PDFs as the main path
- [ ] Do not claim MiniLM Precision@5, trained IsolationForest, or HIPAA
- [ ] Do not open DEV_LOG “FULLY SHIPPED” entry to judges
