"""
health-service/core/config.py
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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

    ai_service_url: str = "http://localhost:8003"

    # Shared by BFF, health and AI; required for protected service calls.
    internal_service_key: str = ""
    file_encryption_key: str = ""
    storage_account_quota_bytes: int = Field(default=1024*1024*1024,ge=1)
    storage_account_file_limit: int = Field(default=500,ge=1)
    storage_min_free_bytes: int = Field(default=1024*1024*1024,ge=0)

    @property
    def async_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
