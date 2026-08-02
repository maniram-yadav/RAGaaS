"""Unit tests for `IStorageService`'s contract shape."""

from __future__ import annotations

import pytest

from app.domain.storage.service import IStorageService


def test_is_storage_service_is_abstract() -> None:
    with pytest.raises(TypeError):
        IStorageService()  # type: ignore[abstract]


def test_is_storage_service_declares_expected_methods() -> None:
    for method in ("save", "read", "delete", "get_presigned_url"):
        assert method in IStorageService.__abstractmethods__
