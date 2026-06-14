"""
Production RBAC permission matrix for the clinic information system.

Each staff role is scoped to its operational workflow. Clinic admin manages
users, audit and settings — not clinical write paths for other modules.
"""

from __future__ import annotations

from enum import Enum

from fastapi import HTTPException, status

from models.user import User


class Permission(str, Enum):
    RECEPTION_QUEUE = "reception.queue"
    RECEPTION_INTAKE = "reception.intake"
    RECEPTION_APPOINTMENTS = "reception.appointments"
    DOCTOR_QUEUE = "doctor.queue"
    DOCTOR_CONSULTATION = "doctor.consultation"
    LAB_ORDERS = "lab.orders"
    PHARMACY_ORDERS = "pharmacy.orders"
    BILLING_READ = "billing.read"
    BILLING_PAY = "billing.pay"
    BILLING_REVENUE = "billing.revenue"
    ADMIN_CLINIC = "admin.clinic"
    ADMIN_STAFF = "admin.staff"
    ADMIN_AUDIT = "admin.audit"
    ADMIN_BACKUP = "admin.backup"
    PATIENT_JOURNEY = "patient.journey"
    CLINIC_OPERATIONS = "clinic.operations"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "receptionist": frozenset(
        {
            Permission.RECEPTION_QUEUE,
            Permission.RECEPTION_INTAKE,
            Permission.RECEPTION_APPOINTMENTS,
            Permission.BILLING_READ,
            Permission.BILLING_PAY,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
        }
    ),
    "cashier": frozenset(
        {
            Permission.RECEPTION_QUEUE,
            Permission.RECEPTION_INTAKE,
            Permission.RECEPTION_APPOINTMENTS,
            Permission.BILLING_READ,
            Permission.BILLING_PAY,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
        }
    ),
    "doctor": frozenset(
        {
            Permission.DOCTOR_QUEUE,
            Permission.DOCTOR_CONSULTATION,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
        }
    ),
    "lab_technician": frozenset(
        {
            Permission.LAB_ORDERS,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
        }
    ),
    "pharmacist": frozenset(
        {
            Permission.PHARMACY_ORDERS,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
        }
    ),
    "admin": frozenset(
        {
            Permission.ADMIN_CLINIC,
            Permission.ADMIN_STAFF,
            Permission.ADMIN_AUDIT,
            Permission.ADMIN_BACKUP,
            Permission.BILLING_REVENUE,
            Permission.CLINIC_OPERATIONS,
        }
    ),
}

# Legacy tuple exports for clinical_access / routers (no cross-role admin access).
RECEPTION_ROLES = ("receptionist",)
CASHIER_ROLES = ("cashier",)
DOCTOR_ROLES = ("doctor",)
LAB_ROLES = ("lab_technician",)
PHARMACY_ROLES = ("pharmacist",)
ADMIN_ROLES = ("admin",)
CLINIC_OPS_ROLES = (
    "admin",
    "receptionist",
    "cashier",
    "doctor",
    "lab_technician",
    "pharmacist",
)

BILLING_READ_ROLES = ("receptionist", "cashier", "admin")
BILLING_PAY_ROLES = ("receptionist", "cashier")
BILLING_REVENUE_ROLES = ("admin",)
LAB_QUEUE_ROLES = LAB_ROLES + ADMIN_ROLES
PHARMACY_QUEUE_ROLES = PHARMACY_ROLES + ADMIN_ROLES


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(user: User, permission: Permission) -> bool:
    return permission in permissions_for_role(user.role)


def assert_permission(user: User, permission: Permission) -> None:
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value}",
        )


def assert_any_permission(user: User, *permissions: Permission) -> None:
    role_perms = permissions_for_role(user.role)
    if not any(p in role_perms for p in permissions):
        names = [p.value for p in permissions]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of permissions: {names}",
        )
