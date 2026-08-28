"""
Feature flags for gradual ML cutover.

All flags default to False / rule-based paths so existing demos and tests remain stable.
Enable per environment (.env) or process env:

  USE_UNLIMITED_OCR=0
  USE_ML_NORMALIZER=0
  USE_RISK_MODEL=0
  USE_FORECAST_MODEL=0
  USE_EMBEDDING_SEARCH=0
  USE_HEALTH_SCORE_MODEL=0
  USE_ANOMALY_MODEL=0
  USE_OUTLIER_MODEL=0
  USE_IMAGE_QUALITY_MODEL=0

Backward compatibility:
  MEDIVAULT_USE_DENSE=1 is treated as USE_EMBEDDING_SEARCH=1 when the new flag
  would otherwise be off.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class FeatureFlags(BaseSettings):
    """ML migration switches — all default off (current production path)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        # Field use_unlimited_ocr ← env USE_UNLIMITED_OCR
        case_sensitive=False,
    )

    use_unlimited_ocr: bool = False
    use_ml_normalizer: bool = False
    use_risk_model: bool = False
    use_forecast_model: bool = False
    use_embedding_search: bool = False
    use_health_score_model: bool = False
    use_anomaly_model: bool = False
    use_outlier_model: bool = False  # Phase 0 name; alias of USE_ANOMALY_MODEL
    use_image_quality_model: bool = False


@lru_cache
def get_feature_flags() -> FeatureFlags:
    flags = FeatureFlags()
    updates: dict = {}
    # Honor legacy dense-KB env if embedding search still false
    if not flags.use_embedding_search and _env_truthy("MEDIVAULT_USE_DENSE"):
        updates["use_embedding_search"] = True
    # Phase 4 alias
    if not flags.use_risk_model and _env_truthy("USE_DISEASE_RISK_MODEL"):
        updates["use_risk_model"] = True
    # Phase 7: either USE_ANOMALY_MODEL or USE_OUTLIER_MODEL enables ML anomaly
    anomaly_on = flags.use_anomaly_model or flags.use_outlier_model
    if not anomaly_on and (
        _env_truthy("USE_ANOMALY_MODEL") or _env_truthy("USE_OUTLIER_MODEL")
    ):
        anomaly_on = True
    if anomaly_on:
        updates["use_anomaly_model"] = True
        updates["use_outlier_model"] = True
    if updates:
        return flags.model_copy(update=updates)
    return flags


def reset_feature_flags_cache() -> None:
    """Test helper — clear LRU cache after monkeypatching env."""
    get_feature_flags.cache_clear()


def flags_as_dict() -> dict[str, bool]:
    f = get_feature_flags()
    anomaly = f.use_anomaly_model or f.use_outlier_model
    return {
        "USE_UNLIMITED_OCR": f.use_unlimited_ocr,
        "USE_ML_NORMALIZER": f.use_ml_normalizer,
        "USE_RISK_MODEL": f.use_risk_model,
        "USE_DISEASE_RISK_MODEL": f.use_risk_model,  # Phase 4 alias
        "USE_FORECAST_MODEL": f.use_forecast_model,
        "USE_EMBEDDING_SEARCH": f.use_embedding_search,
        "USE_HEALTH_SCORE_MODEL": f.use_health_score_model,
        "USE_ANOMALY_MODEL": anomaly,
        "USE_OUTLIER_MODEL": anomaly,  # Phase 0 alias
        "USE_IMAGE_QUALITY_MODEL": f.use_image_quality_model,
    }
