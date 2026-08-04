"""Helpers for issuing and clearing browser auth cookies."""

from __future__ import annotations

import os
import secrets

from fastapi import Request, Response

from core.auth_cookie_config import (
    ACCESS_COOKIE_NAME,
    AUTH_COOKIE_PATH,
    AUTH_COOKIE_SAMESITE,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)
from services.auth_session_service import REFRESH_TOKEN_EXPIRE_DAYS


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def should_use_secure_cookies(request: Request | None = None) -> bool:
    override = os.getenv("AUTH_COOKIE_SECURE")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    if request is not None and request.url.scheme == "https":
        return True
    environment = (os.getenv("ENVIRONMENT") or "").strip().lower()
    return environment in {"production", "staging"} or bool(os.getenv("RAILWAY_ENVIRONMENT"))


def _set_cookie(
    response: Response,
    *,
    key: str,
    value: str,
    max_age: int,
    httponly: bool,
    secure: bool,
) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        expires=max_age,
        path=AUTH_COOKIE_PATH,
        secure=secure,
        httponly=httponly,
        samesite=AUTH_COOKIE_SAMESITE,
    )


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    access_max_age: int,
    request: Request | None = None,
    csrf_token: str | None = None,
) -> str:
    """Set HttpOnly access/refresh cookies plus a readable CSRF cookie."""
    secure = should_use_secure_cookies(request)
    csrf = csrf_token or generate_csrf_token()
    _set_cookie(
        response,
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=access_max_age,
        httponly=True,
        secure=secure,
    )
    _set_cookie(
        response,
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=secure,
    )
    _set_cookie(
        response,
        key=CSRF_COOKIE_NAME,
        value=csrf,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=False,
        secure=secure,
    )
    return csrf


def ensure_csrf_cookie(response: Response, request: Request | None = None) -> str:
    csrf = request.cookies.get(CSRF_COOKIE_NAME) if request is not None else None
    if csrf:
        return csrf
    csrf = generate_csrf_token()
    _set_cookie(
        response,
        key=CSRF_COOKIE_NAME,
        value=csrf,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=False,
        secure=should_use_secure_cookies(request),
    )
    return csrf


def clear_auth_cookies(response: Response, request: Request | None = None) -> None:
    secure = should_use_secure_cookies(request)
    for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, CSRF_COOKIE_NAME):
        response.delete_cookie(
            key=name,
            path=AUTH_COOKIE_PATH,
            secure=secure,
            httponly=name != CSRF_COOKIE_NAME,
            samesite=AUTH_COOKIE_SAMESITE,
        )
