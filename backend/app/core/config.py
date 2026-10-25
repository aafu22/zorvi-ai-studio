from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Zorvi AI Studio"
    app_version: str = "0.1.0"
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    storage_dir: str = "storage"
    max_upload_mb: int = Field(default=10, ge=1, le=50)
    file_ttl_hours: int = Field(default=24, ge=1)
    # AI Marketing Brain (Google Gemini). The key stays on the server and is never sent to the browser.
    gemini_api_key: str = ""
    # Configurable so you can switch models without touching code. See https://ai.google.dev/gemini-api/docs/models
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_timeout_seconds: int = Field(default=30, ge=5, le=120)
    # Folder holding the demo product photo. Empty = <repo>/sample_assets.
    sample_assets_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        return p if p.is_absolute() else BACKEND_ROOT / p

    @property
    def sample_assets_path(self) -> Path:
        if self.sample_assets_dir:
            p = Path(self.sample_assets_dir)
            return p if p.is_absolute() else BACKEND_ROOT / p
        return BACKEND_ROOT.parent / "sample_assets"

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
