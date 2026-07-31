"""Domain-level errors for the storage module.

Kept in the domain layer (not any infra layer) so callers can catch a stable
exception type regardless of which `IStorageService` implementation is active
(Dependency Inversion / Liskov: every implementation — `LocalFsStorage`,
`S3Storage`, `GcsStorage`, `AzureBlobStorage` — must raise these, not a
driver-specific exception like `FileNotFoundError` or `botocore.exceptions.ClientError`).
"""

from __future__ import annotations


class StorageObjectNotFoundError(Exception):
    """Raised by `IStorageService.read`/`delete`/`get_presigned_url` for an unknown `uri`."""

    def __init__(self, uri: str) -> None:
        self.uri = uri
        super().__init__(f"No stored object found for uri {uri!r}")
