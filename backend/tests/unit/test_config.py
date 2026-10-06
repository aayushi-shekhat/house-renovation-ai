import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_normalizes_supported_postgres_schemes() -> None:
    assert Settings(database_url="postgres://postgres:secret@localhost:5432/house_renovation").database_url == (
        "postgresql+psycopg://postgres:secret@localhost:5432/house_renovation"
    )
    assert Settings(database_url="postgresql://postgres:secret@localhost:5432/house_renovation").database_url == (
        "postgresql+psycopg://postgres:secret@localhost:5432/house_renovation"
    )


def test_project_root_env_file_loads_valid_database_url() -> None:
    settings = Settings()

    assert settings.database_url.startswith("postgresql+psycopg://postgres:")
    assert settings.database_url.endswith("@localhost:5432/house_renovation")


def test_vercel_uses_writable_ephemeral_storage(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://postgres:secret@localhost:5432/house_renovation",
    )

    assert settings.storage_root == "/tmp/house-renovation-assets"
    assert settings.max_upload_bytes == 4_000_000


def test_database_url_rejects_non_postgres_or_missing_host() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL must be a PostgreSQL URL"):
        Settings(database_url="sqlite:///./local.db")
    with pytest.raises(ValidationError, match="DATABASE_URL must be a PostgreSQL URL"):
        Settings(database_url="postgresql+psycopg:///house_renovation")