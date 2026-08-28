# PROJECT PHOENIX — Plan C Report

**Date:** 2026-08-10  
**Lab entrypoint:** `python data/datasets/plan_c/run_plan_c_lab.py`  
**Raw results:** `data/datasets/plan_c/results_latest.json`

---

## 1. Dataset discovery report

| Rank | Dataset | License | Access | ROI for MediVault |
|------|---------|---------|--------|-------------------|
| 1 | **Synthetic India lab fixtures (in-repo)** | Project | Yes | **Highest** — controlled IE gold |
| 2 | Eka Care medical_records_parsing_validation_set | MIT (gated HF) | Gated | India lab/Rx images for OCR/IE eval |
| 3 | NidaanKosha-100k | CC-BY-SA-4.0 | Open HF | Alias/unit/range coverage (no images) |
| 4 | LiveQA Medical / MedQuAD | Research / CC-BY | Open | Harder FAQ eval (Hit@5 already saturated) |
| 5 | NHANES labs | Public domain | Open | Population sanity, not personal series |
| 6 | FUNSD | Research | Open | Weak layout transfer |
| — | MIMIC-IV / full eICU / n2c2 | Credentialed DUA | Slow | **Rejected** for hackathon (ICU/PHI friction) |
| — | MedMCQA | MIT | Open | **Rejected** (exam diagnosis ≠ product) |

**Selected for Plan C execution:** in-repo synthetic IE fixtures + mixed-regime synthetic Hb series + existing 50 FAQ eval set. External gated downloads deferred (Eka/NidaanKosha) pending account terms.

---

## 2–3. Dataset ranking & selection

1. Synthetic IE fixtures (executed)  
2. Mixed-regime anomaly synth (executed)  
3. In-repo FAQ + KB (executed)  
4. Eka / NidaanKosha (queued — license/accept step)  
5. Credentialed clinical corpora (rejected)

---

## 4. Training pipeline

**Decision: no end-to-end model training promoted.**

| Candidate | Hypothesis | Gate | Outcome |
|-----------|------------|------|---------|
| IF / XGB / LSTM anomaly | Beat F1 0.87 | Data + explainability | **REJECT** |
| MiniLM fine-tune / reranker | Beat MRR | 50 FAQ too small; demo risk | **REJECT train**; zero-shot bake-off only |
| LayoutLM / NER IE | Beat regex F1 | No labeled India PDFs in lab | **REJECT train**; regex harden instead |
| Generative answer LLM | Fluency | Safety / no-diagnosis | **REJECT** |
| Safety classifier | Replace regex | Determinism | **REJECT** |

Pipeline that *did* run: **synthetic generate → measure → rule/template promote → Guardian veto**.

---

## 5–6. Model / method comparison & benchmarks

| Experiment | Metric | Plan B / baseline | Plan C result | Promote? |
|------------|--------|-------------------|---------------|----------|
| IE aliases + separators | Field F1 | (hard fixtures) | **0.9667** (R=1.0) | **YES → shipped** |
| Tone scrub | Violation rate | 0.72 | **0.00** | **YES → shipped** |
| Dense hybrid MiniLM | MRR / Hit@5 | 0.954 / 1.0 | **0.990 / 1.0** (ΔMRR=+0.036) | **Warm optional only** (demo default stays BM25) |
| Anomaly OR ref-range | F1 / FAR | 0.60 / 0.11 (mixed regimes) | F1↑ but FAR↑ | **NO** (FAR veto) |
| Anomaly AND ref-range | F1 / Recall | — | Recall stays 0.57 | **NO** |
| Trained DL models | — | — | Not trained | **NO** |

Spike-only Plan B numbers remain the pitch baseline (F1≈0.87). Mixed-regime eval shows gradual drift is harder — documented limitation, not a reason to ship FAR-worsening OR rules.

---

## 7. Hyperparameter summary

| Component | Values |
|-----------|--------|
| Statistical monitor | z≥2; CUSUM k=0.5σ, h=4σ; %Δ narrative @ 25% |
| BM25 | k1=1.5, b=0.75 + stopwords + intent boost ≤0.35 |
| Dense hybrid (optional) | 0.7 BM25 + 0.3 MiniLM cosine |
| IE | Expanded aliases; separators `[\s:|=\t.]+` |
| Tone | Regex rewrite of `you have` / `diagnosed with` in synthesizer |

---

## 8. Guardian monitoring report

- **No gradient training runs** → no exploding grads / catastrophic forgetting.  
- Dense bake-off incurred ~100s cold HF download → **demo-default veto** despite metric pass.  
- Anomaly OR-ref-range **metric-promoted then Guardian-vetoed** (FAR regression).  
- Rolling policy: FAR must not worsen; demo latency/reliability overrides pure F1/MRR.  
- Exploration stopped: no remaining local experiment clears *metric ∧ data ∧ demo-risk* simultaneously for a trained model.

---

## 9. Final promoted artifacts

| Artifact | Status |
|----------|--------|
| IE alias/separator hardening | **Integrated** (`patterns.py`) |
| Tone sanitizer + KB scrub | **Integrated** (`synthesizer.py`, KB txt) |
| Optional ref-range soft summary API | **Integrated** (does not flip `is_anomaly`) |
| Warm MiniLM hybrid | **Documented optional**; demo `FAST_KB=1` |
| Any newly trained weights | **None** |

---

## 10. Integration plan

Already applied in-repo. Day-of demo:

```text
MEDIVAULT_FAST_KB=1
MEDIVAULT_USE_DENSE=0
```

Optional post-demo science path: warm MiniLM once, then `FAST_KB=0 USE_DENSE=1`.

Next data acquisition (when accounts ready): Eka parse set → OCR CER / IE F1 on real India images; NidaanKosha → alias dictionary expansion.

---

## 11. Scientific justification

Plan B already saturates FAQ Hit@5 and beats IsolationForest on spike synth. Training without adequate labeled India lab PDFs or longitudinal outpatient series would overfit synthetic artifacts and inflate demo risk. Plan C therefore maximized **measurable gains under Guardian constraints**: IE recall on hard layouts, tone compliance, honest regime diagnostics, and a reproducible dense bake-off that **does not** override BM25 as the stage default.

---

## 12. Remaining limitations

1. IE F1 is on synthetic text, not scanned India PDFs.  
2. Mixed-regime anomaly recall (~0.57 overall) shows gradual drift remains hard.  
3. Dense MRR gain requires warm cache — not demo-safe cold.  
4. Eka/NidaanKosha not ingested this pass (gated/terms).  
5. No clinical validation; synthetic labels only.  
6. Tone heuristic is substring-based (now 0% on 50 FAQ after scrub).
