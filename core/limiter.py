"""API rate limiting (slowapi)."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_default = os.getenv("RATE_LIMIT_DEFAULT", "200/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[_default])


def login_rate_limit() -> str:
    """Per-IP login cap — higher in dev/QA, conservative in production."""
    explicit = (os.getenv("RATE_LIMIT_LOGIN") or "").strip()
    if explicit:
        return explicit
    env = (os.getenv("ENVIRONMENT") or "development").lower().strip()
    if env == "production":
        return "30/minute"
    return "120/minute"


def register_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_REGISTER", "5/minute")
