"""`LocalFsStorage` — the first concrete `IStorageService` (local disk).

Registers itself under the `"local"` key in `app.core.storage_factory`'s
registry on import (Open/Closed: `StorageFactory` never needs an `if/elif`
branch added for this backend — it just imports this module once, listed in
`_STORAGE_SERVICE_MODULES`).
"""

from __future__ import annotations

import asyncio
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname
from uuid import uuid4

from app.core.settings import get_settings
from app.core.storage_factory import register_storage_service
from app.domain.storage.errors import StorageObjectNotFoundError
from app.domain.storage.service import IStorageService


def _sanitize_filename(filename: str) -> str:
    """Strip any directory components so a crafted `filename` can't escape `base_path`."""
    name = PurePosixPath(filename.replace("\\", "/")).name
    return name or "file"


def _path_to_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"LocalFsStorage cannot resolve a non-file:// uri: {uri!r}")
    return Path(url2pathname(parsed.path))


class LocalFsStorage(IStorageService):
    """`IStorageService` backed by the local filesystem.

    Every `save()` writes a new file named `<uuid4hex>_<sanitized-filename>`
    under `base_path` (created if missing) and returns its absolute path as a
    `file://` uri (`pathlib.Path.as_uri()`, RFC 8089 — portable across Windows
    and POSIX; round-tripped back to a `Path` via `urllib.request.url2pathname`).

    **Documented `get_presigned_url()` behavior**: local storage has no HTTP
    layer in front of it, so there is no real time-limited "presigned URL"
    concept here. This implementation returns the same `file://` uri unchanged
    (a served-path stub) once it has confirmed the object exists — callers
    running against local storage should not expect a browser-fetchable
    HTTP(S) URL out of this method. STORY-046/STORY-047's `S3Storage`/
    `GcsStorage`/`AzureBlobStorage` implement genuine expiring presigned URLs.
    """

    def __init__(self, base_path: str | Path) -> None:
        self._base_path = Path(base_path)

    @property
    def base_path(self) -> Path:
        """The configured storage root (created lazily on first `save()`)."""
        return self._base_path

    async def save(self, filename: str, content: bytes) -> str:
        safe_name = _sanitize_filename(filename)
        key = f"{uuid4().hex}_{safe_name}"
        dest = self._base_path / key

        def _write() -> None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

        await asyncio.to_thread(_write)
        return _path_to_uri(dest)

    async def read(self, uri: str) -> bytes:
        path = _uri_to_path(uri)
        if not await asyncio.to_thread(path.is_file):
            raise StorageObjectNotFoundError(uri)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, uri: str) -> None:
        path = _uri_to_path(uri)
        if not await asyncio.to_thread(path.is_file):
            raise StorageObjectNotFoundError(uri)
        await asyncio.to_thread(path.unlink)

    async def get_presigned_url(self, uri: str, expires_in_seconds: int = 3600) -> str:
        path = _uri_to_path(uri)
        if not await asyncio.to_thread(path.is_file):
            raise StorageObjectNotFoundError(uri)
        return uri


@register_storage_service("local")
def _build_local_storage(storage_section: dict[str, Any]) -> IStorageService:
    """Registry builder used by `StorageFactory.get_storage_service()`.

    Reads `storage.local.base_path` from the resolved `system_config` section,
    falling back to `Settings.local_storage_base_path` (layers 2/3) when the
    section has no `local.base_path` value — matching `ConfigService`'s own
    default-section builder for `storage`.
    """
    settings = get_settings()
    local_section = storage_section.get("local") or {}
    base_path = local_section.get("base_path") or settings.local_storage_base_path
    return LocalFsStorage(base_path)
