"""
Production RBAC permission matrix for the clinic information system.

Each staff role is scoped to its operational workflow. Clinic admin manages
users, audit and settings — not clinical write paths for other modules.
"""

from __future__ import annotations

from enum import Enum

from fastapi import HTTPException, status

from core.roles import effective_role
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
    BILLING_OVERRIDE = "billing.override"
    BILLING_FREE_TEXT = "billing.free_text"
    ADMIN_CLINIC = "admin.clinic"
    ADMIN_STAFF = "admin.staff"
    ADMIN_AUDIT = "admin.audit"
    ADMIN_BACKUP = "admin.backup"
    ADMISSION_MANAGE = "admission.manage"
    ADMISSION_BEDS = "admission.beds"
    PATIENT_JOURNEY = "patient.journey"
    CLINIC_OPERATIONS = "clinic.operations"
    PLATFORM_SYSTEM = "platform.system"
    PLATFORM_SETTINGS = "platform.settings"
    PLATFORM_SUBSCRIPTIONS = "platform.subscriptions"
    NUTRITION_ASSESS = "nutrition.assess"
    NUTRITION_READ = "nutrition.read"
    IMMUNIZATION_ADMINISTER = "immunization.administer"
    IMMUNIZATION_READ = "immunization.read"


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
            Permission.ADMISSION_MANAGE,
            Permission.ADMISSION_BEDS,
            Permission.IMMUNIZATION_READ,
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
            Permission.ADMISSION_BEDS,
        }
    ),
    "doctor": frozenset(
        {
            Permission.DOCTOR_QUEUE,
            Permission.DOCTOR_CONSULTATION,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
            Permission.ADMISSION_MANAGE,
            Permission.IMMUNIZATION_READ,
            Permission.NUTRITION_READ,
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
    "nutritionist": frozenset(
        {
            Permission.NUTRITION_ASSESS,
            Permission.NUTRITION_READ,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
        }
    ),
    "midwife": frozenset(
        {
            Permission.NUTRITION_ASSESS,
            Permission.NUTRITION_READ,
            Permission.IMMUNIZATION_ADMINISTER,
            Permission.IMMUNIZATION_READ,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
            Permission.RECEPTION_INTAKE,
        }
    ),
    "nurse": frozenset(
        {
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
            Permission.RECEPTION_INTAKE,
            Permission.NUTRITION_READ,
            Permission.IMMUNIZATION_READ,
            Permission.ADMISSION_MANAGE,
            Permission.ADMISSION_BEDS,
        }
    ),
    "pev_agent": frozenset(
        {
            Permission.IMMUNIZATION_ADMINISTER,
            Permission.IMMUNIZATION_READ,
            Permission.PATIENT_JOURNEY,
            Permission.CLINIC_OPERATIONS,
            Permission.RECEPTION_INTAKE,
        }
    ),
    "patient": frozenset(
        {
            Permission.PATIENT_JOURNEY,
        }
    ),
    "admin": frozenset(
        {
            Permission.ADMIN_CLINIC,
            Permission.ADMIN_STAFF,
            Permission.ADMIN_AUDIT,
            Permission.ADMIN_BACKUP,
            Permission.BILLING_REVENUE,
            Permission.BILLING_READ,
            Permission.BILLING_PAY,
            Permission.BILLING_OVERRIDE,
            Permission.BILLING_FREE_TEXT,
            Permission.CLINIC_OPERATIONS,
            Permission.ADMISSION_MANAGE,
            Permission.ADMISSION_BEDS,
            Permission.NUTRITION_ASSESS,
            Permission.NUTRITION_READ,
            Permission.IMMUNIZATION_ADMINISTER,
            Permission.IMMUNIZATION_READ,
        }
    ),
    "clinic_admin": frozenset(
        {
            Permission.ADMIN_CLINIC,
            Permission.ADMIN_STAFF,
            Permission.ADMIN_AUDIT,
            Permission.ADMIN_BACKUP,
            Permission.BILLING_REVENUE,
            Permission.BILLING_READ,
            Permission.BILLING_PAY,
            Permission.BILLING_OVERRIDE,
            Permission.BILLING_FREE_TEXT,
            Permission.CLINIC_OPERATIONS,
            Permission.ADMISSION_MANAGE,
            Permission.ADMISSION_BEDS,
            Permission.NUTRITION_ASSESS,
            Permission.NUTRITION_READ,
            Permission.IMMUNIZATION_ADMINISTER,
            Permission.IMMUNIZATION_READ,
        }
    ),
    "platform_owner": frozenset(
        {
            Permission.ADMIN_CLINIC,
            Permission.ADMIN_STAFF,
            Permission.ADMIN_AUDIT,
            Permission.ADMIN_BACKUP,
            Permission.BILLING_REVENUE,
            Permission.BILLING_OVERRIDE,
            Permission.BILLING_FREE_TEXT,
            Permission.CLINIC_OPERATIONS,
            Permission.ADMISSION_MANAGE,
            Permission.ADMISSION_BEDS,
            Permission.PLATFORM_SYSTEM,
            Permission.PLATFORM_SETTINGS,
            Permission.PLATFORM_SUBSCRIPTIONS,
            Permission.RECEPTION_QUEUE,
            Permission.RECEPTION_INTAKE,
            Permission.RECEPTION_APPOINTMENTS,
            Permission.DOCTOR_QUEUE,
            Permission.DOCTOR_CONSULTATION,
            Permission.LAB_ORDERS,
            Permission.PHARMACY_ORDERS,
            Permission.BILLING_READ,
            Permission.BILLING_PAY,
            Permission.PATIENT_JOURNEY,
        }
    ),
    "platform_admin": frozenset(
        {
            Permission.ADMIN_CLINIC,
            Permission.ADMIN_STAFF,
            Permission.ADMIN_AUDIT,
            Permission.ADMIN_BACKUP,
            Permission.BILLING_REVENUE,
            Permission.BILLING_OVERRIDE,
            Permission.BILLING_FREE_TEXT,
            Permission.CLINIC_OPERATIONS,
            Permission.ADMISSION_MANAGE,
            Permission.ADMISSION_BEDS,
        }
    ),
}

RECEPTION_ROLES = ("receptionist",)
CASHIER_ROLES = ("cashier",)
DOCTOR_ROLES = ("doctor",)
LAB_ROLES = ("lab_technician",)
PHARMACY_ROLES = ("pharmacist",)
NUTRITION_ROLES = ("nutritionist",)
MIDWIFE_ROLES = ("midwife",)
CLINIC_ADMIN_ROLES = ("clinic_admin", "admin")
PLATFORM_OWNER_ROLES = ("platform_owner",)
PLATFORM_ADMIN_ROLES = ("platform_admin",)
PLATFORM_SCOPE_ROLES = ("platform_owner", "platform_admin")
CLINIC_ADMIN_ROLES = ("clinic_admin", "admin")
ADMIN_ROLES = CLINIC_ADMIN_ROLES
CLINIC_OPS_ROLES = (
    "platform_owner",
    "platform_admin",
    "clinic_admin",
    "admin",
    "receptionist",
    "cashier",
    "doctor",
    "lab_technician",
    "pharmacist",
    "nutritionist",
    "midwife",
    "nurse",
    "pev_agent",
)

BILLING_READ_ROLES = ("receptionist", "cashier", "clinic_admin", "admin", "platform_admin", "platform_owner")
BILLING_PAY_ROLES = ("receptionist", "cashier")
BILLING_REVENUE_ROLES = ("clinic_admin", "admin", "platform_admin", "platform_owner", "receptionist", "cashier")
# Negotiated catalog prices and free-text (non-catalog) charges — never receptionist/cashier.
BILLING_OVERRIDE_ROLES = ("clinic_admin", "admin", "platform_admin", "platform_owner")
BILLING_FREE_TEXT_ROLES = BILLING_OVERRIDE_ROLES
LAB_QUEUE_ROLES = LAB_ROLES + CLINIC_ADMIN_ROLES
PHARMACY_QUEUE_ROLES = PHARMACY_ROLES + CLINIC_ADMIN_ROLES


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(effective_role(role), frozenset())


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
