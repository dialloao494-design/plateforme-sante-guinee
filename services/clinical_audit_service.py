"""Centralized audit logging for patient dossier and CIS clinical actions."""

from __future__ import annotations

import logging
import json
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
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
        commit: bool = True,
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
            user_agent=(user_agent or "")[:512] or None,
            reason=(reason or "").strip()[:500] or None,
            before_json=json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
            after_json=json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
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
        actor_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[ClinicalAuditLog]:
        q = db.query(ClinicalAuditLog).filter(ClinicalAuditLog.clinic_id == clinic_id)
        if patient_id is not None:
            q = q.filter(ClinicalAuditLog.patient_id == patient_id)
        if actor_id is not None:
            q = q.filter(ClinicalAuditLog.actor_id == actor_id)
        if action:
            q = q.filter(ClinicalAuditLog.action == action)
        if resource_type:
            q = q.filter(ClinicalAuditLog.resource_type == resource_type)
        if date_from:
            q = q.filter(ClinicalAuditLog.timestamp >= date_from)
        if date_to:
            q = q.filter(ClinicalAuditLog.timestamp <= date_to)
        return q.order_by(ClinicalAuditLog.timestamp.desc()).limit(limit).all()
