"""
Canonical role definitions for the modular clinical information system.

Staff roles require authorized provisioning — never public registration.
Every staff account must be assigned to a clinic (clinic_id), except platform_owner and platform_admin.
"""

from __future__ import annotations

PUBLIC_REGISTRATION_ROLES: frozenset[str] = frozenset({"patient", "doctor"})
STAFF_ROLES: frozenset[str] = frozenset(
    {
        "platform_owner",
        "platform_admin",
        "clinic_admin",
        "admin",  # legacy alias → clinic_admin behaviour
        "receptionist",
        "cashier",
        "lab_technician",
        "pharmacist",
        "nutritionist",
        "midwife",
        "pev_agent",
        "nurse",
    }
)
PRIVILEGED_ROLES: frozenset[str] = STAFF_ROLES
PLATFORM_OWNER_ROLES: frozenset[str] = frozenset({"platform_owner"})
PLATFORM_ADMIN_ROLES: frozenset[str] = frozenset({"platform_admin"})
PLATFORM_SCOPE_ROLES: frozenset[str] = frozenset({"platform_owner", "platform_admin"})
CLINIC_ADMIN_ROLES: frozenset[str] = frozenset({"clinic_admin", "admin"})
CLINICAL_STAFF_ROLES: frozenset[str] = frozenset(
    {
        "receptionist",
        "cashier",
        "doctor",
        "lab_technician",
        "pharmacist",
        "nutritionist",
        "midwife",
        "pev_agent",
        "nurse",
    }
)
CLINIC_PORTAL_ROLES: frozenset[str] = STAFF_ROLES | frozenset({"doctor"})
ALL_ROLES: frozenset[str] = PUBLIC_REGISTRATION_ROLES | STAFF_ROLES

# Legacy / UI aliases → canonical role (DB cleanup + RBAC normalization).
ROLE_LEGACY_ALIASES: dict[str, str] = {
    "medecin": "doctor",
    "médecin": "doctor",
    "physician": "doctor",
    "professional": "doctor",
    "praticien": "doctor",
}

ROLE_LABELS: dict[str, str] = {
    "platform_owner": "PLATFORM_OWNER",
    "platform_admin": "PLATFORM_ADMIN",
    "clinic_admin": "CLINIC_ADMIN",
    "admin": "CLINIC_ADMIN",
    "receptionist": "RECEPTIONIST",
    "cashier": "CASHIER",
    "doctor": "DOCTOR",
    "lab_technician": "LAB_TECHNICIAN",
    "pharmacist": "PHARMACIST",
    "nutritionist": "NUTRITIONIST",
    "midwife": "MIDWIFE",
    "pev_agent": "PEV_AGENT",
    "nurse": "NURSE",
    "patient": "PATIENT",
}


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
            "Staff accounts cannot be created via public registration."
        )
    if normalized not in PUBLIC_REGISTRATION_ROLES:
        raise PublicRegistrationRoleError(
            f"Public registration only allows: {', '.join(sorted(PUBLIC_REGISTRATION_ROLES))}"
        )
    return normalized


def is_privileged_role(role: str) -> bool:
    return assert_known_role(role) in PRIVILEGED_ROLES


def is_clinical_staff(role: str) -> bool:
    return assert_known_role(role) in CLINICAL_STAFF_ROLES | CLINIC_ADMIN_ROLES | PLATFORM_ADMIN_ROLES


def is_clinic_portal_role(role: str) -> bool:
    return assert_known_role(role) in CLINIC_PORTAL_ROLES


def requires_clinic_assignment(role: str) -> bool:
    """Staff and clinic-affiliated doctors must have clinic_id (not platform-level roles)."""
    r = assert_known_role(role)
    if r in PLATFORM_SCOPE_ROLES:
        return False
    return r in STAFF_ROLES or r == "doctor"


def is_platform_owner_role(role: str) -> bool:
    return assert_known_role(role) in PLATFORM_OWNER_ROLES


def effective_admin_role(role: str) -> str:
    """Map legacy admin to clinic_admin for provisioning."""
    r = assert_known_role(role)
    if r == "admin":
        return "clinic_admin"
    return r


def effective_role(role: str | None) -> str:
    """Normalize stored or token role strings for RBAC (case, whitespace, legacy aliases)."""
    if role is None:
        return ""
    normalized = str(role).strip().lower()
    if not normalized:
        return ""
    return ROLE_LEGACY_ALIASES.get(normalized, normalized)


def expand_role_set(required_roles: list[str] | set[str] | tuple[str, ...]) -> set[str]:
    """Expand allowed roles with platform_owner and admin/clinic_admin aliases."""
    expanded: set[str] = set()
    for role in required_roles:
        r = effective_role(role)
        if not r:
            continue
        expanded.add(r)
        if r == "platform_admin":
            expanded.add("platform_owner")
        if r in ("admin", "clinic_admin"):
            expanded.add("admin")
            expanded.add("clinic_admin")
    return expanded


def user_has_any_role(user_role: str | None, allowed_roles: list[str] | set[str] | tuple[str, ...]) -> bool:
    effective = effective_role(user_role)
    if not effective:
        return False
    return effective in expand_role_set(allowed_roles)


def roles_equivalent(role_a: str | None, role_b: str | None) -> bool:
    return effective_role(role_a) == effective_role(role_b)
