# Web Frontend — `apps/web`

## What this service owns

The web UI for MediVault AI (web-first MVP; mobile wrapper deferred to post-MVP).

## Tech

React or Next.js — to be finalised at Feature 3 (Q&A UI build), but scoped to stay compatible with both.

## Responsibilities

- Report upload flow (Feature 1)
- Timeline / trend view (Feature 2)
- Q&A chat with visible citations (Feature 3)
- Always surfaces the deterministic safety-layer message verbatim when the API returns one — must never suppress or reword it.

## API

Communicates exclusively through `apps/api` (the BFF/Gateway). Never calls `auth-service`, `health-service`, or `ai-service` directly.

## Status

Placeholder at scaffold stage — populated starting at Feature 1 frontend sprint.
