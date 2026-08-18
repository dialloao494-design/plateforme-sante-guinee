"""Canonical public frontend URL resolution for production emails and CORS.

The clinic's production SPA is the GitHub-connected Vercel project:
https://plateforme-sante-guinee.vercel.app

A legacy Vercel project (frontend-seven-rust-94) may still be present in
Railway env vars. This module remaps that host so password-reset /
email-verification links and CORS never depend on the retired project.
"""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

CANONICAL_FRONTEND_URL = "https://plateforme-sante-guinee.vercel.app"
LEGACY_FRONTEND_HOSTS = frozenset(
    {
        "frontend-seven-rust-94.vercel.app",
    }
)
_ENV_KEY = "FRONTEND_URL"


def _normalize(url: str) -> str:
    return (url or "").strip().rstrip("/")


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def raw_frontend_url_from_env() -> str:
    """Canonical frontend env value, unmodified (may contain a legacy host)."""
    return _normalize(os.getenv(_ENV_KEY) or "")


def resolve_frontend_url(*, allow_localhost_fallback: bool = True) -> str:
    """
    Effective public frontend base URL.

    - Remaps known legacy Vercel hosts to the canonical production URL.
    - Falls back to canonical URL in production-like deploys when unset.
    - Falls back to local Vite only for local/dev when allow_localhost_fallback.
    """
    raw = raw_frontend_url_from_env()
    if raw and _host(raw) in LEGACY_FRONTEND_HOSTS:
        logger.warning(
            "Remapping legacy frontend URL %s -> %s (update Railway FRONTEND_URL)",
            raw,
            CANONICAL_FRONTEND_URL,
        )
        return CANONICAL_FRONTEND_URL
    if raw:
        return raw

    # Deployed services should never emit localhost reset links.
    env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").lower()
    is_deployed = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
    if is_deployed or env in {"production", "prod", "staging"}:
        return CANONICAL_FRONTEND_URL
    # Clinic Node serves its own SPA on LAN HTTPS — never remap to Vercel.
    if env in {"clinic-node", "clinic_node"}:
        return "https://sante-locale"

    if allow_localhost_fallback:
        return "http://localhost:5173"
    return CANONICAL_FRONTEND_URL


def frontend_url_status() -> dict:
    """Non-secret status for /health/email and migration audits."""
    raw = raw_frontend_url_from_env()
    effective = resolve_frontend_url(allow_localhost_fallback=False)
    return {
        "frontend_url_set": bool(raw),
        "frontend_url_raw": raw or None,
        "frontend_url": effective,
        "frontend_url_remapped_from_legacy": bool(raw) and _host(raw) in LEGACY_FRONTEND_HOSTS,
        "canonical_frontend_url": CANONICAL_FRONTEND_URL,
        "legacy_frontend_hosts": sorted(LEGACY_FRONTEND_HOSTS),
    }
