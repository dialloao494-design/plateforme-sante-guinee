"""Centralized audit logging for patient dossier access."""

from __future__ import annotations

import logging
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
        patient_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        client_ip: Optional[str] = None,
    ) -> ClinicalAuditLog:
        entry = ClinicalAuditLog(
            actor_id=actor.id,
            actor_role=actor.role,
            patient_id=patient_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip=client_ip,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(
            "Clinical audit patient_id=%s actor_id=%s role=%s action=%s resource=%s:%s",
            patient_id,
            actor.id,
            actor.role,
            action,
            resource_type,
            resource_id,
        )
        return entry
