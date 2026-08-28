"""ai-service configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Shared with health-service — /parse may only read under this root
    storage_local_path: str = "./data/uploads"

    # Shared secret for service-to-service calls (health → AI).
    # If empty, internal auth is disabled (unit tests / local without .env).
    # Hackathon/demo: set INTERNAL_SERVICE_KEY in .env and never publish AI ports.
    internal_service_key: str = ""

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    tesseract_cmd: str = "tesseract"

    # --- ML feature flags (defaults OFF = current rule-based path) ---
    # Also available via core.feature_flags.FeatureFlags for registry selection.
    use_unlimited_ocr: bool = False
    use_ml_normalizer: bool = False
    use_risk_model: bool = False
    use_embedding_search: bool = False
    use_health_score_model: bool = False
    use_outlier_model: bool = False
    use_image_quality_model: bool = False

    # Unlimited-OCR operator config (optional; only used when USE_UNLIMITED_OCR=1)
    unlimited_ocr_backend: str = "auto"  # auto | http | local | stub
    unlimited_ocr_endpoint: str = ""
    unlimited_ocr_hf_model: str = "baidu/Unlimited-OCR"
    unlimited_ocr_timeout_s: float = 120.0

    @property
    def storage_root(self) -> Path:
        return Path(self.storage_local_path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
