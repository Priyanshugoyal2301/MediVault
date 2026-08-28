# Reproducibility Checklist

## Per model (8/8 packages audited)

- [x] `README.md`  
- [x] `train.py`  
- [x] `evaluate.py`  
- [x] `infer.py`  
- [x] `config.yaml`  
- [x] `model_card.md`  
- [x] `requirements.txt`  
- [x] Config loader / env overrides (paths, backend, seed where applicable)  
- [x] Checkpoint / artifact format documented (pickle/meta JSON or HTTP-only OCR)

## Platform

- [x] `python models/platform/audit.py`  
- [x] Random seeds in phase configs (risk/forecast/health/anomaly/quality)  
- [x] Dataset `LICENSING.md` / synthetic generators  
- [x] Docs model cards under `docs/model-cards/`  
- [ ] Bit-exact cross-machine hardware (not required; document CPU/GPU variance)

## Commands to re-verify

```bash
python models/platform/audit.py
python models/platform/benchmark_suite.py
python models/platform/e2e_validate.py
```

Latest machine audit: `datasets/evaluation/platform_reproducibility_audit.json`
