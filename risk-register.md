# Risk Register — MediVault ML

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R-01 | User confuses risk/score with diagnosis | Med | High | Disclaimers; flags off by default; product copy review |
| R-02 | PHI sent to public OCR endpoint | Low/Med | Critical | Private endpoint only; default OCR legacy |
| R-03 | High FAR anomaly alerts | Med | Med | Statistical default; tune thresholds offline |
| R-04 | Quality model blocks valid scans | Med | Med | Flag off default; passthrough / soft fail |
| R-05 | Synthetic metrics published as clinical | Med | High | Validation docs + research-readiness wording |
| R-06 | Dependency bloat (torch) on deploy image | Med | Med | Optional deps; feature-head quality train |
| R-07 | Stale registry after env change | High | Low | Document restart requirement |
| R-08 | Experiment tracking uploads secrets | Low | High | Tracking disabled by default |
| R-09 | Multi-flag ON latency / OOM | Med | Med | Cutover one flag at a time |
| R-10 | License violation shipping corpora | Low | Critical | Datasets not redistributed; env paths only |

Owner: platform ML + product safety. Review each cutover.
