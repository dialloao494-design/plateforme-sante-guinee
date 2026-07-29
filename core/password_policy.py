"""Production password policy for Santé Guinée (Security Wave 0)."""

from __future__ import annotations

import os
import re

# Minimum length per approved architecture (≥12). Override only for controlled migration.
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "12"))

# Common / breached-style passwords blocked regardless of complexity.
_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password12",
        "password123",
        "password1234",
        "password12345",
        "12345678",
        "123456789",
        "1234567890",
        "qwerty123",
        "qwertyuiop",
        "admin123",
        "admin1234",
        "welcome1",
        "welcome12",
        "letmein1",
        "monkey123",
        "dragon123",
        "master123",
        "login1234",
        "passw0rd",
        "changeme",
        "changeme1",
        "sante123",
        "guinee123",
        "clinic123",
        "azerty123",
        "azertyuiop",
    }
)


def validate_password(password: str) -> bool:
    """
    Enforce staff-grade password rules.

    - length ≥ PASSWORD_MIN_LENGTH (default 12)
    - at least one uppercase, one lowercase, one digit
    - not in common-password denylist
    """
    if not isinstance(password, str):
        raise ValueError("Password must be a string")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
        )
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit")
    if password.lower().strip() in _COMMON_PASSWORDS:
        raise ValueError("Password is too common; choose a stronger password")
    # Reject passwords that are only the email-local-part pattern is handled by caller.
    return True
