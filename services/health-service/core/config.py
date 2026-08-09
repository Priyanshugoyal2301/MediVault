"""
health-service/core/config.py
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "medivault"
    postgres_user: str = "medivault_user"
    postgres_password: str

    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "./data/uploads"
    storage_s3_bucket: str = ""
    storage_s3_endpoint: str = ""
    storage_s3_access_key: str = ""
    storage_s3_secret_key: str = ""

    ai_service_url: str = "http://ai-service:8003"

    @property
    def async_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
