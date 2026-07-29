#!/usr/bin/env python3
"""Smoke checks for Security Wave 2 document / attachment controls."""

from __future__ import annotations

import os
import sys

# Ensure repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main() -> int:
    failures: list[str] = []

    from core.attachment_policy import PHI_DOWNLOAD_HEADERS, phi_download_headers
    from core.attachment_malware import virus_scan_mode
    from core.output_encoding import escape_pdf_paragraph
    from core.attachment_encryption import encryption_enabled, reset_encryption_cache

    if "no-store" not in PHI_DOWNLOAD_HEADERS.get("Cache-Control", ""):
        failures.append("PHI_DOWNLOAD_HEADERS missing no-store")
    headers = phi_download_headers(filename="rx.pdf", content_sha256="abc")
    if headers.get("X-Content-SHA256") != "abc":
        failures.append("phi_download_headers missing X-Content-SHA256")
    if "&lt;" not in escape_pdf_paragraph("<script>"):
        failures.append("escape_pdf_paragraph failed")
    if virus_scan_mode() not in {"off", "stub", "clamav", "0", "false", "no", "disabled", ""}:
        # mode may be whatever is set; just ensure callable
        pass

    reset_encryption_cache()
    _ = encryption_enabled()

    from services.secure_attachment_storage import SecureAttachmentStorage

    digest = SecureAttachmentStorage.content_sha256(b"test")
    if len(digest) != 64:
        failures.append("content_sha256 length")

    if failures:
        print("WAVE2 SMOKE FAIL:", "; ".join(failures))
        return 1
    print("WAVE2 SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
