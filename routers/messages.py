from pathlib import Path
from typing import List
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

import models
from core.limiter import limiter
from database import get_db
from schemas import message as message_schemas
from security import get_current_user
from core.attachment_policy import phi_download_headers
from services.message_attachment_service import MessageAttachmentService, assert_appointment_access
from services.secure_attachment_storage import SecureAttachmentStorage

router = APIRouter(prefix="/messages", tags=["Messages"])


def _serialize_message(message: models.Message) -> message_schemas.MessageResponse:
    has_attachment = MessageAttachmentService.has_attachment(message)
    return message_schemas.MessageResponse(
        id=message.id,
        appointment_id=message.appointment_id,
        sender_user_id=message.sender_user_id,
        sender_role=message.sender_role,
        content=message.content,
        attachment_name=message.attachment_name if has_attachment else None,
        has_attachment=has_attachment,
        attachment_download_url=(
            MessageAttachmentService.download_path(message.id) if has_attachment else None
        ),
        attachment_mime_type=message.attachment_mime_type if has_attachment else None,
        attachment_size_bytes=message.attachment_size_bytes if has_attachment else None,
        created_at=message.created_at,
    )


@router.get("/attachments/{message_id}/download")
@limiter.limit(os.getenv("RATE_LIMIT_ATTACHMENT_DOWNLOAD", "30/minute"))
def download_message_attachment(
    request: Request,
    message_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client_ip = request.client.host if request.client else None
    message, content, mime = MessageAttachmentService.get_message_for_download(
        db, message_id, current_user, client_ip=client_ip
    )
    filename = SecureAttachmentStorage.sanitize_filename(message.attachment_name or "attachment")
    return Response(
        content=content,
        media_type=mime,
        headers=phi_download_headers(
            filename=filename,
            content_sha256=message.attachment_content_sha256,
        ),
    )


@router.get("/{appointment_id}", response_model=List[message_schemas.MessageResponse])
def list_messages(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    assert_appointment_access(db, appointment, current_user)

    messages = (
        db.query(models.Message)
        .filter(models.Message.appointment_id == appointment_id)
        .order_by(models.Message.created_at.asc(), models.Message.id.asc())
        .all()
    )

    return [_serialize_message(message) for message in messages]


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

    assert_appointment_access(db, appointment, current_user)

    clean_content = (content or "").strip()
    if not clean_content and attachment is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content or attachment is required")

    attachment_name = None
    attachment_storage_key = None
    attachment_mime_type = None
    attachment_size_bytes = None
    attachment_content_sha256 = None

    if attachment is not None:
        extension = Path(attachment.filename or "").suffix.lower()
        file_bytes = await attachment.read()
        stored = SecureAttachmentStorage.store(
            file_bytes,
            original_filename=attachment.filename or f"file{extension}",
            extension=extension,
        )
        attachment_name = stored.original_filename
        attachment_storage_key = stored.storage_key
        attachment_mime_type = stored.mime_type
        attachment_size_bytes = stored.size_bytes
        attachment_content_sha256 = stored.content_sha256

    message = models.Message(
        appointment_id=appointment_id,
        sender_user_id=current_user.id,
        content=clean_content or None,
        attachment_name=attachment_name,
        attachment_storage_key=attachment_storage_key,
        attachment_mime_type=attachment_mime_type,
        attachment_size_bytes=attachment_size_bytes,
        attachment_content_sha256=attachment_content_sha256,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return _serialize_message(message)
