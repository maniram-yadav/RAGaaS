"""Bootstrap-level application settings (config precedence layers 2 & 3).

`Settings` is a `pydantic-settings` model that reads environment variables, falling
back to a `.env` file (via `python-dotenv`, if one exists on disk) and finally to
the field defaults declared below. That collapses the plan's "environment
variables -> `.env` defaults" precedence layers into a single object, since
`pydantic-settings` already applies env-var-overrides-dotenv-overrides-default
resolution internally.

This module never reads or writes a *real* `.env` file itself — it only declares
*how* one would be read if present, matching the shape documented in
`.env.example`. See `.claude/rules/config-management.md`.

`ConfigService` (`app/core/config.py`) is the only thing that combines this
bootstrap layer with layer 1 (the MongoDB `system_config` document). Feature code
should not import `Settings` to read a *runtime-tunable* value (active provider,
model name, limits) — it should go through `ConfigService.get(section)` instead.
`Settings` is appropriate for genuinely bootstrap-only concerns (DB connection
strings, the JWT signing key, ...).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bootstrap settings sourced from environment variables / `.env`.

    Field names map to env vars of the same name (case-insensitive), matching
    `.env.example`. Every field here documents its purpose and default in
    `docs/reference/configuration.md`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_env: str = "local"
    app_secret_key: str = ""
    app_log_level: str = "INFO"

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "raas"
    postgres_user: str = "raas"
    postgres_password: str = ""

    # --- MongoDB (also hosts the system_config collection) ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "raas"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # --- Auth ---
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # --- ConfigService fallback defaults for system_config sections ---
    # (layers 2/3 of the precedence chain; see docs/reference/configuration.md)
    db_active: str = "postgres"

    storage_active: str = "local"
    local_storage_base_path: str = "./var/storage"
    aws_s3_bucket: str = ""
    aws_region: str = ""
    gcs_bucket: str = ""
    azure_storage_container: str = ""

    llm_active: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_embedding_model: str = "text-embedding-3-small"

    payment_active: str = "stripe"

    vectorstore_active: str = "qdrant"

    safety_rate_limit_rpm: int = 60
    safety_moderation_active: str = "openai"

    config_cache_ttl_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached `Settings` instance (Singleton-via-DI)."""
    return Settings()
