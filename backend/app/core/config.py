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

    # ---- Database
    # Empty = a SQLite file in the storage folder (fine on your own computer).
    # A postgresql://... address = PostgreSQL, e.g. a free Neon database. Needed on hosts whose disk is wiped
    # on restart (Render's free plan), otherwise accounts and saved data disappear.
    database_url: str = ""

    # ---- Accounts: email verification and password reset
    # Public address of the website. Used to build the links inside emails.
    frontend_url: str = "http://localhost:3000"
    # When true, a new account must click the emailed link before it can sign in.
    require_email_verification: bool = True
    verification_token_hours: int = Field(default=24, ge=1)
    reset_token_minutes: int = Field(default=60, ge=5)
    # Outgoing email (SMTP). Leave smtp_host empty in development: emails are then printed
    # in the backend terminal instead of being sent.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""  # e.g. "Zorvi AI Studio <you@example.com>"; empty = smtp_username
    smtp_use_ssl: bool = False  # true = implicit TLS (port 465); false = STARTTLS (port 587)
    # Brevo (https://www.brevo.com) sends email through a web API instead of SMTP. Use it on hosts that
    # block SMTP ports (for example Render's free plan). If brevo_api_key is set it is used instead of SMTP.
    brevo_api_key: str = ""
    brevo_sender_email: str = ""  # must be a sender you verified in Brevo
    brevo_sender_name: str = "Zorvi AI Studio"

    # ---- HTTPS
    # Redirect plain-HTTP requests to HTTPS. Turn on when the site is served over HTTPS
    # (normally behind a reverse proxy such as Caddy or nginx; see deploy/Caddyfile).
    force_https: bool = False

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
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host.strip())

    @property
    def brevo_configured(self) -> bool:
        return bool(self.brevo_api_key.strip())

    @property
    def email_configured(self) -> bool:
        return self.brevo_configured or self.smtp_configured

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
