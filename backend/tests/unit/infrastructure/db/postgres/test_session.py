"""Unit test for `build_postgres_url` — pure string building, no live DB."""

from __future__ import annotations

from app.core.settings import Settings
from app.infrastructure.db.postgres.session import build_postgres_url


def test_build_postgres_url_uses_asyncpg_driver() -> None:
    settings = Settings(
        _env_file=None,
        postgres_user="raas",
        postgres_password="secret",
        postgres_host="db.internal",
        postgres_port=5433,
        postgres_db="raas_test",
    )

    url = build_postgres_url(settings)

    assert url == "postgresql+asyncpg://raas:secret@db.internal:5433/raas_test"
