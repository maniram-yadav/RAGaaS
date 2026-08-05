"""Ingestion domain: `Document` model/repo, document loaders, LoaderFactory."""

from app.domain.ingestion.entities import Document, DocumentStatus
from app.domain.ingestion.errors import DocumentNotFoundError, UnsupportedFileTypeError
from app.domain.ingestion.loaders import (
    BaseLoader,
    DocxLoader,
    LoaderFactory,
    PdfLoader,
    RawDocument,
    TextLoader,
)
from app.domain.ingestion.repository import IDocumentRepository

__all__ = [
    "BaseLoader",
    "Document",
    "DocumentNotFoundError",
    "DocumentStatus",
    "DocxLoader",
    "IDocumentRepository",
    "LoaderFactory",
    "PdfLoader",
    "RawDocument",
    "TextLoader",
    "UnsupportedFileTypeError",
]
