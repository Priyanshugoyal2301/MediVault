# Judge Q&A Guide (50 questions)

Format: **Q** → Short (30s) → Technical (2 min) → Evidence

---

### Architecture

**1. Why microservices?**  
Short: Clear ownership boundaries for a small team.  
Tech: Auth/health/AI separate FastAPI apps; BFF is the browser edge. Shared Postgres for MVP speed.  
Evidence: `apps/api/`, `services/*/main.py`, `docs/02_ARCHITECTURE.md`

**2. Isn’t this a modular monolith?**  
Short: Operationally yes for MVP; folders enforce boundaries.  
Tech: Health can import AI as fallback; primary path is HTTP.  
Evidence: `health-service/routers/qa.py`

**3. What does the BFF do?**  
Short: JWT verify + trusted identity injection + proxy.  
Tech: Strips client `X-User-ID`, sets from JWT `sub`, does not proxy AI.  
Evidence: `apps/api/routers/proxy.py`, `apps/api/core/auth.py`

**4. Why not expose AI publicly?**  
Short: Internal OCR/parse/anomaly surface.  
Tech: Compose binds AI to localhost; optional `X-Internal-Key`.  
Evidence: `docker-compose.yml`, `ai-service/core/internal_auth.py`

**5. Where is state stored?**  
Short: Postgres for users/reports/timeline; files on local disk.  
Tech: Alembic 001–004; `LocalStorage` under `STORAGE_LOCAL_PATH`.  
Evidence: `infra/migrations/`, `storage/local_storage.py`

### ML / Anomaly

**6. What anomaly model do you use?**  
Short: Causal statistical monitor (leave-last-out z, %Δ, CUSUM) — IsolationForest removed.  
Tech: thresholds z≥2, |%Δ|≥25%, CUSUM k=0.5σ / h=4σ; method=`statistical_monitor`.  
Evidence: `ai-service/anomaly/model.py`

**7. Why not a deep model?**  
Short: n is tiny (3–10 points); deep models overfit and hurt reliability.  
Tech: Statistical monitor is explainable for judges (lab-QC inspired).  
Evidence: `anomaly/zscore.py`, `anomaly/model.py`, `detector.py`

**8. What’s your baseline?**  
Short: Whole-series z-score + OLS slope for trend; causal monitor for last-point flags.  
Tech: Ablation vs legacy IsolationForest in synthetic eval script.  
Evidence: `anomaly/detector.py`, `generate_synthetic_anomaly_data.py`

**9. Evaluation dataset?**  
Short: Synthetic Hb series for anomaly scripts; not MIMIC.  
Tech: Disclose circularity risk of planted spikes.  
Evidence: `data/datasets/generate_synthetic_anomaly_data.py`

**10. Can you show metrics?**  
Short: Anomaly F1 on synthetic is directional only.  
Tech: Do not oversell; prefer live LDL trend demo.  
Evidence: `docs/PRESENTATION_CLAIMS.md`, historical eval notes in `docs/PLAN_C_REPORT.md` / Plan B docs

### RAG / Embeddings

**11. Do you use an LLM?**  
Short: No free-form LLM for answers — template synthesizer.  
Tech: Retrieve chunks → paste/cite sentences; safer for health.  
Evidence: `rag/synthesizer.py`

**12. Which embeddings / retriever?**  
Short: Default BM25+intent (Plan B). Dense MiniLM only if `MEDIVAULT_USE_DENSE=1` and FAST_KB off.  
Tech: Tiny curated KB (~13 chunks) — lexical IR is the honest default.  
Evidence: `rag/bootstrap.py`, `rag/retriever.py`, `rag/bm25.py`

**13. What is Precision@5 82%?**  
Short: Retracted (was MD5 Hit@5 mislabeled). Current harness reports Hit@5/MRR on BM25.  
Tech: `--use-dense` for hybrid bake-off; still Hit@5 ≠ classical P@5.  
Evidence: `data/datasets/evaluate_rag.py`, `docs/PRESENTATION_CLAIMS.md`

**14. How do citations work?**  
Short: Synthesizer attaches sources for retrieved chunks.  
Tech: Not full claim-level entailment verification.  
Evidence: `rag/synthesizer.py`

**15. Hallucination rate?**  
Short: We track tone-violation substrings; not generative hallucination.  
Tech: Templates + extractive paste reduce free-form invention.  
Evidence: `evaluate_rag.py`

**16. Is pgvector used live?**  
Short: Table exists; live Q&A uses in-memory chunks at startup.  
Tech: Future: query `knowledge_documents`.  
Evidence: migration 003, `rag/retriever.py`

### OCR / Parsing

**17. How does OCR work?**  
Short: pdfplumber text layer first, else Tesseract eng+hin.  
Tech: Classical pipeline; handwriting weak.  
Evidence: `ocr/tesseract_backend.py`

**18. What panels?**  
Short: CBC, lipid, thyroid, HbA1c via regex.  
Tech: `parsers/patterns.py`  
Evidence: same

**19. Why demo seed?**  
Short: Deterministic judging; OCR is environment-sensitive.  
Tech: `POST /reports/demo/seed` writes values+timeline.  
Evidence: `health-service/routers/reports.py`

**20. File type safety?**  
Short: Magic-byte sniffing, not just Content-Type.  
Tech: PDF/JPEG/PNG/TIFF/WEBP signatures.  
Evidence: `reports.py` `_sniff_mime`

### Security

**21. How is identity enforced?**  
Short: JWT → BFF → trusted header → ScopedRepository.  
Tech: Client cannot set owner id through BFF.  
Evidence: `apps/api/core/auth.py`, `base_repository.py`

**22. Can I hit health with spoofed header?**  
Short: If ports are exposed, yes — we bind localhost and require BFF for UI.  
Tech: Disclose residual risk if someone tunnels to :8002.  
Evidence: `docker-compose.yml`

**23. Is /parse open?**  
Short: Path allowlist + optional internal key.  
Tech: Must resolve under `STORAGE_LOCAL_PATH`.  
Evidence: `internal_auth.py`, `parse.py`

**24. Password policy?**  
Short: Min length 8 on register.  
Tech: bcrypt via passlib.  
Evidence: `auth.py` RegisterRequest

**25. Rate limiting?**  
Short: Not in MVP; laptop demo only.  
Tech: Future: SlowAPI/gateway limits.  
Evidence: honest gap

**26. Secrets?**  
Short: `.env` local; never commit.  
Tech: Shared JWT secret across auth+BFF.  
Evidence: `.env.example`

### Privacy / Healthcare

**27. HIPAA?**  
Short: Not claiming HIPAA compliance.  
Tech: India-first consumer prototype; DPDP-minded design goals.  
Evidence: `PRESENTATION_CLAIMS.md`

**28. Do you diagnose?**  
Short: No — “commonly associated”, discuss with doctor.  
Tech: Tone tests + safety layer.  
Evidence: `explainer/templates.py`, `safety/red_flags.py`

**29. Emergency handling?**  
Short: Deterministic regex before RAG; fixed copy.  
Tech: Cardiac/GI/vision/stroke/suicide categories.  
Evidence: `safety/red_flags.py`, tests

**30. Data retention / delete?**  
Short: Report DELETE cascades; full account erase API not done.  
Tech: Disclose.  
Evidence: `reports.py` delete

**31. Encryption at rest?**  
Short: Not in this prototype.  
Tech: Local disk plaintext files.  
Evidence: `local_storage.py`

### Product / Business

**32. Who is the user?**  
Short: Individuals with scattered Indian lab PDFs.  
Tech: Literacy + longitudinal memory gap.  
Evidence: `docs/01_PROJECT_CONTEXT.md`

**33. Competition?**  
Short: Practo/lab portals store results; we add explain+trend+cited Q&A+safety.  
Tech: Differentiation is the combo + non-diagnostic stance.  
Evidence: pitch

**34. Monetization?**  
Short: Out of scope for hackathon; B2C freemium or B2B clinic white-label later.  
Tech: —

**35. Why Hindi?**  
Short: India primary; phrase-assisted bilingual templates.  
Tech: Not full NMT.  
Evidence: `synthesizer.py`

### Scalability / Reliability

**36. Scale to 1M users?**  
Short: Not this architecture as-is.  
Tech: Need queue, object storage, horizontal AI workers.  
Evidence: BackgroundTasks note in `reports.py`

**37. OCR job durability?**  
Short: In-process BackgroundTasks — demo uses seed.  
Tech: Crash can leave pending.  
Evidence: `reports.py` docstring

**38. Cold start?**  
Short: MiniLM download risk; we ship `MEDIVAULT_FAST_KB=1`.  
Tech: `/health` shows `kb_embedder`.  
Evidence: `rag/bootstrap.py`

**39. Observability?**  
Short: Redacting logger; no APM.  
Tech: Enough for hackathon.  
Evidence: `packages/shared-utils/logging.py`

### Frontend / UX

**40. Is the UI mocked?**  
Short: No — live APIs via Vite proxy.  
Tech: `api.js` + BFF.  
Evidence: `apps/web/src/api.js`, `vite.config.js`

**41. Accessibility?**  
Short: Basic labels/chips; not full WCAG AA.  
Tech: Honest gap.  
Evidence: AuthView labels, QA chips

**42. Offline?**  
Short: No.  
Tech: —

### Future work

**43. What’s next?**  
Short: Durable queue, encrypt-at-rest, audit logs, real MiniLM eval, WCAG.  
Tech: See PROJECT_STATE partial list.  
Evidence: `docs/PRESENTATION_CLAIMS.md`, `README.md`

**44. ABHA / hospital integration?**  
Short: Out of MVP scope.  
Tech: —

**45. Generative LLM later?**  
Short: Only behind stronger grounding/safety; templates first by design.  
Tech: —

### Gotchas judges love

**46. Show me the Network tab.**  
Short: Bearer to :3000 proxy → BFF; no X-User-ID.  
Evidence: live

**47. What if I ask for a diagnosis?**  
Short: Templates hedge; safety may not catch all; we never output “you have X” by policy in generators.  
Tech: KB may still mention disease names in educational text — we disclose.  
Evidence: KB files, synthesizer

**48. Why IsolationForest contamination 0.1?**  
Short: Heuristic for short series; can raise FAR — we pair with z-score messaging.  
Evidence: `model.py`

**49. Are tests green?**  
Short: Large unit suite; integration empty; auth needs jose installed.  
Evidence: `tests/unit/`, `tests/integration/.gitkeep`

**50. Why should you win?**  
Short: Working end-to-end health vault with security-aware BFF, honest ML claims, and a safety-first Q&A demo that never improvises emergencies.  
Tech: Deterministic seed + live anomaly + citations + regex safety in <3 minutes.  
Evidence: this repo + DEMO_SCRIPT
