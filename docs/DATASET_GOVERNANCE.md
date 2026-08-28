# Dataset Governance — MediVault AI

**Audit date:** 2026-08-28  
**Scope:** All data under `datasets/`, `data/datasets/`, and `data/knowledge-base/`  
**Principle:** No PHI. Synthetic-first. Licensed corpora via env paths only.

---

## 1. Governance rules

1. **Never commit** real patient records, hospital exports, or credentialed corpora (MIMIC, NHANES, etc.).
2. **Prefer committing** small synthetic JSONL fixtures required for `train.py` / `evaluate.py` reproducibility.
3. **Regenerated metrics** (`*_latest.json`) stay out of git — reproduce via evaluate scripts.
4. **Large public datasets** ship as manifests + download scripts, not raw blobs.
5. Every ML task folder must have `README.md` and, where applicable, `LICENSING.md`.

---

## 2. Dataset inventory

| Dataset | Location | Format | Approx. size | Source | License / redistribution | Synthetic? | PHI? | Train | Eval | Demo | Strategy |
|---------|----------|--------|--------------|--------|------------------------|------------|------|-------|------|------|----------|
| Synthetic anomaly labs | `datasets/anomaly_detection/` | JSONL | ~682 KB | Generator scripts | Project-owned synthetic | Yes | No | Yes | Yes | No | **COMMIT** JSONL + LICENSING |
| Synthetic forecasting | `datasets/forecasting/` | JSONL | ~1.15 MB | Generator | Project-owned synthetic | Yes | No | Yes | Yes | No | **COMMIT** |
| Synthetic health score | `datasets/health_score/` | JSONL | ~775 KB | Generator | Project-owned synthetic | Yes | No | Yes | Yes | No | **COMMIT** |
| Synthetic risk prediction | `datasets/risk_prediction/` | JSONL | ~1.06 MB | Generator | Project-owned synthetic | Yes | No | Yes | Yes | No | **COMMIT** |
| Test normalization pairs | `datasets/test_normalization/` | JSONL + JSON | ~274 KB | Synthetic + LOINC subset | LOINC subset is reference data; no full UMLS | Mostly | No | Yes | Yes | No | **COMMIT** — document LOINC subset scope |
| Retrieval benchmark | `datasets/retrieval/` | JSONL | ~2 KB | Synthetic KB queries | Project-owned | Yes | No | Yes | Yes | No | **COMMIT** |
| Document parsing (placeholder) | `datasets/document_parsing/` | — | empty | N/A | N/A | — | — | Future | Future | No | **COMMIT** `.gitkeep` + README only |
| Image quality (placeholder) | `datasets/image_quality/` | — | empty | Generator optional | Synthetic when generated | Yes | No | Yes | Yes | No | **COMMIT** README + LICENSING |
| Phase eval snapshots | `datasets/evaluation/*_latest.json` | JSON | ~35 KB | `evaluate.py` output | Regenerated | N/A | No | No | Yes | No | **IGNORE** (gitignored) |
| Platform benchmark snapshots | `datasets/evaluation/platform_*.json`, `ocr_phase1a_bench.json` | JSON | ~55 KB | Platform scripts | Project-owned metrics | N/A | No | No | Yes | Yes | **COMMIT** as audit trail |
| Plan B RAG eval | `data/datasets/` (scripts) | — | scripts only | In-repo harness | Project-owned | Yes | No | No | Yes | Yes | **COMMIT** scripts |
| Plan C IE fixtures | `data/datasets/plan_c/` | JSON/py | ~80 KB | Hand-authored layouts | Project-owned | Yes | No | No | Yes | No | **COMMIT**; review `results_latest.json` |
| Knowledge base text | `data/knowledge-base/*.txt` | TXT | ~20 KB | Curated educational | SOURCE headers in files | No (guidelines) | No | N/A | Yes | Yes | **COMMIT** |
| MIMIC-IV | External | — | — | PhysioNet (credentialed) | **Not redistributed** | Real (if used) | Potential | Optional offline | Optional | No | **DO NOT COMMIT** — `MIMIC_*_PATH` env |
| NHANES | External | — | — | CDC public (restricted use) | **Not redistributed** | Real | Potential | Optional offline | Optional | No | **DO NOT COMMIT** — `NHANES_*_PATH` env |
| eICU | External | — | — | Credentialed | **Not redistributed** | Real | Potential | Optional | Optional | No | **DO NOT COMMIT** |
| DocLayNet / PubLayNet | External | — | — | Licensed CV corpora | **Not redistributed** | Real docs | No PHI assumed | Optional OCR eval | Optional | No | **DO NOT COMMIT** — env paths only |

---

## 3. Licensing stubs (present)

| File | Declares |
|------|----------|
| `datasets/anomaly_detection/LICENSING.md` | Synthetic yes; NHANES/MIMIC env-only |
| `datasets/forecasting/LICENSING.md` | Synthetic yes; MIMIC/eICU env-only |
| `datasets/health_score/LICENSING.md` | Synthetic yes; NHANES/MIMIC env-only |
| `datasets/risk_prediction/LICENSING.md` | Synthetic yes; MIMIC/NHANES env-only |
| `datasets/retrieval/LICENSING.md` | Synthetic KB |
| `datasets/image_quality/LICENSING.md` | Synthetic degradations; optional external CV sets |

---

## 4. `.gitignore` dataset rules (current)

```gitignore
datasets/**/*.csv
datasets/**/*.parquet
datasets/**/*.pkl
datasets/**/*.zip
datasets/evaluation/*_latest.json
!datasets/**/.gitkeep
!datasets/**/README.md
```

**Gap:** JSONL synthetic files are **not** ignored (intentional for reproducibility). Total committed dataset payload is approximately **3.5 MB** — acceptable for git without LFS.

---

## 5. Recommended actions before release

| Priority | Action |
|----------|--------|
| P1 | Commit synthetic JSONL + README + LICENSING per task folder |
| P1 | Do **not** commit `*_latest.json` eval outputs (already ignored) |
| P2 | Add `data/datasets/plan_c/results_latest.json` to `.gitignore` if regenerated |
| P2 | Add `scripts/download_datasets.py` manifest (future) for any large external sets |
| P3 | Document `MIMIC_*_PATH` / `NHANES_*_PATH` in `docs/DATASET_REFERENCE.md` (already present) |

---

## 6. Legal redistribution summary

| Can redistribute in public repo? | Items |
|----------------------------------|-------|
| **Yes** | All synthetic JSONL, LOINC subset, KB text, evaluation metric JSON snapshots, Plan C fixtures |
| **No** | MIMIC, NHANES, eICU, DocLayNet, PubLayNet, any real patient exports |
| **Conditional** | LOINC subset — cite LOINC attribution; do not ship full UMLS |
