"""Ingestion domain: `Document` model/repo, document loaders, LoaderFactory."""

from app.domain.ingestion.entities import Document, DocumentStatus
from app.domain.ingestion.errors import DocumentNotFoundError
from app.domain.ingestion.repository import IDocumentRepository

__all__ = [
    "Document",
    "DocumentNotFoundError",
    "DocumentStatus",
    "IDocumentRepository",
]
