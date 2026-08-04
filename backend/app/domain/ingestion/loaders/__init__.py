"""Document loaders (Strategy) + `LoaderFactory` (STORY-011, plan §4.1).

`BaseLoader`/`RawDocument` (`base.py`) define the shared contract; each
concrete file-type loader — `TextLoader` here, `PdfLoader`/`DocxLoader`
(STORY-012/013), `ExcelLoader`/`CsvLoader` (STORY-026) later — is a
`BaseLoader` subclass registered in `LoaderFactory`'s extension map
(`factory.py`).
"""

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument
from app.domain.ingestion.loaders.factory import LoaderFactory
from app.domain.ingestion.loaders.text_loader import TextLoader

__all__ = [
    "BaseLoader",
    "LoaderFactory",
    "RawDocument",
    "TextLoader",
]
