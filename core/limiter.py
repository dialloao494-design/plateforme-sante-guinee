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


def forgot_password_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_FORGOT_PASSWORD", "10/hour")


def register_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_REGISTER", "5/minute")


def setup_rate_limit() -> str:
    """First-time platform owner setup — strict in production."""
    explicit = (os.getenv("RATE_LIMIT_PLATFORM_SETUP") or "").strip()
    if explicit:
        return explicit
    env = (os.getenv("ENVIRONMENT") or "development").lower().strip()
    if env == "production":
        return "3/hour"
    return "20/hour"


def heavy_mutation_rate_limit() -> str:
    """Pay / PDF — protect DB without blocking clinic LAN workflows."""
    return os.getenv("RATE_LIMIT_HEAVY", "60/minute")


def search_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_SEARCH", "90/minute")
