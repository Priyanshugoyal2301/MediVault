"""Authenticated encryption for stored originals. Key material never goes to clients."""
from cryptography.fernet import Fernet

MAGIC = b"MEDIVAULT-ENC-1\n"


def encrypt_document(data: bytes, key: str) -> bytes:
    return MAGIC + Fernet(key.encode("ascii")).encrypt(data)


def decrypt_document(data: bytes, key: str) -> bytes:
    if not data.startswith(MAGIC):
        # Backwards-compatible reads for pre-encryption originals. New writes
        # always encrypt; operators must migrate legacy files before deployment.
        return data
    return Fernet(key.encode("ascii")).decrypt(data[len(MAGIC):])
