# AGENT OPERATING RULES

> These rules govern how you (the building agent) work in this repo. They apply on top of, not instead of, whatever general coding practices you already follow.

## 1. Context discipline

- Before starting any task, read `01_PROJECT_CONTEXT.md`, `02_ARCHITECTURE.md`, and `03_MVP_SCOPE.md` in this `/docs` folder if you haven't already this session.
- If a requested change conflicts with the locked MVP scope or the architecture, say so explicitly before building — do not silently build outside scope.

## 2. No dead code, no parallel implementations

- When you replace an existing implementation (a function, endpoint, component, model pipeline), **delete the old one in the same change** — do not leave it commented out or renamed to `_old`/`_v1`/`_backup`. Version control already preserves history; the codebase should not.
- If you are unsure whether an old piece of code is still used anywhere, search the codebase for references before deleting. If it has zero references after your change, remove it.
- Never keep two competing ways of doing the same thing (e.g. two auth middlewares, two report parsers) "just in case." Pick one, migrate everything to it, delete the other.
- If a piece of code turns out to be a dead end (an approach that didn't work, an experiment that failed), remove it once you've confirmed it's not useful — don't let it linger and become confusing clutter for a future session (including future-you).

## 3. Document meaningful decisions

- Record architectural tradeoffs, dataset choices, and evaluation numbers in the relevant docs under `/docs` (for example `CONFIGURATION.md`, `FEATURE_FLAGS.md`, `MODEL_REGISTRY.md`, or a PR description) — not only in chat.
- Prefer updating the README or targeted docs when user-facing behavior changes.

## 4. Scope and safety guardrails

- Do not add features from the "explicitly out of scope" list in `03_MVP_SCOPE.md` without an instruction that names the feature directly.
- Never let the ML/LLM layer bypass the deterministic safety layer described in `03_MVP_SCOPE.md` section on the safety layer — that logic must remain rule-based and must run before any AI-generated response is shown to the user.
- Never introduce a code path that outputs a diagnostic claim (e.g. "you have X condition"). If you notice a prompt or template that could produce one, flag and fix it even if it wasn't the task you were asked to do.
- Do not log or print raw health data (report values, user answers) to application logs. Redact before logging.

## 5. Quality bar

- Every new endpoint/function that touches user health data needs a test that checks it's scoped to the requesting user (no cross-user data leakage).
- Every model or retrieval component you build or change needs evaluation numbers recorded under `validation/` or `docs/benchmark_*` — "it seems to work" is not sufficient.
- Prefer small, reviewable changes over large multi-feature commits.

## 6. When in doubt

- If a request is ambiguous about scope, architecture, or safety behavior, state your assumption explicitly in the PR or task notes before baking it into code.
