"""
auth-service/core/config.py

Loads configuration from environment variables.
All env vars must be set — the service refuses to start if required vars are absent.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "medivault"
    postgres_user: str = "medivault_user"
    postgres_password: str

    # JWT
    auth_secret_key: str
    auth_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 60

    @property
    def async_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
