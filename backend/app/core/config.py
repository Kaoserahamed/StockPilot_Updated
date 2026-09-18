from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration.

    Values come from the process environment first, then from `.env` in the
    working directory. Unrelated shell variables are ignored so startup never
    fails because of an unrelated exported variable.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "StockPilot - Inventory & POS SaaS"
    # Database connection string - MUST be set via environment variable
    # Postgres ex: postgresql+psycopg2://user:password@localhost:5432/dbname
    database_url: str
    secret_key: str  # MUST be set via environment variable
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15  # Reduced from 60 for production security
    refresh_token_expire_days: int = 7
    upload_dir: str = "./uploads"

    # --- CORS ---
    cors_origins: str = "*"  # Comma-separated list; "*" for dev

    # --- Rate limiting ---
    redis_url: str | None = None  # If None, uses in-memory storage
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "5/minute"  # Stricter for login/register

    # --- Database pool ---
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800  # seconds

    # --- Logging ---
    log_level: str = "INFO"
    json_logs: bool = True

    # --- Environment ---
    environment: str = "development"  # development, staging, production
    release_version: str = "dev"  # stamped on logs and error reports

    # --- Observability / error tracking ---
    # When disabled, failures are still counted in-process but never emitted
    # to a sink (useful for noisy local runs).
    error_tracking_enabled: bool = True
    # Optional crash-reporter DSN (Sentry-compatible). Empty => log sink only.
    sentry_dsn: str | None = None

    # --- AI (Phase 5) ---
    # An empty key disables AI features: the endpoints then return the
    # deterministic analytics answer instead of calling out to Gemini.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    @field_validator("secret_key")
    @classmethod
    def _reject_weak_secret_in_production(cls, value: str) -> str:
        """Fail fast when production would run with a guessable JWT secret.

        Test/dev keeps the short ``test-secret-key-*`` / ``dev-secret-key-*``
        conveniences used by ``conftest.py`` and ``docker-compose.dev.yml``;
        anything else running as ``production``/``staging`` must provide a
        strong random secret (>= 32 chars, not a placeholder).
        """
        import os

        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in {"production", "staging"}:
            weak_markers = (
                "test-secret-key",
                "dev-secret-key",
                "changeme",
                "replace-with-",
                "secret",
                "password",
            )
            lowered = value.lower()
            if len(value) < 32 or any(m in lowered for m in weak_markers):
                raise ValueError(
                    "SECRET_KEY is too weak for production: "
                    "set a random value of at least 32 characters "
                    '(generate with `python -c "import secrets; '
                    'print(secrets.token_urlsafe(48))"`).'
                )
        return value

    @property
    def ai_enabled(self) -> bool:
        """True when a Gemini API key has been configured."""
        return bool(self.gemini_api_key.strip())


settings = Settings()  # type: ignore[call-arg]  # pydantic-settings injects from env
