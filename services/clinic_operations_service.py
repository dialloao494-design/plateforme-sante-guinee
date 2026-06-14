"""Clinic-wide operational summary for the unified operations dashboard."""

from __future__ import annotations

from sqlalchemy.orm import Session

import models
from services.clinic_billing_service import ClinicBillingService
from services.clinical_workflow_service import ClinicalWorkflowService


def clinic_operations_summary(db: Session, *, clinic_id: int) -> dict:
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    reception = ClinicalWorkflowService.reception_queue(db, clinic_id=clinic_id)
    scheduled = sum(1 for r in reception if r.clinical_status == "scheduled")
    waiting = sum(1 for r in reception if r.clinical_status == "checked_in")

    doctor_queue = (
        db.query(models.RendezVous)
        .filter(
            models.RendezVous.clinic_id == clinic_id,
            models.RendezVous.clinical_status.in_(("checked_in", "in_consultation")),
            models.RendezVous.status != "cancelled",
        )
        .all()
    )
    in_consultation = sum(1 for r in doctor_queue if r.clinical_status == "in_consultation")
    doctor_waiting = sum(1 for r in doctor_queue if r.clinical_status == "checked_in")

    lab_orders = ClinicalWorkflowService.lab_queue(db, clinic_id=clinic_id)
    pharmacy_orders = ClinicalWorkflowService.pharmacy_queue(db, clinic_id=clinic_id)
    pending_charges = ClinicBillingService.pending_charges(db, clinic_id=clinic_id)
    revenue = ClinicBillingService.daily_summary(db, clinic_id=clinic_id, day=None)

    staff_count = (
        db.query(models.ClinicStaff)
        .filter(models.ClinicStaff.clinic_id == clinic_id, models.ClinicStaff.is_active.is_(True))
        .count()
    )

    pending_gnf = sum(c.amount_gnf or 0 for c in pending_charges)

    return {
        "clinic_id": clinic_id,
        "clinic_name": clinic.name if clinic else "",
        "reception_scheduled": scheduled,
        "reception_waiting": waiting,
        "cashier_pending_charges": len(pending_charges),
        "cashier_pending_gnf": pending_gnf,
        "doctor_waiting": doctor_waiting,
        "doctor_in_consultation": in_consultation,
        "lab_active_orders": len(lab_orders),
        "pharmacy_active_orders": len(pharmacy_orders),
        "revenue_collected_gnf": revenue.get("total_collected_gnf", 0),
        "revenue_pending_gnf": revenue.get("total_pending_gnf", 0),
        "revenue_paid_count": revenue.get("paid_count", 0),
        "staff_count": staff_count,
    }
