"""Unit tests for the `Document` domain entity."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.domain.ingestion.entities import Document, DocumentStatus


def _make_document(**overrides: object) -> Document:
    defaults: dict[str, object] = {
        "org_id": "org-1",
        "filename": "report.txt",
        "file_type": "text/plain",
        "storage_uri": "file:///tmp/report.txt",
        "uploaded_by": uuid4(),
    }
    defaults.update(overrides)
    return Document(**defaults)  # type: ignore[arg-type]


def test_document_generates_a_unique_id_by_default() -> None:
    first = _make_document()
    second = _make_document()

    assert isinstance(first.id, UUID)
    assert first.id != second.id


def test_document_defaults_status_to_uploaded_and_schema_json_to_none() -> None:
    document = _make_document()

    assert document.status == "uploaded"
    assert document.schema_json is None


def test_document_created_at_defaults_to_now() -> None:
    document = _make_document()

    assert document.created_at is not None


def test_document_accepts_explicit_status_and_schema_json() -> None:
    document = _make_document(status="processing", schema_json={"columns": ["a", "b"]})

    assert document.status == "processing"
    assert document.schema_json == {"columns": ["a", "b"]}


def test_document_default_status_is_the_documentstatus_uploaded_enum_member() -> None:
    document = _make_document()

    assert document.status is DocumentStatus.UPLOADED


def test_documentstatus_enum_has_the_four_required_values_and_matches_plain_strings() -> None:
    assert {s.value for s in DocumentStatus} == {"uploaded", "processing", "ready", "failed"}
    assert DocumentStatus.UPLOADED == "uploaded"
    assert DocumentStatus.PROCESSING == "processing"
    assert DocumentStatus.READY == "ready"
    assert DocumentStatus.FAILED == "failed"


def test_document_accepts_a_documentstatus_enum_member_explicitly() -> None:
    document = _make_document(status=DocumentStatus.READY)

    assert document.status == DocumentStatus.READY
    assert document.status == "ready"
