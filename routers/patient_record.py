"""Server-side patient dossier API (MVP — auditable clinical records)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

import schemas.patient_record as record_schemas
from core.attachment_policy import phi_download_headers
from core.http_utils import client_ip
from database import get_db
from models.user import User
from security import get_current_user, require_roles
from services.patient_record_service import PatientRecordService

router = APIRouter(prefix="/patients", tags=["Patient Dossier"])

DOSSIER_READ_ROLES = ["admin", "doctor", "patient", "receptionist", "lab_technician", "pharmacist"]
DOSSIER_WRITE_ROLES = ["admin", "doctor", "lab_technician", "pharmacist", "receptionist"]


@router.get("/{patient_id}/notes", response_model=List[record_schemas.ClinicalNoteResponse])
def list_clinical_notes(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(DOSSIER_READ_ROLES)),
):
    return PatientRecordService.list_notes(
        db, patient_id, current_user, client_ip=client_ip(request)
    )


@router.post(
    "/{patient_id}/notes",
    response_model=record_schemas.ClinicalNoteResponse,
    status_code=201,
)
def create_clinical_note(
    patient_id: int,
    payload: record_schemas.ClinicalNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "doctor"])),
):
    return PatientRecordService.create_note(
        db, patient_id, payload, current_user, client_ip=client_ip(request)
    )


@router.get("/{patient_id}/summaries", response_model=List[record_schemas.ConsultationSummaryResponse])
def list_consultation_summaries(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(DOSSIER_READ_ROLES)),
):
    return PatientRecordService.list_summaries(
        db, patient_id, current_user, client_ip=client_ip(request)
    )


@router.post(
    "/{patient_id}/summaries",
    response_model=record_schemas.ConsultationSummaryResponse,
    status_code=201,
)
def create_consultation_summary(
    patient_id: int,
    payload: record_schemas.ConsultationSummaryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "doctor"])),
):
    return PatientRecordService.create_summary(
        db, patient_id, payload, current_user, client_ip=client_ip(request)
    )


@router.get("/{patient_id}/documents", response_model=List[record_schemas.PatientDocumentResponse])
def list_patient_documents(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(DOSSIER_READ_ROLES)),
):
    return PatientRecordService.list_documents(
        db, patient_id, current_user, client_ip=client_ip(request)
    )


@router.post(
    "/{patient_id}/documents",
    response_model=record_schemas.PatientDocumentResponse,
    status_code=201,
)
async def upload_patient_document(
    patient_id: int,
    request: Request,
    type_document: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(DOSSIER_WRITE_ROLES)),
):
    return await PatientRecordService.upload_document(
        db,
        patient_id,
        type_document=type_document,
        file=file,
        current_user=current_user,
        client_ip=client_ip(request),
    )


@router.get("/{patient_id}/documents/{document_id}/download")
def download_patient_document(
    patient_id: int,
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(DOSSIER_READ_ROLES)),
):
    content, mime, filename, content_sha256 = PatientRecordService.download_document(
        db, patient_id, document_id, current_user, client_ip=client_ip(request)
    )
    return Response(
        content=content,
        media_type=mime,
        headers=phi_download_headers(filename=filename, content_sha256=content_sha256),
    )


@router.get("/{patient_id}/timeline", response_model=List[record_schemas.TimelineEvent])
def get_patient_timeline(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(DOSSIER_READ_ROLES)),
):
    return PatientRecordService.build_timeline(
        db, patient_id, current_user, client_ip=client_ip(request)
    )
