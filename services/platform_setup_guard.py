"""Rate limiting for the one-time platform owner setup endpoint."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

_lock = Lock()
_attempts: dict[str, list[float]] = defaultdict(list)


def _max_attempts_per_hour() -> int:
    env = (os.getenv("ENVIRONMENT") or "development").lower().strip()
    if env == "production":
        return int(os.getenv("PLATFORM_SETUP_MAX_PER_HOUR", "3"))
    return int(os.getenv("PLATFORM_SETUP_MAX_PER_HOUR", "20"))


def enforce_setup_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_seconds = 3600

    with _lock:
        bucket = _attempts[client_ip]
        _attempts[client_ip] = [ts for ts in bucket if now - ts < window_seconds]
        if len(_attempts[client_ip]) >= _max_attempts_per_hour():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many setup attempts. Try again later.",
            )
        _attempts[client_ip].append(now)
