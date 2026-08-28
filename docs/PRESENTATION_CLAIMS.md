# Allowed claims (judge-safe)

Use these lines. Do not improvise stronger ones.

## One-liner
MediVault turns lab PDFs into an owner-scoped health vault with plain-language explanations, personal trend scoring, and citation-backed Q&A — with a deterministic emergency safety layer and **no diagnosis**.

## Architecture
- Browser → FastAPI BFF validates JWT and injects trusted user identity.
- Health service owns reports/timeline; AI service is internal (parse, anomaly, Q&A).
- Postgres stores owner-scoped rows; ScopedRepository enforces `owner_id` on queries.

## ML / AI (conservative)
- OCR: Tesseract + pdfplumber (classical), not a trained neural OCR in-repo.
- Extraction: regex panels (CBC, lipid, thyroid, HbA1c).
- Explanations: bilingual templates with non-diagnostic tone rules.
- Trends: z-score trend + causal statistical monitor (leave-last-out z, %Δ, CUSUM) on the user’s short series — not a persisted clinical model.
- Q&A: BM25 + intent retrieval + **template synthesizer** (not a generative LLM chat model). Optional dense hybrid via `MEDIVAULT_USE_DENSE=1`.
- Eval: keyword Hit@5 / MRR harness on the true retriever (BM25 by default).

## Security / privacy
- JWT auth; BFF strips client `X-User-ID`.
- AI parse restricted to storage root; optional internal service key.
- Magic-byte MIME checks on upload.
- Local OCR by design (dev); no cloud OCR API in the default path.
- **Not** claiming HIPAA certification or full encrypt-at-rest in this prototype.

## Product
- Demo seed panels for reliable judging; real PDF upload is wired for stretch.
- Hindi support is phrase-assisted, not a full NMT engine.
