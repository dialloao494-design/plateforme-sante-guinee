"""Audit hooks for clinical information system actions."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models.user import User
from services.clinical_audit_service import ClinicalAuditService


def log_cis(
    db: Session,
    *,
    actor: User,
    clinic_id: int,
    action: str,
    resource_type: str,
    patient_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    client_ip: Optional[str] = None,
) -> None:
    ClinicalAuditService.log(
        db,
        actor=actor,
        patient_id=patient_id,
        clinic_id=clinic_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        client_ip=client_ip,
    )


def log_cis_denied(
    db: Session,
    *,
    actor: User,
    action: str,
    resource_type: str,
    clinic_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    client_ip: Optional[str] = None,
) -> None:
    ClinicalAuditService.log_denied(
        db,
        actor=actor,
        action=action,
        resource_type=resource_type,
        clinic_id=clinic_id,
        patient_id=patient_id,
        resource_id=resource_id,
        client_ip=client_ip,
    )
