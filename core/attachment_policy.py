"""
Clinical attachment policy — allowed types, size limits, security headers.
"""

from __future__ import annotations

import os

# Maximum attachment size (default 10 MiB — suitable for PDF prescriptions / imaging snapshots).
MAX_ATTACHMENT_BYTES = int(os.getenv("ATTACHMENT_MAX_BYTES", str(10 * 1024 * 1024)))

ALLOWED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"})

ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
        "text/plain",
    }
)

# Extension → expected MIME for validation after magic-byte sniffing.
EXTENSION_MIME_MAP = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".txt": "text/plain",
}

SECURE_ATTACHMENT_ROOT = os.getenv("SECURE_ATTACHMENT_ROOT", "uploads/secure")

# Legacy public mount path — must never be served without auth.
LEGACY_PUBLIC_UPLOAD_PREFIX = "/uploads/"

# Only this subtree under uploads/ may be resolved for legacy DB rows.
LEGACY_MESSAGES_SUBDIR = "messages"

# PHI download response headers (no cache, no MIME sniffing).
PHI_DOWNLOAD_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


def phi_download_headers(*, filename: str, content_sha256: str | None = None) -> dict[str, str]:
    """Safe Content-Disposition + anti-caching headers for medical downloads."""
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in (filename or "document"))[:120]
    headers = {
        **PHI_DOWNLOAD_HEADERS,
        "Content-Disposition": f'attachment; filename="{safe or "document"}"',
    }
    if content_sha256:
        headers["X-Content-SHA256"] = content_sha256
    return headers
