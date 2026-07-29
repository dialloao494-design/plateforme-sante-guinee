"""Business logic for server-side patient dossier (MVP)."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import models
import schemas.patient as patient_schemas
import schemas.patient_record as record_schemas
from models.user import User
from services.clinical_audit_service import ClinicalAuditService
from services.patient_record_access import PatientRecordAccessPolicy
from services.secure_attachment_storage import SecureAttachmentStorage


def _patient_to_response(patient: models.Patient, db: Session) -> patient_schemas.PatientResponse:
    user = db.query(User).filter(User.id == patient.user_id).first()
    email = user.email if user else None
    return patient_schemas.PatientResponse(
        id=patient.id,
        user_id=patient.user_id,
        first_name=patient.first_name or "",
        last_name=patient.last_name or "",
        age=patient.age or 0,
        gender=patient.gender or "unknown",
        date_of_birth=patient.date_of_birth,
        phone=patient.phone,
        email=email,
        address=patient.address,
        emergency_contact=patient.emergency_contact,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


def _assert_appointment_belongs_to_patient(
    db: Session, appointment_id: int, patient_id: int
) -> models.RendezVous:
    appointment = (
        db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    )
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if appointment.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment does not belong to this patient",
        )
    return appointment


class PatientRecordService:
    @staticmethod
    def get_patient_detail(
        db: Session,
        patient_id: int,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> patient_schemas.PatientResponse:
        patient = PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="read",
            resource_type="patient",
            resource_id=patient_id,
            client_ip=client_ip,
        )
        return _patient_to_response(patient, db)

    @staticmethod
    def list_notes(
        db: Session,
        patient_id: int,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> list[record_schemas.ClinicalNoteResponse]:
        PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
        notes = (
            db.query(models.ClinicalNote)
            .filter(models.ClinicalNote.patient_id == patient_id)
            .order_by(models.ClinicalNote.created_at.desc())
            .all()
        )
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="read",
            resource_type="clinical_notes",
            client_ip=client_ip,
        )
        return notes

    @staticmethod
    def create_note(
        db: Session,
        patient_id: int,
        payload: record_schemas.ClinicalNoteCreate,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> record_schemas.ClinicalNoteResponse:
        patient, doctor = PatientRecordAccessPolicy.assert_can_write_clinical(
            db, current_user, patient_id
        )
        if payload.appointment_id is not None:
            _assert_appointment_belongs_to_patient(db, payload.appointment_id, patient.id)

        note = models.ClinicalNote(
            patient_id=patient.id,
            doctor_id=doctor.id if doctor else None,
            appointment_id=payload.appointment_id,
            note_type=payload.note_type,
            contenu=payload.contenu,
        )
        db.add(note)
        db.commit()
        db.refresh(note)

        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="create",
            resource_type="clinical_note",
            resource_id=note.id,
            client_ip=client_ip,
        )
        return note

    @staticmethod
    def list_summaries(
        db: Session,
        patient_id: int,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> list[record_schemas.ConsultationSummaryResponse]:
        PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
        summaries = (
            db.query(models.ConsultationSummary)
            .filter(models.ConsultationSummary.patient_id == patient_id)
            .order_by(models.ConsultationSummary.created_at.desc())
            .all()
        )
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="read",
            resource_type="consultation_summaries",
            client_ip=client_ip,
        )
        return summaries

    @staticmethod
    def create_summary(
        db: Session,
        patient_id: int,
        payload: record_schemas.ConsultationSummaryCreate,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> record_schemas.ConsultationSummaryResponse:
        if not payload.has_content():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of diagnostic, traitement, or recommandations is required",
            )

        patient, doctor = PatientRecordAccessPolicy.assert_can_write_clinical(
            db, current_user, patient_id
        )
        if payload.appointment_id is not None:
            _assert_appointment_belongs_to_patient(db, payload.appointment_id, patient.id)

        summary = models.ConsultationSummary(
            patient_id=patient.id,
            doctor_id=doctor.id if doctor else None,
            appointment_id=payload.appointment_id,
            diagnostic=payload.diagnostic,
            traitement=payload.traitement,
            recommandations=payload.recommandations,
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)

        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="create",
            resource_type="consultation_summary",
            resource_id=summary.id,
            client_ip=client_ip,
        )
        return summary

    @staticmethod
    def list_documents(
        db: Session,
        patient_id: int,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> list[record_schemas.PatientDocumentResponse]:
        PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
        docs = (
            db.query(models.PatientDocument)
            .filter(models.PatientDocument.patient_id == patient_id)
            .order_by(models.PatientDocument.created_at.desc())
            .all()
        )
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="read",
            resource_type="patient_documents",
            client_ip=client_ip,
        )
        return [
            record_schemas.PatientDocumentResponse(
                id=doc.id,
                patient_id=doc.patient_id,
                uploaded_by=doc.uploaded_by,
                type_document=doc.type_document,
                original_filename=getattr(doc, "original_filename", None),
                mime_type=getattr(doc, "mime_type", None),
                created_at=doc.created_at,
                download_url=f"/patients/{patient_id}/documents/{doc.id}/download",
            )
            for doc in docs
        ]

    @staticmethod
    async def upload_document(
        db: Session,
        patient_id: int,
        *,
        type_document: str,
        file: UploadFile,
        current_user: User,
        client_ip: Optional[str] = None,
    ) -> record_schemas.PatientDocumentResponse:
        patient, _doctor = PatientRecordAccessPolicy.assert_can_write_clinical(
            db, current_user, patient_id
        )

        filename = file.filename or "document"
        ext = os.path.splitext(filename)[1].lower()
        if not ext or ext not in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must have a supported extension (.pdf, .png, .jpg, .jpeg, .webp)",
            )

        content = await file.read()
        stored = SecureAttachmentStorage.store(
            content, original_filename=filename, extension=ext
        )

        doc = models.PatientDocument(
            patient_id=patient.id,
            uploaded_by=current_user.id,
            type_document=type_document.strip() or "autre",
            file_path=stored.storage_key,
            original_filename=stored.original_filename,
            mime_type=stored.mime_type,
            content_sha256=stored.content_sha256,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="create",
            resource_type="patient_document",
            resource_id=doc.id,
            client_ip=client_ip,
        )
        return record_schemas.PatientDocumentResponse(
            id=doc.id,
            patient_id=doc.patient_id,
            uploaded_by=doc.uploaded_by,
            type_document=doc.type_document,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            created_at=doc.created_at,
            download_url=f"/patients/{patient_id}/documents/{doc.id}/download",
        )

    @staticmethod
    def download_document(
        db: Session,
        patient_id: int,
        document_id: int,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> tuple[bytes, str, str, str | None]:
        PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
        doc = (
            db.query(models.PatientDocument)
            .filter(
                models.PatientDocument.id == document_id,
                models.PatientDocument.patient_id == patient_id,
            )
            .first()
        )
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        content, _path = SecureAttachmentStorage.read(
            doc.file_path,
            expected_sha256=getattr(doc, "content_sha256", None),
        )
        mime = (
            getattr(doc, "mime_type", None)
            or SecureAttachmentStorage.sniff_mime(content, "")
        )
        original = getattr(doc, "original_filename", None)
        if original:
            filename = original
        else:
            ext = {
                "application/pdf": "pdf",
                "image/png": "png",
                "image/jpeg": "jpg",
                "image/webp": "webp",
                "text/plain": "txt",
            }.get(mime, "bin")
            filename = f"{doc.type_document}_{doc.id}.{ext}"

        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="download",
            resource_type="patient_document",
            resource_id=doc.id,
            client_ip=client_ip,
        )
        return content, mime, filename, getattr(doc, "content_sha256", None)

    @staticmethod
    def build_timeline(
        db: Session,
        patient_id: int,
        current_user: User,
        *,
        client_ip: Optional[str] = None,
    ) -> list[record_schemas.TimelineEvent]:
        patient = PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
        clinic_id = PatientRecordAccessPolicy.dossier_clinic_id(db, current_user, patient)

        events: list[record_schemas.TimelineEvent] = []

        for note in (
            db.query(models.ClinicalNote)
            .filter(models.ClinicalNote.patient_id == patient_id)
            .all()
        ):
            events.append(
                record_schemas.TimelineEvent(
                    event_type="clinical_note",
                    resource_id=note.id,
                    timestamp=note.created_at,
                    summary=f"Note ({note.note_type})",
                    payload={
                        "note_type": note.note_type,
                        "contenu": note.contenu,
                        "doctor_id": note.doctor_id,
                        "appointment_id": note.appointment_id,
                    },
                )
            )

        for summary in (
            db.query(models.ConsultationSummary)
            .filter(models.ConsultationSummary.patient_id == patient_id)
            .all()
        ):
            text_parts = [
                p
                for p in [summary.diagnostic, summary.traitement, summary.recommandations]
                if p
            ]
            events.append(
                record_schemas.TimelineEvent(
                    event_type="consultation_summary",
                    resource_id=summary.id,
                    timestamp=summary.created_at,
                    summary="Synthèse de consultation",
                    payload={
                        "diagnostic": summary.diagnostic,
                        "traitement": summary.traitement,
                        "recommandations": summary.recommandations,
                        "doctor_id": summary.doctor_id,
                        "appointment_id": summary.appointment_id,
                    },
                )
            )

        for doc in (
            db.query(models.PatientDocument)
            .filter(models.PatientDocument.patient_id == patient_id)
            .all()
        ):
            events.append(
                record_schemas.TimelineEvent(
                    event_type="patient_document",
                    resource_id=doc.id,
                    timestamp=doc.created_at,
                    summary=f"Document ({doc.type_document})",
                    payload={
                        "type_document": doc.type_document,
                        "uploaded_by": doc.uploaded_by,
                        "download_url": f"/patients/{patient_id}/documents/{doc.id}/download",
                    },
                )
            )

        for rdv in (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.patient_id == patient_id,
                models.RendezVous.clinic_id == clinic_id,
            )
            .all()
        ):
            ts = rdv.date if isinstance(rdv.date, datetime) else datetime.utcnow()
            events.append(
                record_schemas.TimelineEvent(
                    event_type="appointment",
                    resource_id=rdv.id,
                    timestamp=ts,
                    summary=f"Rendez-vous ({rdv.status})",
                    payload={
                        "status": rdv.status,
                        "clinical_status": rdv.clinical_status,
                        "consultation_type": rdv.consultation_type,
                        "doctor_id": rdv.doctor_id,
                        "clinic_id": rdv.clinic_id,
                        "payment_status": rdv.payment_status,
                    },
                )
            )

        for consultation in (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.patient_id == patient_id,
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .all()
        ):
            ts = consultation.started_at or consultation.updated_at or datetime.utcnow()
            events.append(
                record_schemas.TimelineEvent(
                    event_type="cis_consultation",
                    resource_id=consultation.id,
                    timestamp=ts,
                    summary=f"Consultation CIS ({consultation.status})",
                    payload={
                        "status": consultation.status,
                        "chief_complaint": consultation.chief_complaint,
                        "diagnosis": consultation.diagnosis,
                        "treatment_plan": consultation.treatment_plan,
                        "doctor_id": consultation.doctor_id,
                        "clinic_id": consultation.clinic_id,
                        "appointment_id": consultation.appointment_id,
                    },
                )
            )

        for lab_order in (
            db.query(models.LabOrder)
            .filter(
                models.LabOrder.patient_id == patient_id,
                models.LabOrder.deleted_at.is_(None),
            )
            .all()
        ):
            ts = lab_order.created_at or datetime.utcnow()
            events.append(
                record_schemas.TimelineEvent(
                    event_type="lab_order",
                    resource_id=lab_order.id,
                    timestamp=ts,
                    summary=f"Examen labo — {lab_order.test_name} ({lab_order.status})",
                    payload={
                        "test_code": lab_order.test_code,
                        "test_name": lab_order.test_name,
                        "status": lab_order.status,
                        "priority": lab_order.priority,
                        "consultation_id": lab_order.consultation_id,
                    },
                )
            )
            for result in lab_order.results or []:
                rts = result.validated_at or result.updated_at or result.created_at or ts
                events.append(
                    record_schemas.TimelineEvent(
                        event_type="lab_result",
                        resource_id=result.id,
                        timestamp=rts,
                        summary=f"Résultat labo — {lab_order.test_name} ({result.status})",
                        payload={
                            "lab_order_id": lab_order.id,
                            "result_summary": result.result_summary,
                            "reference_range": result.reference_range,
                            "interpretation": result.interpretation,
                            "status": result.status,
                        },
                    )
                )

        for rx in (
            db.query(models.Prescription)
            .filter(
                models.Prescription.patient_id == patient_id,
                models.Prescription.deleted_at.is_(None),
            )
            .all()
        ):
            ts = rx.created_at or datetime.utcnow()
            meds = ", ".join(i.medication_name for i in (rx.items or []))
            events.append(
                record_schemas.TimelineEvent(
                    event_type="prescription",
                    resource_id=rx.id,
                    timestamp=ts,
                    summary=f"Ordonnance ({rx.status})",
                    payload={
                        "status": rx.status,
                        "medications": meds,
                        "consultation_id": rx.consultation_id,
                        "items": [
                            {
                                "medication_name": i.medication_name,
                                "dosage": i.dosage,
                                "frequency": i.frequency,
                                "duration_days": i.duration_days,
                            }
                            for i in (rx.items or [])
                        ],
                    },
                )
            )

        for ph_order in (
            db.query(models.PharmacyOrder)
            .filter(models.PharmacyOrder.patient_id == patient_id)
            .all()
        ):
            ts = ph_order.dispensed_at or ph_order.created_at or datetime.utcnow()
            events.append(
                record_schemas.TimelineEvent(
                    event_type="pharmacy_order",
                    resource_id=ph_order.id,
                    timestamp=ts,
                    summary=f"Pharmacie ({ph_order.status})",
                    payload={
                        "status": ph_order.status,
                        "prescription_id": ph_order.prescription_id,
                        "dispensed_at": ph_order.dispensed_at.isoformat() if ph_order.dispensed_at else None,
                    },
                )
            )

        for charge in (
            db.query(models.ClinicCharge)
            .filter(models.ClinicCharge.patient_id == patient_id)
            .all()
        ):
            ts = charge.paid_at or charge.created_at or datetime.utcnow()
            events.append(
                record_schemas.TimelineEvent(
                    event_type="billing_charge",
                    resource_id=charge.id,
                    timestamp=ts,
                    summary=f"Facturation {charge.charge_type} ({charge.payment_status})",
                    payload={
                        "charge_type": charge.charge_type,
                        "amount_gnf": charge.amount_gnf,
                        "payment_status": charge.payment_status,
                        "payment_method": charge.payment_method,
                        "description": charge.description,
                    },
                )
            )

        events.sort(key=lambda e: e.timestamp, reverse=True)

        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="read",
            resource_type="timeline",
            client_ip=client_ip,
        )
        return events
