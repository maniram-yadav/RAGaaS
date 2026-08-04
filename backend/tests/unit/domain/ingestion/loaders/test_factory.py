"""Unit tests for `LoaderFactory` (STORY-011)."""

from __future__ import annotations

import pytest

from app.domain.ingestion.errors import UnsupportedFileTypeError
from app.domain.ingestion.loaders.factory import LoaderFactory
from app.domain.ingestion.loaders.text_loader import TextLoader


def test_get_loader_returns_a_text_loader_for_dot_txt() -> None:
    loader = LoaderFactory.get_loader(".txt")

    assert isinstance(loader, TextLoader)


def test_get_loader_is_case_insensitive() -> None:
    loader = LoaderFactory.get_loader(".TXT")

    assert isinstance(loader, TextLoader)


def test_get_loader_returns_a_fresh_instance_each_call() -> None:
    first = LoaderFactory.get_loader(".txt")
    second = LoaderFactory.get_loader(".txt")

    assert first is not second


def test_get_loader_raises_for_an_unregistered_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        LoaderFactory.get_loader(".pdf")

    assert exc_info.value.extension == ".pdf"


def test_get_loader_raises_for_a_completely_unknown_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        LoaderFactory.get_loader(".exe")
