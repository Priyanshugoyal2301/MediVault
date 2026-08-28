# models/explainability

Reusable attribution helpers for MediVault ML models (Phase 6+).

- **SHAP TreeExplainer** when `shap` is installed  
- **Fallback** gain/centered local contributions when not  
- **Linear coef** attributions for ridge/linear models  

Do not hard-fail if SHAP is missing — explainability degrades gracefully.
