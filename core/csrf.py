"""CSRF protection for cookie-authenticated browser requests."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from core.auth_cookie_config import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

CSRF_EXEMPT_SUFFIXES = (
    "/auth/login",
    "/auth/login-json",
    "/auth/register",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/verify-email",
    "/auth/resend-verification",
    "/platform/setup",
)


def _has_bearer_authorization(request: Request) -> bool:
    return (request.headers.get("authorization") or "").lower().startswith("bearer ")


def _is_exempt_path(path: str) -> bool:
    normalized = (path or "").rstrip("/") or "/"
    return any(normalized.endswith(suffix.rstrip("/")) for suffix in CSRF_EXEMPT_SUFFIXES)


def _uses_cookie_auth(request: Request) -> bool:
    # Bearer clients/tests remain API-token authenticated even if the test client
    # also has cookies from a prior login in its jar.
    return bool(request.cookies.get(ACCESS_COOKIE_NAME)) and not _has_bearer_authorization(request)


def validate_csrf(request: Request) -> None:
    if request.method.upper() not in MUTATING_METHODS:
        return
    if _is_exempt_path(request.url.path):
        return
    if not _uses_cookie_auth(request):
        return

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME) or ""
    header_token = request.headers.get("x-csrf-token") or ""
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )


async def csrf_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    try:
        validate_csrf(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)
