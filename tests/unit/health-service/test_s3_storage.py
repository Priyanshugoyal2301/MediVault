import hashlib

import pytest
from cryptography.fernet import Fernet

from packages.shared_utils.vault_crypto import MAGIC
from services.health_service.storage.local_storage import DocumentIntegrityError
from services.health_service.storage.s3_storage import S3Storage


def make_storage():
    return S3Storage(
        bucket="private-documents",
        endpoint="https://project.storage.supabase.co/storage/v1/s3",
        access_key="server-access-key",
        secret_key="server-secret-key",
        encryption_key=Fernet.generate_key().decode("ascii"),
        region="ap-south-1",
    )


def test_s3_storage_encrypts_and_verifies_document(monkeypatch):
    storage = make_storage()
    stored_objects = {}

    def write(key, data):
        stored_objects[key] = data

    def read(path):
        return stored_objects[path.removeprefix("s3://private-documents/")]

    monkeypatch.setattr(type(storage._store), "write_encrypted", lambda self, key, data: write(key, data))
    monkeypatch.setattr(type(storage._store), "read_encrypted", lambda self, path: read(path))
    monkeypatch.setattr(
        type(storage._store),
        "exists",
        lambda self, path: path.removeprefix("s3://private-documents/") in stored_objects,
    )
    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr("services.health_service.storage.s3_storage.asyncio.to_thread", run_inline)

    original = b"synthetic lab document"
    save = storage.save(original, "report.pdf", "f13d4fda-44b6-44e3-818b-1f2c7ac79d08")
    try:
        save.send(None)
    except StopIteration as completed:
        path = completed.value
    else:
        raise AssertionError("mocked storage operation unexpectedly suspended")

    assert path.startswith("s3://private-documents/f13d4fda-44b6-44e3-818b-1f2c7ac79d08/")
    assert stored_objects[next(iter(stored_objects))].startswith(MAGIC)
    assert storage.exists(path)
    assert storage.read(path, hashlib.sha256(original).hexdigest()) == original
    with pytest.raises(DocumentIntegrityError):
        storage.read(path, "0" * 64)


def test_s3_storage_rejects_references_to_other_buckets():
    storage = make_storage()
    with pytest.raises(ValueError):
        storage._store.key_for("s3://another-bucket/user/file")


def test_s3_storage_requires_https_endpoint():
    with pytest.raises(ValueError):
        S3Storage(
            bucket="private-documents",
            endpoint="http://localhost:9000",
            access_key="server-access-key",
            secret_key="server-secret-key",
            encryption_key=Fernet.generate_key().decode("ascii"),
            region="ap-south-1",
        )
