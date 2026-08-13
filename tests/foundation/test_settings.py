import pytest
from pydantic import ValidationError

from packages.foundation.settings import Settings


def test_public_summary_never_contains_secret() -> None:
    value = "should-never-be-serialized"
    settings = Settings(secret_api_key=value)
    assert value not in repr(settings.public_summary())
    assert settings.public_summary()["secret_api_key_configured"] is True


def test_rejects_non_postgres_database() -> None:
    with pytest.raises(ValidationError, match="must use PostgreSQL"):
        Settings(database_url="sqlite:///local.db")


def test_production_rejects_bootstrap_credentials() -> None:
    with pytest.raises(ValidationError, match="must be supplied externally"):
        Settings(
            environment="production",
            # Explicit bootstrap URL keeps the assertion deterministic even when
            # a local .env provides a different NARRATOPRO_DATABASE_URL.
            database_url="postgresql+psycopg://narratopro:narratopro@127.0.0.1:5432/narratopro",
        )
