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
    gemini_model: str = "gemini-2.5-flash"
    gcp_project: str = ""
    gcp_location: str = "us-central1"

    # Agent settings
    agent_response_enabled: bool = True  # Toggle agent responses (disable for testing)

    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = (
        "onboarding@resend.dev"  # Use verified domain in prod: noreply@argent.neverdecel.com
    )
    email_enabled: bool = True

    # SMS (Twilio)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""  # Miro's phone number (E.164 format: +1234567890)
    sms_enabled: bool = True

    # Security
    secret_key: str = "change-me-in-production"

    # Base URL (for verification links in emails)
    base_url: str = "http://localhost:8000"

    # Verification settings
    email_verification_expiry_hours: int = 24
    phone_code_expiry_minutes: int = 10
    phone_resend_cooldown_seconds: int = 60

    # Web inbox (non-immersive mode)
    web_inbox_enabled: bool = True  # Enable web inbox feature
    allow_web_only_registration: bool = True  # Allow players to register in web-only mode
    web_only_verification_code: str = "123456"  # Fixed code for simulated phone verification

    # Scheduler settings
    scheduler_force_immediate: bool = False  # Force immediate execution (skip delays for testing)

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic migrations)."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
