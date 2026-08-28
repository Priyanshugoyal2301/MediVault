# Reproducibility Gap Analysis

**Audit date:** 2026-08-28

---

## Summary

| Area | Status |
|------|--------|
| README setup path | Mostly documented — needs venv + all requirements.txt |
| `.env.example` | Complete — all ML flags documented |
| Python dependencies | Fragmented — per-service + per-model requirements |
| Node dependencies | Documented for `apps/web`; research-site separate |
| Database migrations | Documented — migration 004 untracked |
| Dataset acquisition | Good — synthetic JSONL in-repo |
| Model artifacts | Gap — must run `train.py` if flags enabled |
| Demo scripts | Gap — preflight Windows encoding issue |
| Feature flags | Well documented |
| Integration tests | Gap — no E2E HTTP suite |

---

## Gap register

| # | Issue | Impact | Severity | Recommended remediation |
|---|-------|--------|----------|-------------------------|
| G-01 | No aggregated dev requirements | Auth tests fail without `python-jose` | **High** | Add `requirements-dev.txt` |
| G-02 | Model artifacts not in git | Tests fail if flags on without train | **Medium** | Document train bootstrap |
| G-03 | Migration 004 untracked | Schema drift on fresh clone | **High** | Commit migration 004 |
| G-04 | No `.env` setup script | Manual copy step | **Low** | Add bootstrap script |
| G-05 | `demo_preflight.ps1` Unicode error | Script unusable on Windows PS | **Medium** | Replace em-dashes with ASCII |
| G-06 | Multi-terminal service launch | High setup friction | **Medium** | Document docker-compose path |
| G-07 | `PYTHONPATH=.` required | Import failures | **Medium** | Document in README |
| G-08 | HF models opt-in | Network needed for dense path | **Low** | Already documented |
| G-09 | No integration test suite | E2E regressions undetected | **Medium** | Add integration tests |
| G-10 | Duplicate root vs `docs/` benchmarks | Confusion | **Low** | Consolidate |
| G-11 | `00_PROJECT_STATE.md` stale header | Misleading status | **Medium** | Update before release |
| G-12 | Research site not in main README | Build path unclear | **Low** | Cross-link |
| G-13 | Unlimited-OCR needs endpoint | VLM path not reproducible | **Low** | Stub/fallback documented |
| G-14 | Bit-exact metrics | Cross-machine variance | **Low** | Document in checklist |

---

## Fresh clone checklist

```bash
git clone https://github.com/Priyanshugoyal2301/MediVault.git
cd MediVault
python -m venv .venv
# activate venv
pip install -r services/auth-service/requirements.txt
pip install -r services/health-service/requirements.txt
pip install -r services/ai-service/requirements.txt
pip install -r apps/api/requirements.txt
cp .env.example .env
docker-compose up -d postgres
cd infra/migrations && alembic upgrade head && cd ../..
export PYTHONPATH=.
pytest tests/phase1 tests/phase2 tests/phase3 tests/phase4 tests/phase5 tests/phase6 tests/phase7 tests/phase8 tests/phase9 -q
cd apps/web && npm install && npm run dev
```

---

## Verdict

**Prototype demo (flags off):** Achievable with documented manual steps.  
**Full ML platform (flags on):** Requires train scripts.  
**Bit-exact benchmarks:** Not guaranteed; snapshots committed as reference.
