"""Unit tests for `PdfLoader` (STORY-012)."""

from __future__ import annotations

from pathlib import Path

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument
from app.domain.ingestion.loaders.pdf_loader import PdfLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_pdf_loader_is_a_baseloader() -> None:
    assert isinstance(PdfLoader(), BaseLoader)


def test_pdf_loader_extracts_text_from_every_page_in_order() -> None:
    loader = PdfLoader()
    fixture_path = FIXTURES_DIR / "sample.pdf"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="sample.pdf")

    assert isinstance(result, RawDocument)
    assert "Page one content." in result.content
    assert "Page two content." in result.content
    assert result.content.index("Page one content.") < result.content.index(
        "Page two content."
    )


def test_pdf_loader_returns_correct_page_number_metadata() -> None:
    loader = PdfLoader()
    fixture_path = FIXTURES_DIR / "sample.pdf"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="sample.pdf")

    assert result.metadata["page_count"] == 2
    assert result.metadata["pages"] == [
        {"page": 1, "char_count": len("Page one content.")},
        {"page": 2, "char_count": len("Page two content.")},
    ]


def test_pdf_loader_returns_source_and_file_type_metadata() -> None:
    loader = PdfLoader()
    fixture_path = FIXTURES_DIR / "sample.pdf"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="report.pdf")

    assert result.metadata["source"] == "report.pdf"
    assert result.metadata["file_type"] == ".pdf"
    assert result.metadata["char_count"] == len(result.content)


def test_pdf_loader_joins_pages_with_a_form_feed() -> None:
    loader = PdfLoader()
    fixture_path = FIXTURES_DIR / "sample.pdf"

    with fixture_path.open("rb") as file:
        result = loader.load(file, filename="sample.pdf")

    assert "\f" in result.content
    pages = result.content.split("\f")
    assert len(pages) == 2
