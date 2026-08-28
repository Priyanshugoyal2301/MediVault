# Deployment Checklist — MediVault ML Platform

## Pre-deploy

- [ ] All `USE_*` ML flags **off** in production `.env` unless staged cutover approved  
- [ ] `.env` does not ship secrets; compare `.env.example`  
- [ ] No PHI datasets committed  
- [ ] `python models/platform/audit.py` → `all_pass: true`  
- [ ] `python models/platform/e2e_validate.py` → `PASS`  
- [ ] Unit/phase tests green for changed packages  
- [ ] Artifacts under `models/*/artifacts` intentional (or regenerated in CI offline)

## Service rollout

- [ ] Deploy **ai-service** with flag-off config  
- [ ] Verify `GET /health` includes `ml_feature_flags` all false  
- [ ] Smoke: parse / qa / anomaly endpoints match pre-upgrade schemas  
- [ ] Shadow mode (optional): enable one flag on staging; compare disagreements  

## Cutover (optional)

- [ ] One flag at a time  
- [ ] Monitor latency + error rates  
- [ ] Rollback plan: set flag `0` + restart (no code change)

## Experiment tracking

- [ ] `ML_EXPERIMENT_TRACKING=0` in production  
- [ ] If enabled, use private MLflow URI / offline W&B only

## Post-deploy

- [ ] No unexpected empty `/parse` responses (quality flag)  
- [ ] Log review for ML adapter init failures  
- [ ] Document active flags in ops runbook
