# Deployment — MediVault (ML-aware)

## Verified cloud status — 2 November 2026

The [MediVault project information site](https://medivault-project-site.vercel.app/)
is deployed on Vercel from the reviewed feature branch. It is a static site only;
it is not the health-record application and has no API or database connection.
Vercel Authentication is enabled, so access requires the authorized team or a
temporary share link. No production data is exposed by this site.
The MediVault application is **not deployed** to Vercel or Render. There is no
Render MediVault service; the existing services belong to other repositories.
The free Supabase staging
project `MediVault-Staging` is active in Mumbai (`ap-south-1`), but currently
has no public-schema tables and no recorded migrations. It is an empty database,
not a running application backend. No production monitoring is active.

The reviewed changes are on the pushed branch [`feature/medivault-ecosystem`](https://github.com/Priyanshugoyal2301/MediVault/tree/feature/medivault-ecosystem); `main` remains at the 7 September 2026 baseline. The deployment remains blocked until migrations and runtime roles are applied to the staging database, durable private document storage is configured, all service secrets are provisioned, and end-to-end staging checks pass. The current upload adapter only supports local storage; Render's free filesystem is ephemeral, so it is not safe for storing uploaded documents. Use only fictional test records until the security, privacy, clinical and recovery release gates are satisfied.

The local verification on 2 November passed the Vite production build, Python
bytecode compilation, and Docker Compose configuration validation. The focused
async security/database test run did not complete in the available Windows
runtime, and `npm audit` could not reach the npm registry due to DNS/network
failure. These are open verification gates, not passing checks.

## Service boundary update — 24 October 2026

Set the same randomly generated `INTERNAL_SERVICE_KEY` (32+ characters) in BFF,
health and AI. Protected data routes fail closed if it is missing, short or a
placeholder. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Do not place this key in browser configuration. Restart the three services after
changing it. The BFF also checks auth `/auth/me` on every protected request, so
auth-service availability is now required for those requests.

Rebuild the BFF Docker image to include the shared validation helper. Keep
health/AI/database ingress private. This local Compose stack remains a prototype;
the production gates are in [SECURITY_AND_PRIVACY_PLAN.md](SECURITY_AND_PRIVACY_PLAN.md).

## Production defaults

1. Copy `.env.example` → `.env`; keep **all** `USE_*` ML flags at **0**.  
2. `ML_EXPERIMENT_TRACKING=0`.  
3. Deploy services (auth / health / AI / BFF / web) as before.  
4. Verify `GET ai-service/health` → `ml_feature_flags` all false.  
5. Smoke parse + anomaly against pre-upgrade schemas.

## Document OCR (optional experimental)

1. Default: `USE_UNLIMITED_OCR=0` (legacy).  
2. Staging Unlimited: `USE_UNLIMITED_OCR=1` + private `UNLIMITED_OCR_ENDPOINT` only.  
3. Do **not** set `UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS=1` on small boxes unless intentional.  
4. PHI: self-host only.

## Cutover policy

Enable **one** flag at a time on staging; measure latency/errors; rollback = set flag `0` + restart.

Container images stay lean without forced torch when flags stay off.

## Runtime database roles and authentication abuse controls

Runtime Compose containers no longer import the whole `.env`. Auth receives
only the auth database role, JWT, and file-encryption settings; health receives
its own database role plus storage and internal-service settings; AI and the
BFF receive only their respective internal-call settings. Generate distinct
`POSTGRES_AUTH_PASSWORD` and `POSTGRES_HEALTH_PASSWORD` values (32+ characters)
before applying migration `017`.

Run Alembic with the migration-owner credentials in `POSTGRES_USER` and
`POSTGRES_PASSWORD`, and with both runtime-role passwords in the environment.
Migration `017` creates the roles and rate-limit table and grants auth access
only to `users`, `auth_sessions`, and `auth_login_attempts`. Health receives
CRUD on application health tables and read access to only `users.id`; it does
not receive access to password hashes or auth sessions. Future migrations must
grant new health-owned tables to `medivault_health` explicitly.

Login failures are counted for a client IP and an IP/email pair in PostgreSQL,
so state is shared by service instances. A source is limited to 60 failed
attempts and a source/account pair to 8 failed attempts per 15 minutes. Failures
for one address no longer make the account unavailable from another source.
When the BFF is behind Render's Cloudflare edge, set `TRUST_CF_CONNECTING_IP=true`
so the BFF uses Render's overwritten `CF-Connecting-IP` value; otherwise it
uses the socket peer address. Never accept the `X-Auth-Client-IP` header from a
browser; the BFF strips and replaces it before forwarding login requests.

Registration returns the same generic `202` response for new and existing
addresses. New users are created without receiving a session cookie and then
sign in through the normal login route. Existing accounts keep their current
password; registration never resets or reveals it.
