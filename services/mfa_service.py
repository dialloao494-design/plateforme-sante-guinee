"""Optional TOTP MFA helpers (Security Wave 0). Enforcement via MFA_REQUIRED_ROLES."""

from __future__ import annotations

import os
from typing import Iterable

import pyotp

from core.roles import effective_role
from models.user import User

# Comma-separated roles that must enroll MFA. Empty = opt-in only (clinic UX safe default).
_MFA_REQUIRED = {
    r.strip().lower()
    for r in (os.getenv("MFA_REQUIRED_ROLES") or "").split(",")
    if r.strip()
}


def mfa_required_for_user(user: User) -> bool:
    role = effective_role(user.role)
    return role in _MFA_REQUIRED


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(*, email: str, secret: str) -> str:
    issuer = os.getenv("MFA_ISSUER", "Sante Guinee")
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(str(code).strip(), valid_window=1))


def user_needs_mfa_challenge(user: User) -> bool:
    return bool(getattr(user, "mfa_enabled", False) and getattr(user, "mfa_secret", None))
