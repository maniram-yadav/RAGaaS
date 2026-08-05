"""Unit tests for `DocxLoader` (STORY-013)."""

from __future__ import annotations

from pathlib import Path

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument
from app.domain.ingestion.loaders.docx_loader import DocxLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_docx_loader_is_a_baseloader() -> None:
    assert isinstance(DocxLoader(), BaseLoader)


def test_docx_loader_extracts_text_from_every_paragraph_in_order() -> None:
    loader = DocxLoader()
    fixture_path = FIXTURES_DIR / "sample.docx"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="sample.docx")

    assert isinstance(result, RawDocument)
    assert "First paragraph content." in result.content
    assert "Second paragraph content." in result.content
    assert "Third paragraph content." in result.content
    assert result.content.index("First paragraph content.") < result.content.index(
        "Second paragraph content."
    )
    assert result.content.index("Second paragraph content.") < result.content.index(
        "Third paragraph content."
    )


def test_docx_loader_returns_paragraph_count_metadata() -> None:
    loader = DocxLoader()
    fixture_path = FIXTURES_DIR / "sample.docx"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="sample.docx")

    # 4 paragraphs written to the fixture, including one blank paragraph.
    assert result.metadata["paragraph_count"] == 4


def test_docx_loader_returns_source_and_file_type_metadata() -> None:
    loader = DocxLoader()
    fixture_path = FIXTURES_DIR / "sample.docx"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="report.docx")

    assert result.metadata["source"] == "report.docx"
    assert result.metadata["file_type"] == ".docx"
    assert result.metadata["char_count"] == len(result.content)


def test_docx_loader_joins_paragraphs_with_newlines() -> None:
    loader = DocxLoader()
    fixture_path = FIXTURES_DIR / "sample.docx"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="sample.docx")

    assert "\n" in result.content
    paragraphs = result.content.split("\n")
    assert len(paragraphs) == 4
