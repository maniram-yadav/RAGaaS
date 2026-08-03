"""Unit tests for ingestion domain errors."""

from __future__ import annotations

from uuid import uuid4

from app.domain.ingestion.errors import DocumentNotFoundError


def test_document_not_found_error_carries_the_document_id_and_a_message() -> None:
    document_id = uuid4()

    error = DocumentNotFoundError(document_id)

    assert error.document_id == document_id
    assert str(document_id) in str(error)
