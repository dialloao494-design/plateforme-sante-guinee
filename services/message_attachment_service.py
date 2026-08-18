"""
Authorized access to clinical message attachments — RBAC + appointment scope.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from models.attachment_access_log import AttachmentAccessLog
from models.user import User
from core.roles import effective_role, user_has_any_role
from services.secure_attachment_storage import SecureAttachmentStorage
from services.clinical_audit_service import ClinicalAuditService

logger = logging.getLogger(__name__)


def _get_patient_for_user(db: Session, user_id: int) -> Optional[models.Patient]:
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def _get_doctor_for_user(db: Session, user_id: int) -> Optional[models.Doctor]:
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def assert_appointment_access(db: Session, appointment: models.RendezVous, current_user: User) -> None:
    role = effective_role(current_user.role)

    if user_has_any_role(role, ["platform_admin", "platform_owner"]):
        return

    if role in ("clinic_admin", "admin"):
        cid = getattr(current_user, "clinic_id", None)
        if cid is None or appointment.clinic_id != cid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    if role == "patient":
        patient = _get_patient_for_user(db, current_user.id)
        if not patient or appointment.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    if role == "doctor":
        doctor = _get_doctor_for_user(db, current_user.id)
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


class MessageAttachmentService:
    @staticmethod
    def get_message_for_download(
        db: Session,
        message_id: int,
        current_user: User,
        *,
        client_ip: str | None = None,
    ) -> tuple[models.Message, bytes, str]:
        message = db.query(models.Message).filter(models.Message.id == message_id).first()
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

        if not message.attachment_storage_key and not message.attachment_url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message has no attachment")

        appointment = (
            db.query(models.RendezVous).filter(models.RendezVous.id == message.appointment_id).first()
        )
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        try:
            assert_appointment_access(db, appointment, current_user)
        except HTTPException:
            ClinicalAuditService.log_denied(
                db,
                actor=current_user,
                action="download",
                resource_type="message_attachment",
                resource_id=message.id,
                patient_id=appointment.patient_id,
                clinic_id=appointment.clinic_id,
                client_ip=client_ip,
            )
            raise

        if message.attachment_storage_key:
            content, _path = SecureAttachmentStorage.read(message.attachment_storage_key)
            mime = message.attachment_mime_type or "application/octet-stream"
            storage_kind = "secure"
        else:
            content, _path = SecureAttachmentStorage.read_legacy(message.attachment_url or "")
            mime = message.attachment_mime_type or SecureAttachmentStorage.sniff_mime(
                content, _path.suffix
            )
            storage_kind = "legacy"

        db.add(
            AttachmentAccessLog(
                message_id=message.id,
                appointment_id=message.appointment_id,
                user_id=current_user.id,
                user_role=current_user.role,
                client_ip=client_ip,
                storage_kind=storage_kind,
            )
        )
        db.commit()

        logger.info(
            "Attachment download message_id=%s user_id=%s role=%s appointment_id=%s storage=%s",
            message.id,
            current_user.id,
            current_user.role,
            message.appointment_id,
            storage_kind,
        )
        return message, content, mime

    @staticmethod
    def download_path(message_id: int) -> str:
        return f"/messages/attachments/{message_id}/download"

    @staticmethod
    def has_attachment(message: models.Message) -> bool:
        return bool(message.attachment_storage_key or message.attachment_url)
