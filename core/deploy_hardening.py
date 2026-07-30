"""
Deploy / infrastructure security helpers — Security Wave 3.

Pure helpers used by boot validation and static config tests (Docker, TLS, secrets).
"""

from __future__ import annotations

import os
import re
from urllib.parse import parse_qs, urlparse, unquote


_WEAK_DB_PASSWORDS = frozenset(
    {
        "sante_dev_password",
        "postgres",
        "password",
        "changeme",
        "change-me",
        "secret",
        "sante",
    }
)


def database_url_sslmode(database_url: str) -> str | None:
    """Return sslmode query param if present (lowercase), else None."""
    url = (database_url or "").strip()
    if not url or url.startswith("sqlite"):
        return None
    # Handle both postgresql://user:pass@host/db?sslmode=require
    # and password with special chars.
    try:
        parsed = urlparse(url.replace("postgres://", "postgresql://", 1))
        qs = parse_qs(parsed.query)
        modes = qs.get("sslmode") or qs.get("ssl")
        if modes:
            return str(modes[0]).lower()
    except Exception:
        return None
    return None


def assert_database_tls_policy(
    database_url: str,
    *,
    is_production: bool,
    railway_environment: str | None = None,
    allow_insecure_db_ssl: bool = False,
) -> None:
    """
    Reject insecure Postgres TLS settings in production.

    - sslmode=disable is always forbidden in production
    - On Railway *public* Postgres URLs, require sslmode=require (or verify-full)
    - Railway private hosts (*.railway.internal) use the platform private network;
      missing sslmode is allowed there (TLS is not offered the same way on the
      internal mesh). Still reject explicit sslmode=disable.
    """
    url = (database_url or "").strip()
    if not is_production or not url or url.startswith("sqlite"):
        return

    mode = database_url_sslmode(url)
    if mode == "disable":
        raise RuntimeError(
            "DATABASE_URL must not use sslmode=disable in production — "
            "use sslmode=require (or verify-full)"
        )

    on_railway = bool((railway_environment or "").strip())
    if on_railway and not allow_insecure_db_ssl:
        host = ""
        try:
            host = (urlparse(url.replace("postgres://", "postgresql://", 1)).hostname or "").lower()
        except Exception:
            host = ""
        private_mesh = host.endswith(".railway.internal") or host in {
            "postgres.railway.internal",
            "postgres",
        }
        if private_mesh:
            return
        if mode not in {"require", "verify-ca", "verify-full"}:
            raise RuntimeError(
                "Railway production DATABASE_URL must include sslmode=require "
                "(or verify-ca / verify-full) for public hosts. "
                "Private *.railway.internal URLs are exempt. "
                "Set ALLOW_INSECURE_DB_SSL=true only for lab."
            )


def resolve_db_sslmode_connect_arg() -> str | None:
    """
    Explicit DB_SSLMODE env wins. Otherwise Railway production defaults to require
    for public hosts only — private *.railway.internal mesh leaves libpq default.
    """
    explicit = (os.getenv("DB_SSLMODE") or "").strip().lower()
    if explicit:
        return explicit
    env = (os.getenv("ENVIRONMENT") or "").lower().strip()
    if env == "production" and (os.getenv("RAILWAY_ENVIRONMENT") or "").strip():
        url = (os.getenv("DATABASE_URL") or "").strip()
        host = ""
        try:
            host = (urlparse(url.replace("postgres://", "postgresql://", 1)).hostname or "").lower()
        except Exception:
            host = ""
        if host.endswith(".railway.internal") or host in {"postgres.railway.internal", "postgres"}:
            return None
        return "require"
    return None


def postgres_password_is_weak(password: str) -> bool:
    cleaned = unquote((password or "").strip())
    if not cleaned or len(cleaned) < 12:
        return True
    if cleaned.lower() in _WEAK_DB_PASSWORDS:
        return True
    if "sante_dev" in cleaned.lower():
        return True
    return False


def dockerfile_runs_as_non_root(dockerfile_text: str) -> bool:
    """True if image drops root via USER or gosu/su-exec to a non-root account."""
    users = re.findall(r"(?im)^\s*USER\s+(\S+)", dockerfile_text)
    if users:
        last = users[-1].strip().strip('"').strip("'")
        if last not in {"root", "0", "0:0"}:
            return True
    # Entrypoint privilege-drop pattern (gosu/su-exec appuser).
    if re.search(r"(?i)\bgosu\s+appuser\b", dockerfile_text) or re.search(
        r"(?i)\bgosu\s+appuser\b", dockerfile_text
    ):
        return True
    return bool(
        re.search(r"(?i)useradd.*appuser", dockerfile_text)
        and re.search(r"(?i)\bgosu\b", dockerfile_text)
    )


def compose_publishes_postgres(compose_text: str) -> bool:
    """Heuristic: published host mapping to container 5432."""
    return bool(re.search(r"(?m)^\s*-\s*[\"']?\d+:5432[\"']?", compose_text))


def nginx_enforces_tls12_plus(nginx_text: str) -> bool:
    return "TLSv1.2" in nginx_text and "TLSv1.3" in nginx_text and "TLSv1.0" not in nginx_text


def nginx_blocks_uploads(nginx_text: str) -> bool:
    return bool(re.search(r"location\s+/uploads/\s*\{[^}]*return\s+403", nginx_text, re.S))


def vercel_has_security_headers(vercel_json_text: str) -> bool:
    needed = (
        "Strict-Transport-Security",
        "X-Frame-Options",
        "Content-Security-Policy",
        "X-Content-Type-Options",
    )
    return all(h in vercel_json_text for h in needed)
