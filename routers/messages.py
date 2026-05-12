import os
import re
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import models
from database import get_db
from schemas import message as message_schemas
from security import get_current_user

router = APIRouter(prefix="/messages", tags=["Messages"])

UPLOAD_ROOT = Path("uploads/messages")
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def _sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return cleaned[:120] or "attachment"


def _get_patient_for_user(db: Session, user_id: int):
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def _get_doctor_for_user(db: Session, user_id: int):
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def _assert_can_access_appointment(db: Session, appointment: models.RendezVous, current_user) -> None:
    if current_user.role == "admin":
        return

    if current_user.role == "patient":
        patient = _get_patient_for_user(db, current_user.id)
        if not patient or appointment.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    if current_user.role == "doctor":
        doctor = _get_doctor_for_user(db, current_user.id)
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("/{appointment_id}", response_model=List[message_schemas.MessageResponse])
def list_messages(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, appointment, current_user)

    messages = (
        db.query(models.Message)
        .filter(models.Message.appointment_id == appointment_id)
        .order_by(models.Message.created_at.asc(), models.Message.id.asc())
        .all()
    )

    return messages


@router.post("/{appointment_id}", response_model=message_schemas.MessageResponse)
async def send_message(
    appointment_id: int,
    content: str = Form(default=""),
    attachment: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, appointment, current_user)

    clean_content = (content or "").strip()
    if not clean_content and attachment is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content or attachment is required")

    attachment_name = None
    attachment_url = None

    if attachment is not None:
        extension = Path(attachment.filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported attachment format")

        appointment_folder = UPLOAD_ROOT / f"appointment_{appointment_id}"
        appointment_folder.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_filename(attachment.filename or f"file{extension}")
        unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
        absolute_path = appointment_folder / unique_name

        with absolute_path.open("wb") as out_file:
            file_bytes = await attachment.read()
            out_file.write(file_bytes)

        attachment_name = safe_name
        attachment_url = f"/uploads/messages/appointment_{appointment_id}/{unique_name}"

    message = models.Message(
        appointment_id=appointment_id,
        sender_user_id=current_user.id,
        content=clean_content or None,
        attachment_name=attachment_name,
        attachment_url=attachment_url,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message
