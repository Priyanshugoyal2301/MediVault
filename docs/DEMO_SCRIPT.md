# MediVault — Judge Demo Scripts

**Rule:** Never depend on OCR for the main path. Use **LIPID Demo** seed.

---

## Preflight (5 minutes before stage)

```powershell
# From repo root, with .env configured
docker-compose up -d postgres
alembic -c infra/migrations/alembic.ini upgrade head

$env:MEDIVAULT_FAST_KB="1"   # fast KB embeddings — no HuggingFace download

# Terminals (repo root):
python scripts/run_service.py services.auth_service.main:app 8001
python scripts/run_service.py services.health_service.main:app 8002
python scripts/run_service.py services.ai_service.main:app 8003
python scripts/run_service.py apps.api.main:app 8000
cd apps/web; npm run dev
```

**Port conflicts:** set `POSTGRES_PUBLISH_PORT=5433` + `POSTGRES_PORT=5433` if 5432 is busy; remap auth to e.g. `8011` and set `AUTH_SERVICE_URL=http://127.0.0.1:8011`. For preflight with overrides: `$env:MEDIVAULT_AUTH_PORT=8011; $env:MEDIVAULT_WEB_PORT=3002`. Docker stack: `docker-compose up --build` (rebuild after AI Dockerfile changes).

**Automated:**

```powershell
powershell -File scripts/demo_preflight.ps1
powershell -File scripts/smoke_demo.ps1
```

**Health checks:**

```text
GET http://127.0.0.1:8000/health          → api-gateway ok
GET http://127.0.0.1:8003/health          → kb_ready:true, kb_chunks > 0
```

**Warm the path once (private):** Register → Upload → LIPID Demo → Timeline LDL → click each Q&A chip.

---

## 3-minute demo (tight)

| Time | On screen | Say |
|------|-----------|-----|
| 0:00–0:25 | Auth | “Scattered lab PDFs. People Google symptoms and get noise. MediVault is a private vault that explains values, tracks trends, and answers with citations — without diagnosing.” |
| 0:25–0:40 | Network tab briefly | “Real JWT through our BFF. Browser never sends X-User-ID.” Click **Register Now** → `judge@example.com` / `password123` |
| 0:40–1:20 | Upload → **LIPID Demo** | “Deterministic seed — same every time. Plain-language, non-diagnostic explanations.” |
| 1:20–1:55 | Timeline → **LDL Cholesterol** | “Rising series. Causal statistical monitor (leave-last-out z, %Δ, CUSUM) on *this user’s* points — not a global clinical model.” |
| 1:55–2:35 | Q&A chips | Click **What does high LDL mean?** (citations) → **What was my LDL?** (personal vault) |
| 2:35–2:55 | Safety chip | **I have chest pain and trouble breathing** → fixed emergency copy, before RAG |
| 2:55–3:00 | Close | “Local OCR intent, owner-scoped DB, safety-first RAG. Prototype — not a doctor.” |

---

## 5-minute demo (with architecture)

Same as 3-minute, plus:

| Time | Add |
|------|-----|
| +0:30 | One architecture slide / terminal: Client → BFF (JWT) → Auth/Health; Health→AI internal |
| +0:30 | Mention magic-byte MIME + internal service key on AI parse |
| +0:20 | Optional Hindi locale toggle on one explanation |
| +0:20 | Honest eval: BM25 Hit@5/MRR; statistical monitor with ablation vs IF |

---

## Exact clicks (zero improvisation)

1. Open `http://localhost:3000`
2. **Register Now** → email `judge@example.com` → password `password123` → submit  
   - If 409: switch to Sign In with same credentials
3. Sidebar **Upload & Parse**
4. Click **LIPID Demo** (wait for table + explanations)
5. Sidebar **Timeline** → select **LDL Cholesterol** (wait for bars + summary)
6. Sidebar **Q&A** → click chips in order (Send each):
   1. `What does high LDL mean?`
   2. `What was my LDL?`
   3. `I have chest pain and trouble breathing`
7. Stop. Do **not** upload a random PDF unless rehearsed.

---

## Do NOT say

- “HIPAA compliant” / “production ready”
- “Precision@5 82% on MiniLM”
- “We diagnose anaemia / diabetes”
- “Trained IsolationForest model in production” (removed — we use statistical_monitor)

## DO say

- “Template RAG with citations — deliberately not a free-form LLM”
- “Safety regex runs before retrieval”
- “Demo seed for reliability; real PDF upload is wired”
- “BFF injects trusted identity from JWT”

## Fallback

1. Restart AI if `kb_ready` is false  
2. Stick to seed + safety even if anomaly 503s  
3. Curl path in DEMO_SCRIPT appendix if UI dies
