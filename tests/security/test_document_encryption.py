import uuid
from cryptography.fernet import Fernet, InvalidToken
import pytest
from packages.shared_utils.vault_crypto import MAGIC, decrypt_document, encrypt_document
from services.health_service.storage.local_storage import LocalStorage


def test_encryption_authenticates_contents_and_uses_unique_nonces():
    key=Fernet.generate_key().decode()
    plain=b"Synthetic private prescription"
    encrypted=encrypt_document(plain,key)
    assert encrypted.startswith(MAGIC)
    assert plain not in encrypted
    assert encrypt_document(plain,key)!=encrypted
    assert decrypt_document(encrypted,key)==plain
    with pytest.raises(InvalidToken):
        decrypt_document(encrypted,Fernet.generate_key().decode())
    damaged=encrypted[:-6]+b"AAAAAA"
    with pytest.raises(InvalidToken):
        decrypt_document(damaged,key)


@pytest.mark.asyncio
async def test_storage_does_not_keep_filename_or_plaintext_and_denies_escape(tmp_path):
    storage=LocalStorage(str(tmp_path),Fernet.generate_key().decode())
    path=await storage.save(b"private test bytes","personal-name-prescription.pdf",str(uuid.uuid4()))
    assert 'personal-name' not in path
    assert storage.resolve(path).read_bytes().startswith(MAGIC)
    assert storage.read(path)==b"private test bytes"
    with pytest.raises(ValueError):
        storage.resolve(str(tmp_path.parent/'outside'))
    with pytest.raises(ValueError):
        await storage.delete(str(tmp_path.parent/'outside'))
    await storage.delete(path)
    assert not storage.resolve(path).exists()


def test_missing_key_cannot_create_storage(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(str(tmp_path),'')
