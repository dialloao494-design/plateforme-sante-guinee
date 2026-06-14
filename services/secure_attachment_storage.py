"""
Opaque, non-guessable on-disk storage for clinical message attachments.

Files are stored outside any public static mount. Access is exclusively via
authenticated download endpoints with appointment-scoped authorization.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status

from core.attachment_policy import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    EXTENSION_MIME_MAP,
    LEGACY_MESSAGES_SUBDIR,
    LEGACY_PUBLIC_UPLOAD_PREFIX,
    MAX_ATTACHMENT_BYTES,
    SECURE_ATTACHMENT_ROOT,
)
from core.attachment_encryption import decrypt_blob, encrypt_blob

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredAttachment:
    storage_key: str
    original_filename: str
    mime_type: str
    size_bytes: int


class SecureAttachmentStorage:
    """Write/read attachments using opaque storage keys (never exposed in URLs)."""

    @staticmethod
    def root() -> Path:
        root = Path(os.environ.get("SECURE_ATTACHMENT_ROOT", SECURE_ATTACHMENT_ROOT))
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _absolute_path(storage_key: str) -> Path:
        if not storage_key or ".." in storage_key or "/" in storage_key or "\\" in storage_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage key")
        shard = storage_key[:2]
        return SecureAttachmentStorage.root() / shard / storage_key

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename or "")
        return cleaned[:120] or "attachment"

    @staticmethod
    def sniff_mime(content: bytes, extension: str) -> str:
        ext = extension.lower()
        if content.startswith(b"%PDF"):
            return "application/pdf"
        if content[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if content[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "image/webp"
        try:
            content[:2048].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            pass
        return "application/octet-stream"

    @staticmethod
    def validate_upload(content: bytes, extension: str) -> str:
        if len(content) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty attachment")
        if len(content) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Attachment exceeds maximum size of {MAX_ATTACHMENT_BYTES} bytes",
            )
        ext = extension.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported attachment format")

        mime = SecureAttachmentStorage.sniff_mime(content, ext)
        if mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment content does not match an allowed clinical file type",
            )
        expected = EXTENSION_MIME_MAP.get(ext)
        if expected and mime != expected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment extension does not match file content",
            )
        return mime

    @staticmethod
    def store(content: bytes, *, original_filename: str, extension: str) -> StoredAttachment:
        mime = SecureAttachmentStorage.validate_upload(content, extension)
        storage_key = secrets.token_urlsafe(32)
        target = SecureAttachmentStorage._absolute_path(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encrypt_blob(content))
        safe_name = SecureAttachmentStorage.sanitize_filename(original_filename)
        logger.info(
            "Attachment stored storage_key=%s size=%s mime=%s",
            storage_key[:8] + "...",
            len(content),
            mime,
        )
        return StoredAttachment(
            storage_key=storage_key,
            original_filename=safe_name,
            mime_type=mime,
            size_bytes=len(content),
        )

    @staticmethod
    def read(storage_key: str) -> tuple[bytes, Path]:
        path = SecureAttachmentStorage._absolute_path(storage_key)
        if not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
        return decrypt_blob(path.read_bytes()), path

    @staticmethod
    def _legacy_uploads_root() -> Path:
        return (Path("uploads") / LEGACY_MESSAGES_SUBDIR).resolve()

    @staticmethod
    def resolve_legacy_public_url(attachment_url: Optional[str]) -> Optional[Path]:
        """Map deprecated public URL to on-disk path for backward-compatible reads."""
        if not attachment_url or not attachment_url.startswith(LEGACY_PUBLIC_UPLOAD_PREFIX):
            return None
        relative = attachment_url[len(LEGACY_PUBLIC_UPLOAD_PREFIX) :].lstrip("/").replace("\\", "/")
        parts = [part for part in relative.split("/") if part]
        if not parts or parts[0] != LEGACY_MESSAGES_SUBDIR or ".." in parts:
            return None
        legacy_path = (Path("uploads") / Path(*parts)).resolve()
        if not legacy_path.is_relative_to(SecureAttachmentStorage._legacy_uploads_root()):
            return None
        if legacy_path.is_file():
            return legacy_path
        return None

    @staticmethod
    def read_legacy(attachment_url: str) -> tuple[bytes, Path]:
        path = SecureAttachmentStorage.resolve_legacy_public_url(attachment_url)
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
        return path.read_bytes(), path
