"""
health-service/storage/local_storage.py

Local-disk storage backend for dev. Files are namespaced by owner_id so
two users uploading a file with the same name don't collide.
"""

import uuid
import hashlib
import hmac
import os
import shutil
from cryptography.fernet import Fernet, InvalidToken
from packages.shared_utils.vault_crypto import MAGIC, encrypt_document, decrypt_document
from pathlib import Path

from packages.shared_utils import get_logger

logger = get_logger(__name__)


class StorageFullError(OSError):
    pass


class DocumentIntegrityError(ValueError):
    pass


def encrypted_size(size):
    """Exact Fernet/base64 envelope size without allocating the encrypted file."""
    return len(MAGIC)+4*((57+16*(size//16+1)+2)//3)


class LocalStorage:
    def __init__(self, base_path: str, encryption_key: str, min_free_bytes: int = 0) -> None:
        self._base = Path(base_path).resolve()
        Fernet(encryption_key.encode("ascii"))
        self._key = encryption_key
        self._min_free_bytes = min_free_bytes

    async def save(self, file_bytes: bytes, filename: str, owner_id: str) -> str:
        """Save file under base_path/owner_id/uuid_filename. Returns storage_path."""
        owner_dir = self._base / str(uuid.UUID(owner_id))
        owner_dir.mkdir(parents=True, exist_ok=True)
        if not owner_dir.resolve().is_relative_to(self._base):
            raise ValueError('Upload directory is outside the vault')
        if shutil.disk_usage(self._base).free < self._min_free_bytes+encrypted_size(len(file_bytes)):
            raise StorageFullError('Insufficient vault disk space')

        # Prepend a UUID to prevent filename collisions on repeated uploads
        unique_name = uuid.uuid4().hex
        dest = owner_dir / unique_name
        try:
            with dest.open('xb') as output:
                output.write(encrypt_document(file_bytes, self._key))
                output.flush()
                os.fsync(output.fileno())
        except Exception:
            dest.unlink(missing_ok=True)
            raise

        storage_path = str(dest)
        logger.info("File saved: owner_id=%s", owner_id)
        return storage_path

    async def delete(self, storage_path: str) -> None:
        if storage_path.startswith("demo://"):
            return
        path = self.resolve(storage_path)
        if path.exists():
            path.unlink()
            logger.info("File deleted: storage_path=<redacted>")

    def resolve(self, storage_path: str) -> Path:
        path = Path(storage_path).resolve()
        if not path.is_relative_to(self._base) or path == self._base:
            raise ValueError("Storage path is outside the vault")
        return path

    def exists(self, storage_path: str) -> bool:
        try:
            return self.resolve(storage_path).is_file()
        except (OSError, ValueError):
            return False

    def read(self, storage_path: str, expected_sha256: str | None = None) -> bytes:
        stored=self.resolve(storage_path).read_bytes()
        if expected_sha256 and not stored.startswith(MAGIC):
            raise DocumentIntegrityError('Encrypted envelope missing')
        try:
            data=decrypt_document(stored, self._key)
        except InvalidToken:
            raise DocumentIntegrityError('Document authentication failed') from None
        if expected_sha256 and not hmac.compare_digest(hashlib.sha256(data).hexdigest(),expected_sha256):
            raise DocumentIntegrityError('Document does not match its record')
        return data
