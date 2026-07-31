"""The `storage` domain module: `IStorageService`, the file-storage abstraction.

Concrete implementations (`LocalFsStorage`, and later `S3Storage`/`GcsStorage`/
`AzureBlobStorage` in STORY-046/047) live in `app.infrastructure.storage`.
Business logic and API routers depend on `IStorageService` only, resolved via
`app.core.storage_factory.StorageFactory` (Dependency Inversion).
"""
