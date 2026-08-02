"""`IStorageService` — the file-storage abstraction all persisted-file access
goes through.

This is the Strategy interface `StorageFactory` resolves against
`system_config.storage.active` (STORY-003). Concrete implementations live in
`app.infrastructure.storage.<backend>` and self-register with the factory on
import — business logic and API routers depend on this interface only, never
on `LocalFsStorage`/`S3Storage`/... directly (Dependency Inversion).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IStorageService(ABC):
    """Persistence contract for storing/retrieving arbitrary file content.

    A `uri` returned by `save()` is an opaque identifier scoped to whichever
    backend produced it (e.g. `file://...` for `LocalFsStorage`, `s3://...`
    for a future `S3Storage`) — callers must treat it as an opaque token and
    pass it back unchanged to `read`/`delete`/`get_presigned_url`, never parse
    or construct one themselves.
    """

    @abstractmethod
    async def save(self, filename: str, content: bytes) -> str:
        """Persist `content` under a name derived from `filename` and return its `uri`.

        Implementations must not silently overwrite an existing object for the
        same `filename` — a fresh, unique `uri` is returned on every call.
        """

    @abstractmethod
    async def read(self, uri: str) -> bytes:
        """Return the bytes previously stored at `uri`.

        Raises:
            app.domain.storage.errors.StorageObjectNotFoundError: if `uri`
                doesn't identify a stored object.
        """

    @abstractmethod
    async def delete(self, uri: str) -> None:
        """Delete the object stored at `uri`.

        Raises:
            app.domain.storage.errors.StorageObjectNotFoundError: if `uri`
                doesn't identify a stored object.
        """

    @abstractmethod
    async def get_presigned_url(self, uri: str, expires_in_seconds: int = 3600) -> str:
        """Return a URL usable to fetch `uri`'s content, valid for `expires_in_seconds`.

        Remote-object backends (S3/GCS/Azure, STORY-046/STORY-047) return a
        real time-limited presigned URL. `LocalFsStorage` has no such concept
        (there's no HTTP-served path in front of the local disk yet) — see its
        docstring for the documented stub behavior.

        Raises:
            app.domain.storage.errors.StorageObjectNotFoundError: if `uri`
                doesn't identify a stored object.
        """
