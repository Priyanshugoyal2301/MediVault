# Web Frontend — `apps/web`

## What this service owns

The React application for patient and clinician workflows. This is the product
web app; `apps/research-site` is a separate project-information site.

## Tech

React 18, Vite, and JavaScript modules.

## Responsibilities

- Report upload flow (Feature 1)
- Timeline / trend view (Feature 2)
- Q&A chat with visible citations (Feature 3)
- Always surfaces the deterministic safety-layer message verbatim when the API returns one — must never suppress or reword it.

## API

Communicates exclusively through `apps/api` (the BFF/Gateway). Never calls `auth-service`, `health-service`, or `ai-service` directly.

## Local development

From this directory, run `npm ci` and `npm run dev`. The Vite server proxies
same-origin API paths to the local BFF at `http://127.0.0.1:8000`.

## Vercel deployment

Create a separate Vercel project for this app with the repository root set to
`apps/web`. `vercel.json` builds the Vite app and rewrites `/api/*` to the
public API gateway. The frontend defaults to `/api` in production, keeping the
HttpOnly session cookie same-origin. Update the rewrite destination when the
Render API service URL is assigned. The API gateway must allow the Vercel app
origin in `CORS_ORIGINS`.

The UI talks only to the public BFF. Auth, health, and AI service addresses and
credentials must never be placed in `VITE_*` variables or browser bundles.
