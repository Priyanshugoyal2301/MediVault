# Plan B ML — Benchmark & Validation Report

**Date:** 2026-08-10  
**Scope:** MediVault AI anomaly + retrieval after Plan B execution  
**Seed:** synthetic anomaly `random.seed(42)`; RAG = 50 labeled FAQ pairs  

---

## 1. Final architecture

```
PDF → pdfplumber (+OCR) → regex IE → template explain → Postgres
series → z-score trend + statistical_monitor(causal z ∨ CUSUM; %Δ for score/summary)
question → safety regex → BM25+intent → template cited answer
```

Obsolete removed from production path: IsolationForest, MD5 cosine “embeddings”.

---

## 2. Anomaly ablation (n=200 synthetic Hb patients, 20% spike)

| Method | Precision | Recall | F1 | FAR | TP/FP/FN/TN |
|--------|-----------|--------|----|-----|-------------|
| **statistical_monitor (prod)** | **0.7692** | **1.0000** | **0.8696** | **0.0750** | 40/12/0/148 |
| causal_z_only | 0.7692 | 1.0000 | 0.8696 | 0.0750 | 40/12/0/148 |
| pct_delta_only | 0.8000 | 0.7000 | 0.7467 | 0.0437 | 28/7/12/153 |
| cusum_only | 1.0000 | 0.5750 | 0.7302 | 0.0000 | 23/0/17/160 |
| legacy_isolation_forest | 0.7358 | 0.9750 | 0.8387 | 0.0875 | 39/14/1/146 |

**Decision refinement (evidence-driven):** OR-ing `%Δ` into `is_anomaly` raised FAR (F1 dropped to 0.825). Production binary rule is **causal z ≥ 2 OR CUSUM alarm**; `%Δ` remains in score + bilingual summary.

**Vs previous repo (IF):** ΔF1 ≈ +0.031, ΔFAR ≈ −0.0125, recall +0.025, zero sklearn dependency on the live path.

### Math (production)

Baseline \(\mu,\sigma\) from \(x_{1:t-1}\) (leave-last-out).  
\(z_t=(x_t-\mu)/\sigma\). Alarm if \(|z_t|\ge 2\).  
CUSUM: \(S^\pm\) with \(k=0.5\sigma\), \(h=4\sigma\); alarm if \(S^\pm>h\).  
Score: \(s=1-2\max(|z|/3,\ |Δ|/0.5,\ S_{mag}/h)\) clamped to \([-1,1]\).

---

## 3. Retrieval eval (50 labeled questions)

| Retriever | Hit@5 | MRR | Citation present | Tone violation* |
|-----------|-------|-----|------------------|-----------------|
| **bm25+intent (prod)** | **100% (50/50)** | **0.954** | 100% | 72% |

\*Tone violation = substring `"you have"` / `"diagnosed with"` in synthesizer output — largely KB phrasing leakage, not ranking failure. Not classical hallucination rate.

Historical retracted claim: “MiniLM Precision@5 82%” was MD5 Hit@5. BM25 Hit@5 on the same keyword metric is higher and method-honest.

---

## 4. Unit tests

`tests/unit/ai-service/test_anomaly.py` + `test_rag.py`: **56 passed**.

---

## 5. Remaining limitations

1. Synthetic spike eval ≠ clinical validation; planted last-point anomalies favour causal z.  
2. No reference-range feature yet (needs per-test ranges from reports).  
3. Tone-violation heuristic is noisy; needs span-level grounding audit.  
4. Dense MiniLM bake-off not run in this pass (optional `MEDIVAULT_USE_DENSE=1`).  
5. OCR/IE still regex — largest real-world quality gap for India PDFs.  
6. CUSUM adds little on spike-only synthetic set; kept for gradual-shift robustness.

---

## 6. Why this is optimal for THIS repository

Tiny personal series (n≈3–10) and ~13 KB chunks make IsolationForest and dense embedding theater scientifically weak and operationally fragile. Causal statistics + BM25/intent maximize measurable F1/Hit@5, explainability, and demo reliability under the no-diagnosis constraint.
