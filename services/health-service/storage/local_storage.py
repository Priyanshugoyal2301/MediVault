"""
health-service/storage/local_storage.py

Local-disk storage backend for dev. Files are namespaced by owner_id so
two users uploading a file with the same name don't collide.
"""

import uuid
from pathlib import Path

from packages.shared_utils import get_logger

logger = get_logger(__name__)


class LocalStorage:
    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)

    async def save(self, file_bytes: bytes, filename: str, owner_id: str) -> str:
        """Save file under base_path/owner_id/uuid_filename. Returns storage_path."""
        owner_dir = self._base / owner_id
        owner_dir.mkdir(parents=True, exist_ok=True)

        # Prepend a UUID to prevent filename collisions on repeated uploads
        unique_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        dest = owner_dir / unique_name
        dest.write_bytes(file_bytes)

        storage_path = str(dest)
        logger.info("File saved: owner_id=%s path_suffix=%s", owner_id, unique_name)
        return storage_path

    async def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
            logger.info("File deleted: storage_path=<redacted>")
