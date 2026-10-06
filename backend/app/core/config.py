from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def default_storage_root() -> str:
    return "/tmp/house-renovation-assets" if os.getenv("VERCEL") == "1" else "./data/assets"


def default_max_upload_bytes() -> int:
    return 4_000_000 if os.getenv("VERCEL") == "1" else 10 * 1024 * 1024


class Settings(BaseSettings):
    app_name: str = "House Renovation System"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/house_renovation"
    storage_root: str = Field(default_factory=default_storage_root)
    openai_api_key: str | None = None
    openai_image_model: str = "gpt-image-1"
    yoloe_model_path: str | None = None
    max_upload_bytes: int = Field(default_factory=default_max_upload_bytes, gt=0)
    min_image_width: int = Field(default=256, gt=0)
    min_image_height: int = Field(default=256, gt=0)
    max_image_width: int = Field(default=12000, gt=0)
    max_image_height: int = Field(default=12000, gt=0)
    max_image_aspect_ratio: float = Field(default=8.0, gt=1)
    blur_variance_threshold: float = Field(default=30.0, ge=0)
    exposure_low_threshold: float = Field(default=12.0, ge=0, le=255)
    exposure_high_threshold: float = Field(default=245.0, ge=0, le=255)
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.startswith("postgres://"):
            normalized = "postgresql+psycopg://" + normalized.removeprefix("postgres://")
        elif normalized.startswith("postgresql://"):
            normalized = "postgresql+psycopg://" + normalized.removeprefix("postgresql://")
        try:
            parsed = make_url(normalized)
        except ArgumentError as exc:
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL such as "
                "postgresql+psycopg://user:password@localhost:5432/database"
            ) from exc
        if parsed.drivername != "postgresql+psycopg" or not parsed.host or not parsed.database:
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL such as "
                "postgresql+psycopg://user:password@localhost:5432/database"
            )
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
