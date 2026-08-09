# PROJECT CONTEXT — READ THIS FIRST

> This file is the single source of truth for what this project is and why it exists.
> Read this before writing any code. If a task request conflicts with this file, flag the conflict — do not silently override it.

## 1. What we are building

**Working name:** MediVault AI (placeholder — replace once finalized)

**One-line description:**
An AI layer that turns a person's scattered medical reports and health data into an understandable, evidence-cited, remembered health record — without ever issuing a diagnosis.

**What this is NOT:**
- Not an AI doctor.
- Not a symptom-to-disease predictor.
- Not a general-purpose health chatbot.

## 2. The problem (the real gap)

Healthcare interaction today is binary: "I'm fine" or "I need a doctor." Between those two states, people are on their own to interpret lab reports, notice trends across years of tests, and find trustworthy answers to specific questions. Google gives noise. Generic chatbots have no memory of the person's history and no citations. Doctors are expensive and not always immediately reachable.

## 3. The USP — the thing not currently solved

Existing tools solve **one** of these in isolation. Nobody combines all three into a persistent, cited, longitudinal system:

1. **Longitudinal memory** — most tools answer one question at a time with no memory of the user's history across years of reports.
2. **Trend-based anomaly detection** — flagging *patterns over time* ("your LDL has risen for 4 consecutive tests") rather than single-point values, which is closer to how clinicians actually reason but is absent from consumer tools.
3. **Evidence-grounded, cited answers** — every explanation traceable to a specific retrieved medical source, not a black-box LLM answer.

This combination — memory + trend detection + cited retrieval — is the defensible core. Everything else (family accounts, biometrics, ID verification, emergency assist) is a future layer built on top of this core, not a substitute for it.

## 4. Non-negotiable product principles

- **Never output a diagnosis or a definitive medical claim.** Always frame as "commonly associated with," "may be worth discussing with a professional."
- **Every AI-generated health explanation must show what it's based on** (retrieved source, or "based on your own historical data") — no unsourced claims.
- **Safety-critical logic (red-flag symptoms) is deterministic rule-based code, not model output.** The LLM/ML layer never has the final say on an emergency escalation.
- **User owns their data.** Delete must actually delete — from the primary store, embeddings, and derived aggregates, not just hide from the UI.
- **Ship narrow, ship real.** MVP is intentionally small. See `03_MVP_SCOPE.md` — do not build outside that scope without an explicit instruction.

## 5. Target user (for this MVP)

An individual (initially India-focused, English + one regional language) who periodically gets lab tests done and wants to understand results, track them over time, and ask grounded follow-up questions. Not built for clinicians in v1.

## 6. Roadmap beyond MVP (context only — do not build yet)

These are known future layers. Build the MVP so these can be added without a rewrite:
- Biometric login / device-based auth
- Government/health-ID verification (e.g. ABHA integration in India)
- Avatar / conversational persona layer on top of the existing chat
- Family multi-profile accounts
- Prescription OCR and medicine reminders
- Multilingual expansion beyond the MVP's 2 languages

Architecture decisions in `02_ARCHITECTURE.md` explain how the MVP stays compatible with these additions.

## 7. Reference documents this project was distilled from

The product direction went through two prior iterations (a broad 7-module concept, then a narrowed "one exceptional workflow" version). This file and `03_MVP_SCOPE.md` represent the final, locked-in scope. Do not resurrect the discarded modules (disease prediction, symptom diagnosis chatbot, emergency assistant, family accounts) inside the MVP — they are explicitly deferred, listed in section 6 above.
