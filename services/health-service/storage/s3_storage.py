"""S3-compatible storage for encrypted medical documents."""

import asyncio
import uuid

from cryptography.fernet import Fernet

from packages.shared_utils.document_storage import S3DocumentStore
from packages.shared_utils.vault_crypto import encrypt_document

from .local_storage import DocumentIntegrityError, encrypted_size
from packages.shared_utils.vault_crypto import MAGIC, decrypt_document
import hashlib
import hmac


class S3Storage:
    def __init__(
        self,
        bucket: str,
        endpoint: str,
        access_key: str,
        secret_key: str,
        encryption_key: str,
        region: str,
    ) -> None:
        Fernet(encryption_key.encode("ascii"))
        self._key = encryption_key
        self._store = S3DocumentStore(bucket, endpoint, access_key, secret_key, region)

    async def save(self, file_bytes: bytes, filename: str, owner_id: str) -> str:
        owner = uuid.UUID(owner_id)
        key = f"{owner}/{uuid.uuid4().hex}"
        encrypted = encrypt_document(file_bytes, self._key)
        try:
            await asyncio.to_thread(self._store.write_encrypted, key, encrypted)
        except OSError:
            raise
        return f"s3://{self._store.bucket}/{key}"

    async def delete(self, storage_path: str) -> None:
        await asyncio.to_thread(self._store.delete, storage_path)

    def exists(self, storage_path: str) -> bool:
        return self._store.exists(storage_path)

    def resolve(self, storage_path: str) -> str:
        self._store.key_for(storage_path)
        return storage_path

    def read(self, storage_path: str, expected_sha256: str | None = None) -> bytes:
        stored = self._store.read_encrypted(storage_path)
        if expected_sha256 and not stored.startswith(MAGIC):
            raise DocumentIntegrityError("Encrypted envelope missing")
        try:
            data = decrypt_document(stored, self._key)
        except Exception as exc:
            raise DocumentIntegrityError("Document authentication failed") from exc
        if expected_sha256 and not hmac.compare_digest(
            hashlib.sha256(data).hexdigest(), expected_sha256
        ):
            raise DocumentIntegrityError("Document does not match its record")
        return data

    @staticmethod
    def encrypted_size(size: int) -> int:
        return encrypted_size(size)
