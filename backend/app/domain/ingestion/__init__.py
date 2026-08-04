"""Ingestion domain: `Document` model/repo, document loaders, LoaderFactory."""

from app.domain.ingestion.entities import Document, DocumentStatus
from app.domain.ingestion.errors import DocumentNotFoundError, UnsupportedFileTypeError
from app.domain.ingestion.loaders import BaseLoader, LoaderFactory, RawDocument, TextLoader
from app.domain.ingestion.repository import IDocumentRepository

__all__ = [
    "BaseLoader",
    "Document",
    "DocumentNotFoundError",
    "DocumentStatus",
    "IDocumentRepository",
    "LoaderFactory",
    "RawDocument",
    "TextLoader",
    "UnsupportedFileTypeError",
]
