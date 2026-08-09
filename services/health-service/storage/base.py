"""
health-service/storage/base.py

Protocol (interface) for file storage backends.
Swap between local disk (dev) and S3-compatible (prod) without touching
the report upload endpoint — per 02_ARCHITECTURE.md §6 abstraction intent.
"""

from typing import Protocol


class StorageBackend(Protocol):
    async def save(self, file_bytes: bytes, filename: str, owner_id: str) -> str:
        """
        Persist file_bytes. Returns the storage_path to record in the DB.
        owner_id is used to namespace files per user (prevents path collisions).
        """
        ...

    async def delete(self, storage_path: str) -> None:
        """Hard-delete a stored file. Called on report deletion."""
        ...
