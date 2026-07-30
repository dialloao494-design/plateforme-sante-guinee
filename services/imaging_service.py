"""Radiology / imaging workflow."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from models.user import User
from services.cis_audit import log_cis
from services.unified_billing_service import UnifiedBillingService, DEFAULT_RADIOLOGY_FEE_GNF
from services.visit_service import VisitService


class ImagingService:
    # Catalogue modalities. Doctors may also request "other" imaging with a
    # free-text label, so we accept any non-empty modality up to the column
    # length (String(32)) rather than a fixed whitelist.
    VALID_MODALITIES = (
        "xray",
        "ultrasound",
        "ct_scan",
        "mri",
        "mammography",
        "dental_panoramic",
    )

    @staticmethod
    def create_order(
        db: Session,
        *,
        clinic_id: int,
        consultation_id: int,
        modality: str,
        body_part: str | None,
        clinical_indication: str | None,
        priority: str,
        actor: User,
        client_ip: str | None = None,
    ) -> models.ImagingOrder:
        modality = (modality or "").strip()
        if not modality or len(modality) > 32:
            raise HTTPException(status_code=400, detail=f"Invalid modality: {modality}")
        consultation = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.id == consultation_id,
                models.ClinicalConsultation.clinic_id == clinic_id,
            )
            .first()
        )
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        order = models.ImagingOrder(
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            consultation_id=consultation_id,
            modality=modality,
            body_part=body_part,
            clinical_indication=clinical_indication,
            priority=priority,
            ordered_by_user_id=actor.id,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        visit = VisitService.ensure_for_consultation(db, consultation)
        UnifiedBillingService._ensure_charge(
            db,
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            visit_id=visit.id,
            charge_type="radiology",
            source_type="imaging_order",
            source_id=order.id,
            description=f"Imagerie {modality} — {body_part or 'examen'}",
            amount_gnf=DEFAULT_RADIOLOGY_FEE_GNF,
        )
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            action="create",
            resource_type="imaging_order",
            resource_id=order.id,
            client_ip=client_ip,
        )
        return order

    @staticmethod
    def list_queue(db: Session, *, clinic_id: int, status: str | None = None) -> list[models.ImagingOrder]:
        q = db.query(models.ImagingOrder).filter(models.ImagingOrder.clinic_id == clinic_id)
        if status:
            q = q.filter(models.ImagingOrder.status == status)
        else:
            q = q.filter(models.ImagingOrder.status.notin_(["validated", "cancelled"]))
        return q.order_by(models.ImagingOrder.created_at.asc()).all()

    @staticmethod
    def update_status(
        db: Session, *, clinic_id: int, order_id: int, status: str, scheduled_at: datetime | None = None
    ) -> models.ImagingOrder:
        order = ImagingService._get_order(db, clinic_id, order_id)
        order.status = status
        if scheduled_at:
            order.scheduled_at = scheduled_at
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def submit_report(
        db: Session,
        *,
        clinic_id: int,
        order_id: int,
        findings: str,
        impression: str,
        recommendations: str | None,
        actor: User,
        client_ip: str | None = None,
    ) -> models.ImagingResult:
        order = ImagingService._get_order(db, clinic_id, order_id)
        result = models.ImagingResult(
            order_id=order.id,
            findings=findings,
            impression=impression,
            recommendations=recommendations,
            reported_by_user_id=actor.id,
            reported_at=datetime.utcnow(),
            status="reported",
        )
        order.status = "reported"
        db.add(result)
        db.commit()
        db.refresh(result)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=order.patient_id,
            action="report",
            resource_type="imaging_result",
            resource_id=result.id,
            client_ip=client_ip,
        )
        return result

    @staticmethod
    def validate_report(
        db: Session, *, clinic_id: int, result_id: int, actor: User, client_ip: str | None = None
    ) -> models.ImagingResult:
        result = (
            db.query(models.ImagingResult)
            .join(models.ImagingOrder)
            .filter(
                models.ImagingResult.id == result_id,
                models.ImagingOrder.clinic_id == clinic_id,
            )
            .first()
        )
        if not result:
            raise HTTPException(status_code=404, detail="Imaging result not found")
        result.status = "validated"
        result.validated_by_user_id = actor.id
        result.validated_at = datetime.utcnow()
        result.order.status = "validated"
        db.commit()
        db.refresh(result)
        ImagingService.attach_report_to_patient_record(db, result=result, actor=actor)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=result.order.patient_id,
            action="validate",
            resource_type="imaging_result",
            resource_id=result.id,
            client_ip=client_ip,
        )
        return result

    @staticmethod
    def attach_report_to_patient_record(
        db: Session, *, result: models.ImagingResult, actor: User
    ) -> None:
        """Persist validated imaging report as a patient document."""
        from services.secure_attachment_storage import SecureAttachmentStorage

        order = result.order
        body = (
            f"Imagerie: {order.modality} — {order.body_part or 'examen'}\n"
            f"Indication: {order.clinical_indication or '—'}\n"
            f"Constats: {result.findings or '—'}\n"
            f"Conclusion: {result.impression or '—'}\n"
            f"Recommandations: {result.recommendations or '—'}\n"
            f"Validé le: {result.validated_at or datetime.utcnow()}\n"
        ).encode("utf-8")
        stored = SecureAttachmentStorage.store(
            body, original_filename=f"imaging_result_{order.id}.txt", extension=".txt"
        )
        db.add(
            models.PatientDocument(
                patient_id=order.patient_id,
                uploaded_by=actor.id,
                type_document="imaging_report",
                file_path=stored.storage_key,
                original_filename=stored.original_filename,
                mime_type=stored.mime_type,
                content_sha256=stored.content_sha256,
            )
        )
        db.add(
            models.ClinicalNote(
                patient_id=order.patient_id,
                doctor_id=order.consultation.doctor_id if order.consultation else None,
                appointment_id=order.consultation.appointment_id if order.consultation else None,
                note_type="imaging",
                contenu=body.decode("utf-8"),
            )
        )
        db.commit()

    @staticmethod
    def _get_order(db: Session, clinic_id: int, order_id: int) -> models.ImagingOrder:
        order = (
            db.query(models.ImagingOrder)
            .filter(models.ImagingOrder.id == order_id, models.ImagingOrder.clinic_id == clinic_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Imaging order not found")
        return order
