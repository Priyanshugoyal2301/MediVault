"""API Gateway configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        extra="ignore",
    )

    auth_secret_key: str
    auth_algorithm: str = "HS256"

    auth_service_url: str = "http://localhost:8001"
    health_service_url: str = "http://localhost:8002"
    internal_service_key: str = ""
    cookie_secure: bool = True
    trust_cf_connecting_ip: bool = False

    # Comma-separated browser origins allowed to call the BFF
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def auth_service_base_url(self) -> str:
        return self._http_url(self.auth_service_url)

    @property
    def health_service_base_url(self) -> str:
        return self._http_url(self.health_service_url)

    @staticmethod
    def _http_url(value: str) -> str:
        value = value.strip().rstrip("/")
        return value if "://" in value else f"http://{value}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
