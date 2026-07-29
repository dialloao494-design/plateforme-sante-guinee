"""
Clinic Node / mini-PC security helpers — Security Wave 4.

Pure functions for boot validation and static package checks.
Does not enable Offline V1 product features (sync/license UX).
"""

from __future__ import annotations

import os
import re
from pathlib import Path


def is_clinic_node_environment(environment: str | None = None) -> bool:
    env = (environment if environment is not None else os.getenv("ENVIRONMENT") or "").lower().strip()
    return env in {"clinic-node", "clinic_node"}


def secrets_are_distinct(*values: str) -> bool:
    """Return True when all non-empty secrets are pairwise distinct."""
    cleaned = [v.strip() for v in values if (v or "").strip()]
    return len(cleaned) == len(set(cleaned))


def assert_clinic_node_secret_separation(
    *,
    jwt_secret: str,
    license_secret: str = "",
    update_secret: str = "",
    attachment_key: str = "",
) -> None:
    """Reject reuse of JWT as license/update/attachment material."""
    jwt = (jwt_secret or "").strip()
    failures: list[str] = []
    if license_secret and license_secret.strip() == jwt:
        failures.append(
            "CLINIC_NODE_LICENSE_SECRET must not equal JWT_SECRET "
            "(unique per-node secret required)"
        )
    if update_secret and update_secret.strip() == jwt:
        failures.append(
            "CLINIC_NODE_UPDATE_SECRET must not equal JWT_SECRET "
            "(unique per-node secret required)"
        )
    if attachment_key and attachment_key.strip() == jwt:
        failures.append("ATTACHMENT_ENCRYPTION_KEY must not equal JWT_SECRET")
    if failures:
        raise RuntimeError("; ".join(failures))


def clinic_compose_publishes_postgres(compose_text: str) -> bool:
    return bool(re.search(r"(?m)^\s*-\s*[\"']?\d+:5432[\"']?", compose_text))


def clinic_compose_uses_bridge_network(compose_text: str) -> bool:
    return "driver: bridge" in compose_text or "networks:" in compose_text


def clinic_host_compose_binds_postgres_localhost(compose_text: str) -> bool:
    return "listen_addresses=127.0.0.1" in compose_text or "listen_addresses='127.0.0.1'" in compose_text


def clinic_nginx_enforces_tls12_plus(nginx_text: str) -> bool:
    return "TLSv1.2" in nginx_text and "TLSv1.3" in nginx_text and "TLSv1.0" not in nginx_text


def clinic_nginx_blocks_uploads(nginx_text: str) -> bool:
    return bool(re.search(r"location\s+/uploads/\s*\{[^}]*return\s+403", nginx_text, re.S))


def clinic_nginx_redirects_http_to_https(nginx_text: str) -> bool:
    return "return 301 https://" in nginx_text


def pki_permissions_are_secure(pki_dir: Path) -> tuple[bool, list[str]]:
    """Check CA/server private keys are not world-readable when present."""
    issues: list[str] = []
    if not pki_dir.is_dir():
        return True, []
    for name in ("ca.key", "privkey.pem"):
        path = pki_dir / name
        if not path.is_file():
            continue
        mode = path.stat().st_mode & 0o777
        if mode & 0o077:
            issues.append(f"{name} mode {oct(mode)} allows group/other access")
    return (len(issues) == 0), issues


def env_file_permissions_are_secure(env_path: Path) -> tuple[bool, str | None]:
    if not env_path.is_file():
        return True, None
    mode = env_path.stat().st_mode & 0o777
    if mode & 0o077:
        return False, f".env mode {oct(mode)} — expected 0600"
    return True, None
