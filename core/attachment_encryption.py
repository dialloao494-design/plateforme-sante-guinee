"""
Optional Fernet encryption for clinical attachments at rest.

When ATTACHMENT_ENCRYPTION_KEY is set, blobs are encrypted before write and
decrypted on read. Plaintext legacy files remain readable until re-uploaded.

Production requires ATTACHMENT_ENCRYPTION_KEY (enforced at boot via settings).
"""

from __future__ import annotations

import os

_ENCRYPTION_MAGIC = b"\x00ATTENC\x01"
_fernet = None
_initialized = False


def encryption_enabled() -> bool:
    return bool(os.getenv("ATTACHMENT_ENCRYPTION_KEY", "").strip())


def reset_encryption_cache() -> None:
    """Clear cached Fernet instance (tests / key rotation)."""
    global _fernet, _initialized
    _fernet = None
    _initialized = False


def _get_fernet():
    global _fernet, _initialized
    if _initialized:
        return _fernet
    _initialized = True
    key = os.getenv("ATTACHMENT_ENCRYPTION_KEY", "").strip()
    if not key:
        _fernet = None
        return None
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError(
            "ATTACHMENT_ENCRYPTION_KEY is set but the 'cryptography' package is not installed."
        ) from exc
    _fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    return _fernet


def encrypt_blob(plaintext: bytes) -> bytes:
    fernet = _get_fernet()
    if fernet is None:
        return plaintext
    return _ENCRYPTION_MAGIC + fernet.encrypt(plaintext)


def decrypt_blob(payload: bytes) -> bytes:
    if not payload.startswith(_ENCRYPTION_MAGIC):
        return payload
    fernet = _get_fernet()
    if fernet is None:
        raise ValueError("Encrypted attachment found but ATTACHMENT_ENCRYPTION_KEY is not configured")
    from cryptography.fernet import InvalidToken

    try:
        return fernet.decrypt(payload[len(_ENCRYPTION_MAGIC) :])
    except InvalidToken as exc:
        raise ValueError("Attachment decryption failed — key mismatch or corrupted blob") from exc
