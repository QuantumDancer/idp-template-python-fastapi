from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Silently ignore extra env vars
        extra="ignore",
    )

    app_name: str = "${{ values.slug }}"
    app_version: str = "0.1.0"

    # Controls log format (JSON when non-dev) and Swagger UI visibility (hidden in prod)
    environment: str = "development"  # development | staging | production

    log_level: str = "INFO"

    # JSON list of allowed CORS origins; ["*"] permits all origins (fine for internal APIs)
    cors_origins: list[str] = ["*"]

    # OTLP/HTTP trace exporter endpoint. Tracing is disabled when unset.
    otel_exporter_otlp_endpoint: str | None = None

    @property
    def log_as_json(self) -> bool:
        """Emit structured JSON logs in every environment except development."""
        return self.environment != "development"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Wrapped in lru_cache so config is read once at startup. Override in tests with
    ``app.dependency_overrides[get_settings] = lambda: my_test_settings``.
    """
    return Settings()
