"""
Jitsi JWT token generation for self-hosted / 8x8 JaaS instances.

Public meet.jit.si does not accept custom JWT — configure JITSI_APP_ID + JITSI_APP_SECRET
on your own Jitsi deployment or 8x8 Video.
"""

from __future__ import annotations

import os
import time
from typing import Any

from jose import jwt


def jitsi_jwt_configured() -> bool:
    app_id = (os.getenv("JITSI_APP_ID") or "").strip()
    secret = (os.getenv("JITSI_APP_SECRET") or os.getenv("JITSI_APP_KEY") or "").strip()
    return bool(app_id and secret)


def build_jitsi_jwt(
    *,
    room: str,
    display_name: str,
    email: str | None = None,
    moderator: bool = False,
    ttl_seconds: int = 3600,
) -> str | None:
    app_id = (os.getenv("JITSI_APP_ID") or "").strip()
    secret = (os.getenv("JITSI_APP_SECRET") or os.getenv("JITSI_APP_KEY") or "").strip()
    if not app_id or not secret:
        return None

    domain = (os.getenv("JITSI_DOMAIN") or "meet.jit.si").strip()
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": app_id,
        "sub": domain,
        "aud": "jitsi",
        "room": room,
        "exp": now + ttl_seconds,
        "nbf": now - 10,
        "context": {
            "user": {
                "name": display_name or "Participant",
                "email": email or "participant@sante.local",
                "moderator": moderator,
            }
        },
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def build_jitsi_meeting_url(domain: str, room: str, token: str | None = None) -> str:
    base = f"https://{domain.rstrip('/')}/{room}"
    if token:
        return f"{base}?jwt={token}"
    return base
