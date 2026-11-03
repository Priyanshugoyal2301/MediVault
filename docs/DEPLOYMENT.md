# Deployment — MediVault (ML-aware)

## Verified cloud status — 2 November 2026

The [MediVault project information site](https://medivault-project-site.vercel.app/)
is deployed on Vercel from the reviewed feature branch. It is a static site only;
it is not the health-record application and has no API or database connection.
Vercel Authentication is enabled, so access requires the authorized team or a
temporary share link. No production data is exposed by this site.
The MediVault application is **not deployed** to Vercel or Render. There is no
Render MediVault service; the existing services belong to other repositories.
The Supabase staging project `MediVault-Staging` is active in Mumbai
(`ap-south-1`), but currently has no public-schema tables and no recorded
migrations. No private document bucket or S3 credentials are configured. No
application monitoring is active.

The current branch contains an S3-compatible storage adapter. It encrypts originals
before writing them and lets the OCR service read them from the same private
bucket. The adapter is unit-tested, but it is not active in the hosted project
until the bucket and server-side access keys are configured. Render's free
compute does not provide private services: free web services cannot receive
private-network traffic, while this architecture requires the API gateway to be
the only public backend and auth, health, and OCR to stay private. An always-on
Render layout therefore needs paid compute. At current rates, a baseline of a
$7/month API gateway, $7/month auth service, $7/month health service, and a
$25/month 2 GB OCR service is about $46/month before transfer and any extra
storage or workspace costs. No paid Render resources have been created.

The app remains a prototype. Keep it limited to fictional test records until
the migration, access-control, backup/restore, monitoring, clinical review,
privacy, and security release gates have been completed. This staging setup is
not a clinical or compliance certification.

The local verification on 2 November passed the Vite production build, Python
bytecode compilation, and Docker Compose configuration validation. The focused
async security/database test run did not complete in the available Windows
runtime, and `npm audit` could not reach the npm registry due to DNS/network
failure. These are open verification gates, not passing checks.

## Product app deployment configuration — 3 November 2026

`render.yaml` describes the actual services: the public API gateway and private
auth, health, and AI services. `apps/web/vercel.json` configures the React
product app. Create a **separate Vercel project** with its root directory set to
`apps/web`; the existing `medivault-project-site` serves only project information.
The app uses same-origin `/api/*` requests so its HttpOnly session cookie stays
on the app origin. Update the Vercel rewrite target to the actual Render API URL
after provisioning, then set `CORS_ORIGINS` to the product app's Vercel origin.

The Blueprint targets the existing Mumbai Supabase project, so it does not
create a new database project. Supply the Supabase session-pooler host and
credentials as Render secrets (use the pooler endpoint for IPv4-compatible
connectivity). Apply migrations `001` through `017` using the
database migration-owner credentials before the runtime services start. Migration
`017` creates least-privilege service roles and requires unique 32+ character
`POSTGRES_AUTH_PASSWORD` and `POSTGRES_HEALTH_PASSWORD` values. Configure the
auth database username as `medivault_auth` and the health username as
`medivault_health`; use their corresponding role passwords.

Create a private Supabase Storage bucket and server-side S3 credentials for
health and AI. Use the same Fernet `FILE_ENCRYPTION_KEY` for both services, the
same `AUTH_SECRET_KEY` for BFF and auth, and the same `INTERNAL_SERVICE_KEY`
for BFF, health, and AI. Enter values only in Render's secret fields; never
commit or share them in chat. Use fictional data during staging.

The current always-on compute estimate is about **$46/month** for the API
gateway (0.5 CPU/512 MB), auth (0.5 CPU/512 MB), health (0.5 CPU/512 MB), and
AI (1 CPU/2 GB), before transfer, storage, and any workspace subscription.
Render's current service plan identifiers and service types are documented in
[its Blueprint reference](https://render.com/docs/blueprint-spec) and live
[pricing page](https://render.com/pricing). No paid resources have been created.

Deployment sequence: create the Blueprint from this repository and configure
secrets; apply database migrations; verify private service health; deploy the
public BFF; create the separate Vercel project rooted at `apps/web`; configure
the final API rewrite target and BFF allowed origin; then smoke-test signup,
sign-in, MFA, upload, OCR processing, download, deletion, and account scoping
using synthetic records. The current free Render workspace cannot keep this
private-service architecture running without paid compute. Do not treat the
existing informational site as the product app.

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
