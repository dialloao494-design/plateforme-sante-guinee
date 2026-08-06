"""Shared names and defaults for browser auth cookies."""

from __future__ import annotations

import os

ACCESS_COOKIE_NAME = "sg_access"
REFRESH_COOKIE_NAME = "sg_refresh"
CSRF_COOKIE_NAME = "sg_csrf"

AUTH_COOKIE_PATH = "/"


def resolve_auth_cookie_samesite() -> str:
    """Return cookie SameSite mode for the current deployment topology.

    Production frontend (Vercel) and API (Railway) are cross-site, so browsers
    will not attach SameSite=Lax cookies on credentialed XHR/fetch. Use
    SameSite=None (with Secure) for deployed environments unless overridden.
    """
    override = (os.getenv("AUTH_COOKIE_SAMESITE") or "").strip().lower()
    if override in {"lax", "strict", "none"}:
        return override

    environment = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if os.getenv("RAILWAY_ENVIRONMENT") or environment in {"production", "staging"}:
        return "none"
    return "lax"


# Evaluated at import for callers that expect a module-level constant; helpers
# also call resolve_auth_cookie_samesite() so env changes in tests are honored.
AUTH_COOKIE_SAMESITE = resolve_auth_cookie_samesite()
