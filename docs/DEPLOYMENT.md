# Deployment — MediVault (ML-aware)

Full ops checklist: [`deployment-checklist.md`](../deployment-checklist.md).

## Production defaults

1. Copy `.env.example` → `.env`; keep **all** `USE_*` ML flags at **0**.  
2. `ML_EXPERIMENT_TRACKING=0`.  
3. Deploy services (auth / health / AI / BFF / web) as before.  
4. Verify `GET ai-service/health` → `ml_feature_flags` all false.  
5. Smoke parse + anomaly against pre-upgrade schemas.

## Document OCR (optional experimental)

1. Default: `USE_UNLIMITED_OCR=0` (legacy).  
2. Staging Unlimited: `USE_UNLIMITED_OCR=1` + private `UNLIMITED_OCR_ENDPOINT` only.  
3. Do **not** set `UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS=1` on small boxes unless intentional.  
4. PHI: self-host only.

## Cutover policy

Enable **one** flag at a time on staging; measure latency/errors; rollback = set flag `0` + restart.

Container images stay lean without forced torch when flags stay off.
