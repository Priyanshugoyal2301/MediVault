# Developer rules

Conventions for anyone changing MediVault. Follow these in addition to normal engineering practice.

## 1. Context discipline

- Before large changes, read `01_PROJECT_CONTEXT.md`, `02_ARCHITECTURE.md`, and `03_MVP_SCOPE.md` in `/docs`.
- If a request conflicts with locked MVP scope or architecture, say so before building — do not silently expand scope.

## 2. No dead code, no parallel implementations

- When replacing an implementation, delete the old path in the same change (no `_old` / `_v1` leftovers).
- Search for references before deleting; remove unused code once confirmed unused.
- Do not keep two competing ways to do the same thing. Pick one, migrate, delete the other.

## 3. Document meaningful decisions

- Record architectural tradeoffs, dataset choices, and evaluation numbers in `/docs` (or the PR description).
- Update the README or targeted docs when user-facing behavior changes.

## 4. Scope and safety guardrails

- Do not add features from the “explicitly out of scope” list in `03_MVP_SCOPE.md` without an explicit request.
- Never let the ML/LLM layer bypass the deterministic safety layer — it must stay rule-based and run before AI responses reach the user.
- Never introduce a code path that asserts a diagnosis (e.g. “you have X condition”).
- Do not log or print raw health data; redact before logging.

## 5. Quality bar

- Every new endpoint that touches user health data needs a test that it is scoped to the requesting user.
- Model or retrieval changes need evaluation numbers under `validation/` or `docs/benchmark_*`.
- Prefer small, reviewable commits.

## 6. When in doubt

- State assumptions about scope, architecture, or safety in the PR or task notes before baking them into code.
