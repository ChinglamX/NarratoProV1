"""Typed application settings with secret-safe serialization."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NARRATOPRO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    environment: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("environment", "NARRATOPRO_ENV"),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str = "postgresql+psycopg://narratopro:narratopro@127.0.0.1:5432/narratopro"
    temporal_target: str = "127.0.0.1:7233"
    temporal_namespace: str = "default"
    object_store_root: Path = Path("data/local/object_store")
    artifact_root: Path = Path("artifacts")
    temp_root: Path = Path("tmp")
    max_local_cost_cents: int = Field(default=0, ge=0)
    secret_api_key: SecretStr | None = None

    # Volcengine Ark (E06 VLM provider; open-source model backend via API).
    volcengine_ark_api_key: SecretStr | None = None
    volcengine_ark_endpoint: str = (
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    )
    volcengine_ark_model: str | None = None

    @field_validator("secret_api_key", "volcengine_ark_api_key", mode="before")
    @classmethod
    def empty_secret_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("database_url")
    @classmethod
    def require_database_scheme(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("database_url must use PostgreSQL")
        return value

    @model_validator(mode="after")
    def production_cannot_use_bootstrap_credentials(self) -> Settings:
        if self.environment == "production" and "narratopro:narratopro@" in self.database_url:
            raise ValueError("production database credentials must be supplied externally")
        return self

    def public_summary(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "log_level": self.log_level,
            "database_scheme": self.database_url.split(":", maxsplit=1)[0],
            "temporal_target": self.temporal_target,
            "temporal_namespace": self.temporal_namespace,
            "object_store_root": str(self.object_store_root),
            "artifact_root": str(self.artifact_root),
            "temp_root": str(self.temp_root),
            "max_local_cost_cents": self.max_local_cost_cents,
            "secret_api_key_configured": self.secret_api_key is not None,
            "volcengine_ark_configured": self.volcengine_ark_api_key is not None,
            "volcengine_ark_endpoint": self.volcengine_ark_endpoint,
            "volcengine_ark_model": self.volcengine_ark_model,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
