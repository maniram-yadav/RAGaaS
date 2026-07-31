"""Unit tests for `app.core.settings.Settings` (config precedence layers 2/3).

`Settings` must prefer an explicitly-set environment variable over its field
default, and never touch a real `.env` file (tests pass `_env_file=None` so a
developer's local `.env`, if any, can never leak into test expectations).
"""

from app.core.settings import Settings, get_settings


def test_field_default_used_when_no_env_var_set() -> None:
    """With no override, a field resolves to its declared default (layer 3)."""
    settings = Settings(_env_file=None)

    assert settings.app_env == "local"
    assert settings.db_active == "postgres"
    assert settings.config_cache_ttl_seconds == 30


def test_env_var_overrides_field_default(monkeypatch) -> None:
    """An environment variable takes precedence over the field default."""
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DB_ACTIVE", "mongo")
    monkeypatch.setenv("CONFIG_CACHE_TTL_SECONDS", "90")

    settings = Settings(_env_file=None)

    assert settings.app_env == "staging"
    assert settings.db_active == "mongo"
    assert settings.config_cache_ttl_seconds == 90


def test_explicit_kwarg_overrides_env_var(monkeypatch) -> None:
    """Constructor kwargs (used by tests to pin values) beat env vars too."""
    monkeypatch.setenv("DB_ACTIVE", "mongo")

    settings = Settings(_env_file=None, db_active="postgres")

    assert settings.db_active == "postgres"


def test_get_settings_is_cached_singleton() -> None:
    """`get_settings()` returns the same instance across calls (Singleton-via-DI)."""
    assert get_settings() is get_settings()
