"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "ARGent"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://argent:argent@localhost:5432/argent"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Google Cloud / Gemini (for agent work)
    gemini_api_key: str = ""
    gcp_project: str = ""
    gcp_location: str = "us-central1"

    # Email (Mailgun/Resend)
    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    email_from: str = "noreply@argent.game"

    # Telegram
    telegram_bot_token_ember: str = ""
    telegram_bot_token_miro: str = ""

    # Security
    secret_key: str = "change-me-in-production"

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic migrations)."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
