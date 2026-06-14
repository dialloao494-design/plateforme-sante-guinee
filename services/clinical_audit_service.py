"""Centralized audit logging for patient dossier and CIS clinical actions."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models.clinical_audit_log import ClinicalAuditLog
from models.user import User

logger = logging.getLogger(__name__)


class ClinicalAuditService:
    @staticmethod
    def log(
        db: Session,
        *,
        actor: User,
        patient_id: int | None,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        client_ip: Optional[str] = None,
        clinic_id: Optional[int] = None,
    ) -> ClinicalAuditLog:
        entry = ClinicalAuditLog(
            actor_id=actor.id,
            actor_role=actor.role,
            patient_id=patient_id,
            clinic_id=clinic_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip=client_ip,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(
            "Clinical audit clinic_id=%s patient_id=%s actor_id=%s role=%s action=%s resource=%s:%s",
            clinic_id,
            patient_id,
            actor.id,
            actor.role,
            action,
            resource_type,
            resource_id,
        )
        return entry

    @staticmethod
    def log_denied(
        db: Session,
        *,
        actor: User,
        action: str,
        resource_type: str,
        client_ip: Optional[str] = None,
        patient_id: Optional[int] = None,
        clinic_id: Optional[int] = None,
        resource_id: Optional[int] = None,
    ) -> ClinicalAuditLog:
        return ClinicalAuditService.log(
            db,
            actor=actor,
            patient_id=patient_id,
            action=f"denied_{action}",
            resource_type=resource_type,
            resource_id=resource_id,
            client_ip=client_ip,
            clinic_id=clinic_id,
        )

    @staticmethod
    def list_for_clinic(
        db: Session,
        *,
        clinic_id: int,
        patient_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[ClinicalAuditLog]:
        q = db.query(ClinicalAuditLog).filter(ClinicalAuditLog.clinic_id == clinic_id)
        if patient_id is not None:
            q = q.filter(ClinicalAuditLog.patient_id == patient_id)
        return q.order_by(ClinicalAuditLog.timestamp.desc()).limit(limit).all()
