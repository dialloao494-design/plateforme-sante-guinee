"""
Jitsi JWT token generation for self-hosted (HS256) and 8x8 JaaS (RS256).

Public meet.jit.si does not accept custom JWT and blocks iframe embed (membersOnly / OAuth).
Use a self-hosted Jitsi (deploy/jitsi) or 8x8 JaaS with credentials below.
"""

from __future__ import annotations

import os
import time
from typing import Any

import jwt


def _clean_domain(value: str) -> str:
    return value.strip().replace("https://", "").replace("http://", "").rstrip("/")


def is_jaas_mode() -> bool:
    app_id = (os.getenv("JITSI_APP_ID") or "").strip()
    if app_id.startswith("vpaas-magic-cookie-"):
        return True
    return os.getenv("JITSI_JAAS", "").lower() in ("1", "true", "yes")


def jaas_private_key() -> str | None:
    path = (os.getenv("JITSI_PRIVATE_KEY_PATH") or "").strip()
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip()
    raw = (os.getenv("JITSI_PRIVATE_KEY") or "").replace("\\n", "\n").strip()
    return raw or None


def jaas_key_id() -> str | None:
    value = (os.getenv("JITSI_KEY_ID") or "").strip()
    return value or None


def jitsi_jwt_configured() -> bool:
    if is_jaas_mode():
        return bool((os.getenv("JITSI_APP_ID") or "").strip() and jaas_private_key() and jaas_key_id())
    app_id = (os.getenv("JITSI_APP_ID") or "").strip()
    secret = (os.getenv("JITSI_APP_SECRET") or os.getenv("JITSI_APP_KEY") or "").strip()
    return bool(app_id and secret)


def _build_selfhosted_jwt(
    *,
    room: str,
    display_name: str,
    email: str | None,
    moderator: bool,
    ttl_seconds: int,
) -> str | None:
    app_id = (os.getenv("JITSI_APP_ID") or "").strip()
    secret = (os.getenv("JITSI_APP_SECRET") or os.getenv("JITSI_APP_KEY") or "").strip()
    if not app_id or not secret:
        return None

    domain = _clean_domain(os.getenv("JITSI_DOMAIN") or os.getenv("JITSI_SELF_HOSTED_DOMAIN", "127.0.0.1:8443"))
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
            },
            "features": {
                "livestreaming": False,
                "recording": False,
                "transcription": False,
                "outbound-call": False,
            },
        },
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _build_jaas_jwt(
    *,
    room: str,
    display_name: str,
    email: str | None,
    moderator: bool,
    ttl_seconds: int,
) -> str | None:
    app_id = (os.getenv("JITSI_APP_ID") or "").strip()
    private_key = jaas_private_key()
    key_id = jaas_key_id()
    if not app_id or not private_key or not key_id:
        return None

    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": "chat",
        "sub": app_id,
        "aud": "jitsi",
        "room": room,
        "exp": now + ttl_seconds,
        "nbf": now - 10,
        "context": {
            "user": {
                "name": display_name or "Participant",
                "email": email or "participant@sante.local",
                "moderator": "true" if moderator else "false",
                "id": email or f"user-{display_name}",
            },
            "features": {
                "livestreaming": "false",
                "recording": "false",
                "transcription": "false",
                "outbound-call": "false",
            },
            "room": {"regex": False},
        },
    }
    headers = {"kid": key_id, "typ": "JWT", "alg": "RS256"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


def build_jitsi_jwt(
    *,
    room: str,
    display_name: str,
    email: str | None = None,
    moderator: bool = False,
    ttl_seconds: int = 3600,
) -> str | None:
    if is_jaas_mode():
        return _build_jaas_jwt(
            room=room,
            display_name=display_name,
            email=email,
            moderator=moderator,
            ttl_seconds=ttl_seconds,
        )
    return _build_selfhosted_jwt(
        room=room,
        display_name=display_name,
        email=email,
        moderator=moderator,
        ttl_seconds=ttl_seconds,
    )


def build_jitsi_meeting_url(domain: str, room: str, token: str | None = None, *, jaas: bool = False) -> str:
    host = _clean_domain(domain)
    if jaas:
        app_id = (os.getenv("JITSI_APP_ID") or "").strip()
        base = f"https://{host}/{app_id}/{room}" if app_id else f"https://{host}/{room}"
    else:
        base = f"https://{host}/{room}"
    if token:
        return f"{base}?jwt={token}"
    return base
