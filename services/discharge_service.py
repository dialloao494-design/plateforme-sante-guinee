"""Patient discharge workflow and EMR archive."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from models.user import User
from services.cis_audit import log_cis
from services.medical_history_service import MedicalHistoryService
from services.unified_billing_service import UnifiedBillingService
from services.visit_service import VisitService


class DischargeService:
    @staticmethod
    def get_checklist(db: Session, *, clinic_id: int, visit_id: int) -> dict:
        visit = (
            db.query(models.ClinicalVisit)
            .filter(models.ClinicalVisit.id == visit_id, models.ClinicalVisit.clinic_id == clinic_id)
            .first()
        )
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        pending_charges = UnifiedBillingService.collect_pending_charges(
            db, clinic_id=clinic_id, patient_id=visit.patient_id, visit_id=visit.id
        )
        unpaid_invoices = (
            db.query(models.Invoice)
            .filter(
                models.Invoice.visit_id == visit.id,
                models.Invoice.status.notin_(["paid", "cancelled"]),
            )
            .count()
        )
        pending_pharma = 0
        if visit.consultation_id:
            pending_pharma = (
                db.query(models.PharmacyOrder)
                .join(models.Prescription)
                .filter(
                    models.Prescription.consultation_id == visit.consultation_id,
                    models.PharmacyOrder.status.notin_(["dispensed", "cancelled"]),
                )
                .count()
            )
        has_charges = (
            db.query(models.ClinicCharge)
            .filter(models.ClinicCharge.visit_id == visit.id)
            .count()
            > 0
        ) or len(pending_charges) > 0
        paid_invoice = (
            db.query(models.Invoice)
            .filter(models.Invoice.visit_id == visit.id, models.Invoice.status == "paid")
            .first()
        )
        invoice_validated = paid_invoice is not None if has_charges else True
        return {
            "visit_id": visit.id,
            "patient_id": visit.patient_id,
            "pending_charges": len(pending_charges),
            "unpaid_invoices": unpaid_invoices,
            "pending_pharmacy_orders": pending_pharma,
            "invoice_validated": invoice_validated,
            "ready_for_discharge": (
                len(pending_charges) == 0
                and unpaid_invoices == 0
                and invoice_validated
                and pending_pharma == 0
            ),
        }

    @staticmethod
    def discharge_patient(
        db: Session,
        *,
        clinic_id: int,
        visit_id: int,
        actor: User,
        follow_up_instructions: str | None = None,
        force: bool = False,
        client_ip: str | None = None,
    ) -> models.DischargeSummary:
        checklist = DischargeService.get_checklist(db, clinic_id=clinic_id, visit_id=visit_id)
        if not checklist["ready_for_discharge"] and not force:
            raise HTTPException(
                status_code=400,
                detail="Sortie impossible : facturation ou pharmacie incomplète",
            )
        visit = db.query(models.ClinicalVisit).filter(models.ClinicalVisit.id == visit_id).first()
        consultation = None
        if visit and visit.consultation_id:
            consultation = (
                db.query(models.ClinicalConsultation)
                .filter(models.ClinicalConsultation.id == visit.consultation_id)
                .first()
            )
        admission = None
        if visit and visit.admission_id:
            admission = db.query(models.Admission).filter(models.Admission.id == visit.admission_id).first()

        invoice = (
            db.query(models.Invoice)
            .filter(models.Invoice.visit_id == visit_id, models.Invoice.status == "paid")
            .order_by(models.Invoice.paid_at.desc())
            .first()
        )

        medications = ""
        procedures = ""
        if consultation:
            rx_list = (
                db.query(models.PrescriptionItem)
                .join(models.Prescription)
                .filter(models.Prescription.consultation_id == consultation.id)
                .all()
            )
            medications = "; ".join(
                f"{r.medication_name} {r.dosage or ''} {r.frequency or ''}".strip() for r in rx_list
            )
            lab_list = db.query(models.LabOrder).filter(models.LabOrder.consultation_id == consultation.id).all()
            imaging_list = (
                db.query(models.ImagingOrder).filter(models.ImagingOrder.consultation_id == consultation.id).all()
            )
            proc_parts = [l.test_name for l in lab_list]
            proc_parts.extend(f"{i.modality} {i.body_part or ''}".strip() for i in imaging_list)
            procedures = "; ".join(proc_parts)

        summary = models.DischargeSummary(
            clinic_id=clinic_id,
            patient_id=visit.patient_id,
            visit_id=visit_id,
            admission_id=visit.admission_id,
            consultation_id=visit.consultation_id,
            invoice_id=invoice.id if invoice else None,
            discharge_type="inpatient" if admission else "ambulatory",
            status="finalized",
            diagnoses=consultation.diagnosis if consultation else None,
            procedures=procedures or None,
            medications=medications or None,
            clinical_summary=consultation.treatment_plan if consultation else None,
            follow_up_instructions=follow_up_instructions,
            invoice_validated=invoice is not None,
            discharged_by_user_id=actor.id,
            discharged_at=datetime.utcnow(),
        )
        db.add(summary)

        if consultation and consultation.status != "completed":
            consultation.status = "completed"
            consultation.completed_at = datetime.utcnow()
        if admission and admission.status not in ("discharged", "cancelled"):
            admission.status = "discharged"
            admission.discharged_at = datetime.utcnow()

        VisitService.mark_discharged(db, visit)
        db.commit()
        db.refresh(summary)

        MedicalHistoryService.snapshot_consultation_to_dossier(db, consultation, actor=actor) if consultation else None
        DischargeService._archive_to_emr(db, summary, consultation, actor)
        summary.archived_to_emr = True
        VisitService.mark_archived(db, visit)
        db.commit()
        db.refresh(summary)

        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=visit.patient_id,
            action="discharge",
            resource_type="discharge_summary",
            resource_id=summary.id,
            client_ip=client_ip,
        )
        return summary

    @staticmethod
    def list_summaries(db: Session, *, clinic_id: int, patient_id: int | None = None) -> list[models.DischargeSummary]:
        q = db.query(models.DischargeSummary).filter(models.DischargeSummary.clinic_id == clinic_id)
        if patient_id:
            q = q.filter(models.DischargeSummary.patient_id == patient_id)
        return q.order_by(models.DischargeSummary.discharged_at.desc()).all()

    @staticmethod
    def list_open_visits(db: Session, *, clinic_id: int) -> list[models.ClinicalVisit]:
        return (
            db.query(models.ClinicalVisit)
            .filter(
                models.ClinicalVisit.clinic_id == clinic_id,
                models.ClinicalVisit.status.in_(["open", "billing", "paid"]),
            )
            .order_by(models.ClinicalVisit.started_at.desc())
            .limit(100)
            .all()
        )

    @staticmethod
    def _archive_to_emr(
        db: Session,
        summary: models.DischargeSummary,
        consultation: models.ClinicalConsultation | None,
        actor: User,
    ) -> None:
        """Persist discharge summary as permanent dossier entries."""
        note_parts = [
            f"Type: {summary.discharge_type}",
            f"Diagnostics: {summary.diagnoses or '—'}",
            f"Procédures: {summary.procedures or '—'}",
            f"Médicaments: {summary.medications or '—'}",
            f"Résumé: {summary.clinical_summary or '—'}",
            f"Suivi: {summary.follow_up_instructions or '—'}",
            f"Facture validée: {'oui' if summary.invoice_validated else 'non'}",
        ]
        db.add(
            models.ClinicalNote(
                patient_id=summary.patient_id,
                doctor_id=consultation.doctor_id if consultation else None,
                appointment_id=consultation.appointment_id if consultation else None,
                note_type="discharge",
                contenu="\n".join(note_parts),
            )
        )
        db.add(
            models.ConsultationSummary(
                patient_id=summary.patient_id,
                doctor_id=consultation.doctor_id if consultation else None,
                appointment_id=consultation.appointment_id if consultation else None,
                diagnostic=summary.diagnoses,
                traitement=summary.medications,
                recommandations=summary.follow_up_instructions,
            )
        )
        db.commit()
