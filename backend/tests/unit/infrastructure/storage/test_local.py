"""Unit tests for `LocalFsStorage` — the round-trip proof required by
STORY-005's acceptance criteria ("Round-trip save->read->delete test passes")
plus the documented `get_presigned_url` stub behavior, all against a `tmp_path`
so no real project directory is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.storage.errors import StorageObjectNotFoundError
from app.infrastructure.storage.local import LocalFsStorage, _sanitize_filename


@pytest.mark.asyncio
async def test_save_read_delete_round_trip(tmp_path: Path) -> None:
    storage = LocalFsStorage(base_path=tmp_path)

    uri = await storage.save("hello.txt", b"hello world")

    assert uri.startswith("file://")
    read_back = await storage.read(uri)
    assert read_back == b"hello world"

    await storage.delete(uri)

    with pytest.raises(StorageObjectNotFoundError):
        await storage.read(uri)


@pytest.mark.asyncio
async def test_save_creates_base_path_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "dir"
    storage = LocalFsStorage(base_path=nested)

    uri = await storage.save("a.bin", b"\x00\x01")

    assert nested.is_dir()
    assert await storage.read(uri) == b"\x00\x01"


@pytest.mark.asyncio
async def test_save_generates_unique_uri_per_call(tmp_path: Path) -> None:
    storage = LocalFsStorage(base_path=tmp_path)

    uri_one = await storage.save("same-name.txt", b"first")
    uri_two = await storage.save("same-name.txt", b"second")

    assert uri_one != uri_two
    assert await storage.read(uri_one) == b"first"
    assert await storage.read(uri_two) == b"second"


@pytest.mark.asyncio
async def test_save_sanitizes_path_traversal_in_filename(tmp_path: Path) -> None:
    storage = LocalFsStorage(base_path=tmp_path)

    uri = await storage.save("../../etc/passwd", b"payload")

    stored_path = Path(uri.removeprefix("file:///"))
    # Resolved storage path must stay under tmp_path, not escape it.
    assert tmp_path.resolve() in stored_path.resolve().parents or (
        tmp_path.resolve() == stored_path.resolve().parent
    )


@pytest.mark.asyncio
async def test_read_missing_uri_raises_storage_object_not_found(tmp_path: Path) -> None:
    storage = LocalFsStorage(base_path=tmp_path)
    missing_uri = (tmp_path / "does-not-exist.txt").resolve().as_uri()

    with pytest.raises(StorageObjectNotFoundError):
        await storage.read(missing_uri)


@pytest.mark.asyncio
async def test_delete_missing_uri_raises_storage_object_not_found(tmp_path: Path) -> None:
    storage = LocalFsStorage(base_path=tmp_path)
    missing_uri = (tmp_path / "does-not-exist.txt").resolve().as_uri()

    with pytest.raises(StorageObjectNotFoundError):
        await storage.delete(missing_uri)


@pytest.mark.asyncio
async def test_get_presigned_url_returns_the_same_file_uri_stub(tmp_path: Path) -> None:
    """Documented behavior: local storage has no HTTP layer, so the "presigned
    URL" is the `file://` uri itself, returned once existence is confirmed.
    """
    storage = LocalFsStorage(base_path=tmp_path)
    uri = await storage.save("doc.pdf", b"%PDF-1.4")

    presigned = await storage.get_presigned_url(uri)

    assert presigned == uri


@pytest.mark.asyncio
async def test_get_presigned_url_missing_uri_raises_storage_object_not_found(
    tmp_path: Path,
) -> None:
    storage = LocalFsStorage(base_path=tmp_path)
    missing_uri = (tmp_path / "ghost.txt").resolve().as_uri()

    with pytest.raises(StorageObjectNotFoundError):
        await storage.get_presigned_url(missing_uri)


def test_sanitize_filename_strips_directory_components() -> None:
    assert _sanitize_filename("../../etc/passwd") == "passwd"
    assert _sanitize_filename("a/b/c.txt") == "c.txt"
    assert _sanitize_filename("plain.txt") == "plain.txt"
    assert _sanitize_filename("") == "file"
