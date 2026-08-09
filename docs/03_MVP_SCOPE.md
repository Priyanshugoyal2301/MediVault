# MVP SCOPE — LOCKED

> If a feature isn't listed under "In scope," it does not get built without an explicit new instruction from the project owner. Log any scope question in `DEV_LOG.md` under "Open Questions" rather than assuming.

## In scope (build this, in this order)

### 1. Medical Report Understanding
- Upload a report (PDF/image).
- OCR + parsing to extract structured values (test name, value, unit, reference range, date).
- Plain-language explanation per value, generated with an explicit template that never states a diagnosis (see tone rules in `01_PROJECT_CONTEXT.md` section 4).
- Acceptance: given a sample lab report PDF, the system extracts at least the common panels (CBC, lipid profile, thyroid, HbA1c) with correct value/unit/reference-range pairing, and produces a plain-language summary for each.

### 2. Health Timeline & Trend/Anomaly Detection
- Store extracted values over time per user, per test type.
- Detect trends/anomalies across 3+ historical points (rising/falling trend, out-of-range persistence) using the baseline (z-score) method first, then the trained model.
- Acceptance: given 3+ historical values for one test type, the system correctly flags a clear upward/downward trend and states it in plain language with no diagnostic claim.

### 3. Evidence-Based Q&A (RAG)
- User asks a free-text question.
- System retrieves from the curated knowledge base (+ the user's own report history where relevant).
- Answer is generated with visible citations back to the retrieved source(s).
- Acceptance: given a question about a value the user has on file, the answer references both a retrieved external source and the user's own historical value, with the source shown in the UI.

### 4. Deterministic Safety Layer (cross-cutting, not a standalone feature)
- A rules-based (non-ML) check runs on any free-text input for defined red-flag terms/patterns (e.g. chest pain + breathing difficulty).
- On trigger: show a fixed, non-AI-generated emergency-guidance message. This overrides normal AI response for that turn.
- Acceptance: red-flag phrases in test inputs always trigger the fixed message, deterministically, in <100ms, without going through the LLM.

## Explicitly out of scope for MVP (do not build)

- Symptom-to-disease prediction / diagnosis chatbot
- Prescription OCR / medicine reminders
- Family multi-profile accounts
- Emergency assistant beyond the deterministic safety layer above
- Biometric login, government ID verification
- Avatar / persona layer
- More than 2 languages (MVP = English + one regional language, to be specified)
- Wearable/IoT integration

## Definition of done for the MVP as a whole

- All four in-scope items meet their acceptance criteria above.
- Privacy/security baseline from `02_ARCHITECTURE.md` section 5 is implemented, not deferred.
- The evaluation numbers for the ML and IR components (see below) are recorded in `DEV_LOG.md`, not just "it works."

## Evaluation requirements (needed for the academic/ML+IR credibility, not optional polish)

- **Anomaly detection:** report precision, recall, F1, and false-alert rate on a held-out set (real or synthetic — state which).
- **Retrieval/RAG:** report Precision@K and/or nDCG for retrieval, plus a manually-labeled sample (even 30-50 Q&A pairs) for citation correctness and hallucination rate.
- Both must be logged in `DEV_LOG.md` with the dataset used and its known limitations stated plainly — do not overstate confidence in synthetic or small datasets.
