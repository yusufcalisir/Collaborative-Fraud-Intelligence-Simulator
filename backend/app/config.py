"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check all configuration at startup.
Fails fast if required variables are missing.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────
    app_env: str = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"

    # ── FastAPI ───────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # ── PostgreSQL ────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fraud_intelligence"
    postgres_user: str = "fraud_user"
    postgres_password: str = "change_me_in_production"

    # ── Redis ─────────────────────────────────
    # Leave redis_host empty to disable Redis and use in-memory storage silently.
    # Set REDIS_HOST env var to enable Redis.
    redis_host: str = ""
    redis_port: int = 6379
    redis_db: int = 0

    # ── Celery ────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── FL Simulation Defaults ────────────────
    fl_default_rounds: int = 10
    fl_default_local_epochs: int = 3
    fl_default_learning_rate: float = 0.001
    fl_default_batch_size: int = 64
    fl_min_clients_per_round: int = 2

    # ── API Gateway Security ──────────────────
    gateway_require_auth: bool = False
    gateway_rate_limit: int = 120  # requests per minute
    gateway_api_keys: str = "key_bank_a:bank_a:bank,key_bank_b:bank_b:bank,key_bank_c:bank_c:bank,key_analyst:analyst:analyst"

    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync PostgreSQL connection URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str | None:
        """Redis connection URL, or None if Redis is not configured."""
        if not self.redis_host:
            return None
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance. Parsed once at startup."""
    return Settings()
