"""Shared teleconsultation room naming and Jitsi URL helpers."""

from __future__ import annotations

import hashlib
import os

from services.jitsi_jwt import build_jitsi_meeting_url, is_jaas_mode, jitsi_jwt_configured

BLOCKED_EMBED_DOMAINS = frozenset({"meet.jit.si"})


def _clean_domain(value: str) -> str:
    return value.strip().replace("https://", "").replace("http://", "").rstrip("/")


def jitsi_domain() -> str:
    explicit = (os.getenv("JITSI_DOMAIN") or "").strip()
    if explicit:
        return _clean_domain(explicit)
    return _clean_domain(os.getenv("JITSI_SELF_HOSTED_DOMAIN", "127.0.0.1:8443"))


def jitsi_app_id() -> str:
    return (os.getenv("JITSI_APP_ID") or "").strip()


def is_blocked_public_embed_domain(domain: str | None = None) -> bool:
    host = _clean_domain(domain or jitsi_domain()).split(":")[0].lower()
    return host in BLOCKED_EMBED_DOMAINS


def jitsi_embed_mode() -> str:
    """jaas | self_hosted_jwt | self_hosted_open | blocked"""
    if is_jaas_mode():
        return "jaas"
    if jitsi_jwt_configured():
        return "self_hosted_jwt"
    if is_blocked_public_embed_domain():
        return "blocked"
    from core.settings import get_settings

    if get_settings().is_deployed and not _env_flag("ALLOW_OPEN_JITSI_IN_PRODUCTION"):
        return "blocked"
    return "self_hosted_open"


def _env_flag(name: str) -> bool:
    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def effective_jitsi_embed_domain() -> str:
    if jitsi_embed_mode() == "jaas":
        return "8x8.vc"
    return jitsi_domain()


def embed_block_reason() -> str | None:
    mode = jitsi_embed_mode()
    if mode == "blocked":
        if is_blocked_public_embed_domain():
            return (
                "meet.jit.si ne permet pas la vidéo intégrée (OAuth / salle réservée aux membres). "
                "Configurez JITSI_DOMAIN sur une instance Jitsi dédiée — voir deploy/jitsi/README.md."
            )
        from core.settings import get_settings

        if get_settings().is_deployed and not _env_flag("ALLOW_OPEN_JITSI_IN_PRODUCTION"):
            return (
                "En production, Jitsi doit être configuré avec JWT (JITSI_APP_SECRET ou clés JaaS). "
                "Le mode salle ouverte sans JWT est interdit."
            )
        return "Configuration vidéo indisponible pour cette téléconsultation."
    if mode == "jaas" and not jitsi_jwt_configured():
        return (
            "JaaS (8x8) requiert JITSI_APP_ID, JITSI_KEY_ID et JITSI_PRIVATE_KEY "
            "(ou JITSI_PRIVATE_KEY_PATH)."
        )
    return None


def room_name(appointment_id: int) -> str:
    salt = (os.getenv("SECRET_KEY") or "dev")[:16]
    digest = hashlib.sha256(f"{salt}:appt:{appointment_id}".encode()).hexdigest()[:12]
    return f"sante-gn-{appointment_id}-{digest}"


def meeting_link_for_appointment(appointment_id: int, *, domain: str | None = None, jwt_token: str | None = None) -> str:
    domain = domain or effective_jitsi_embed_domain()
    return build_jitsi_meeting_url(domain, room_name(appointment_id), jwt_token, jaas=is_jaas_mode())
