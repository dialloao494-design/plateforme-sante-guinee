"""Failed cipher initialization must not make a later upload write plaintext."""
import pytest
from concurrent.futures import ThreadPoolExecutor

from core import attachment_encryption as encryption


def test_failed_encryption_initialization_still_rejects_retry(monkeypatch):
    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", "invalid-fernet-key")
    encryption.reset_encryption_cache()
    try:
        for _ in range(2):
            with pytest.raises(ValueError):
                encryption.encrypt_blob(b"synthetic clinical content")
    finally:
        encryption.reset_encryption_cache()


def test_concurrent_uploads_share_a_fully_initialized_cipher(monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    encryption.reset_encryption_cache()
    try:
        content = b"synthetic clinical content"
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(encryption.encrypt_blob, [content] * 16))
        assert all(blob.startswith(encryption._ENCRYPTION_MAGIC) for blob in results)
        assert all(encryption.decrypt_blob(blob) == content for blob in results)
    finally:
        encryption.reset_encryption_cache()
