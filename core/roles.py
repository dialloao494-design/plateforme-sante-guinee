"""
Canonical role definitions for authorization and user provisioning.

All role assignment for new accounts MUST go through services.user_provisioning
so public registration cannot elevate to admin.
"""

from __future__ import annotations

PUBLIC_REGISTRATION_ROLES: frozenset[str] = frozenset({"patient", "doctor"})
PRIVILEGED_ROLES: frozenset[str] = frozenset({"admin"})
ALL_ROLES: frozenset[str] = PUBLIC_REGISTRATION_ROLES | PRIVILEGED_ROLES


class InvalidRoleError(ValueError):
    """Raised when a role string is not a known platform role."""


class PublicRegistrationRoleError(ValueError):
    """Raised when a role is not allowed on the public registration endpoint."""


class PrivilegedRoleAssignmentError(PermissionError):
    """Raised when a privileged role is assigned outside an authorized provisioning path."""


def normalize_role(role: str) -> str:
    if not role or not str(role).strip():
        raise InvalidRoleError("Role is required")
    return str(role).strip().lower()


def assert_known_role(role: str) -> str:
    normalized = normalize_role(role)
    if normalized not in ALL_ROLES:
        raise InvalidRoleError(
            f"Invalid role '{role}'. Must be one of: {', '.join(sorted(ALL_ROLES))}"
        )
    return normalized


def assert_public_registration_role(role: str) -> str:
    normalized = assert_known_role(role)
    if normalized in PRIVILEGED_ROLES:
        raise PublicRegistrationRoleError(
            "Administrator accounts cannot be created via public registration."
        )
    if normalized not in PUBLIC_REGISTRATION_ROLES:
        raise PublicRegistrationRoleError(
            f"Public registration only allows: {', '.join(sorted(PUBLIC_REGISTRATION_ROLES))}"
        )
    return normalized


def is_privileged_role(role: str) -> bool:
    return assert_known_role(role) in PRIVILEGED_ROLES
