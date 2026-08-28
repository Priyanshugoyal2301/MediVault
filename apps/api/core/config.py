"""API Gateway configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_secret_key: str
    auth_algorithm: str = "HS256"

    auth_service_url: str = "http://localhost:8001"
    health_service_url: str = "http://localhost:8002"

    # Comma-separated browser origins allowed to call the BFF
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
