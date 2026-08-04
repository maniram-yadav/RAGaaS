"""Unit tests for `TextLoader` (STORY-011)."""

from __future__ import annotations

import io
from pathlib import Path

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument
from app.domain.ingestion.loaders.text_loader import TextLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_text_loader_is_a_baseloader() -> None:
    assert isinstance(TextLoader(), BaseLoader)


def test_text_loader_loads_a_fixture_file_verbatim() -> None:
    loader = TextLoader()
    fixture_path = FIXTURES_DIR / "sample.txt"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="sample.txt")

    assert isinstance(result, RawDocument)
    assert result.content == fixture_path.read_text(encoding="utf-8")


def test_text_loader_returns_correct_metadata() -> None:
    loader = TextLoader()
    content = b"hello world"

    result = loader.load(io.BytesIO(content), filename="notes.txt")

    assert result.metadata == {
        "source": "notes.txt",
        "file_type": ".txt",
        "char_count": len("hello world"),
    }


def test_text_loader_decodes_utf8_bytes() -> None:
    loader = TextLoader()
    content = "café — résumé".encode()

    result = loader.load(io.BytesIO(content), filename="unicode.txt")

    assert result.content == "café — résumé"


def test_text_loader_replaces_undecodable_bytes_instead_of_raising() -> None:
    loader = TextLoader()
    content = b"valid text \xff\xfe more text"

    result = loader.load(io.BytesIO(content), filename="bad-encoding.txt")

    assert "valid text" in result.content
    assert "more text" in result.content


def test_text_loader_handles_empty_file() -> None:
    loader = TextLoader()

    result = loader.load(io.BytesIO(b""), filename="empty.txt")

    assert result.content == ""
    assert result.metadata["char_count"] == 0
