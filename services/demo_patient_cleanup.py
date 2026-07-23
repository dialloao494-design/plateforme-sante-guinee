"""Safe removal of obvious demo/test patients for a clinic.

Only matches synthetic name patterns used by prior E2E / field probes.
Never deletes pharmacy inventory or staff accounts.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

import models

# Match last_name OR first_name (case-insensitive).
TEST_NAME_PATTERNS = (
    r"^E2E",
    r"^Dashboard",
    r"^Test",
    r"^Demo",
    r"^Fake",
    r"^Sample",
    r"^Browser",
    r"^ClinicE2E",
    r"^Harden",
    r"^LabDbg",
    r"^Recep\d+",
    r"^Form\d+",
    r"^Test\d+",
)


def is_test_patient_name(first_name: str | None, last_name: str | None) -> bool:
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    for pat in TEST_NAME_PATTERNS:
        if re.search(pat, last, re.I) or re.search(pat, first, re.I):
            return True
    return False


def list_demo_patients(db: Session, clinic_id: int) -> list[models.Patient]:
    patients = (
        db.query(models.Patient)
        .filter(
            models.Patient.clinic_id == clinic_id,
            models.Patient.is_archived.is_(False),
        )
        .order_by(models.Patient.id)
        .all()
    )
    return [p for p in patients if is_test_patient_name(p.first_name, p.last_name)]


def _delete(db: Session, model, label: str, counts: dict[str, int], *filters) -> None:
    n = db.query(model).filter(*filters).delete(synchronize_session=False)
    if n:
        counts[label] = counts.get(label, 0) + n


def purge_patient(db: Session, patient_id: int) -> dict[str, int]:
    """Hard-delete a patient and dependent clinical/billing rows."""
    counts: dict[str, int] = {}

    lab_order_ids = [
        row[0] for row in db.query(models.LabOrder.id).filter(models.LabOrder.patient_id == patient_id).all()
    ]
    if lab_order_ids:
        _delete(db, models.LabResult, "lab_results", counts, models.LabResult.lab_order_id.in_(lab_order_ids))
        _delete(db, models.LabOrder, "lab_orders", counts, models.LabOrder.id.in_(lab_order_ids))

    imaging_order_ids = [
        row[0]
        for row in db.query(models.ImagingOrder.id).filter(models.ImagingOrder.patient_id == patient_id).all()
    ]
    if imaging_order_ids:
        _delete(
            db,
            models.ImagingResult,
            "imaging_results",
            counts,
            models.ImagingResult.order_id.in_(imaging_order_ids),
        )
        _delete(db, models.ImagingOrder, "imaging_orders", counts, models.ImagingOrder.id.in_(imaging_order_ids))

    rx_ids = [
        row[0]
        for row in db.query(models.Prescription.id).filter(models.Prescription.patient_id == patient_id).all()
    ]
    if rx_ids:
        _delete(db, models.PharmacyOrder, "pharmacy_orders", counts, models.PharmacyOrder.prescription_id.in_(rx_ids))
        _delete(
            db,
            models.PrescriptionItem,
            "prescription_items",
            counts,
            models.PrescriptionItem.prescription_id.in_(rx_ids),
        )
        _delete(db, models.Prescription, "prescriptions", counts, models.Prescription.id.in_(rx_ids))

    _delete(db, models.PharmacyOrder, "pharmacy_orders", counts, models.PharmacyOrder.patient_id == patient_id)
    _delete(db, models.NurseAssessment, "nurse_assessments", counts, models.NurseAssessment.patient_id == patient_id)
    _delete(db, models.NursingProcedure, "nursing_procedures", counts, models.NursingProcedure.patient_id == patient_id)
    _delete(
        db,
        models.DoctorMedicineDelivery,
        "doctor_medicine_deliveries",
        counts,
        models.DoctorMedicineDelivery.patient_id == patient_id,
    )
    _delete(
        db,
        models.ClinicServiceRequest,
        "service_requests",
        counts,
        models.ClinicServiceRequest.patient_id == patient_id,
    )
    _delete(db, models.DischargeSummary, "discharges", counts, models.DischargeSummary.patient_id == patient_id)
    _delete(
        db,
        models.ConsultationSummary,
        "consultation_summaries",
        counts,
        models.ConsultationSummary.patient_id == patient_id,
    )
    _delete(db, models.ClinicalNote, "clinical_notes", counts, models.ClinicalNote.patient_id == patient_id)

    invoice_ids = [row[0] for row in db.query(models.Invoice.id).filter(models.Invoice.patient_id == patient_id).all()]
    if invoice_ids:
        _delete(db, models.PaymentRecord, "payment_records", counts, models.PaymentRecord.invoice_id.in_(invoice_ids))
        _delete(db, models.InvoiceItem, "invoice_items", counts, models.InvoiceItem.invoice_id.in_(invoice_ids))
        _delete(db, models.ClinicRefund, "refunds", counts, models.ClinicRefund.invoice_id.in_(invoice_ids))
        _delete(db, models.Invoice, "invoices", counts, models.Invoice.id.in_(invoice_ids))
    _delete(db, models.ClinicRefund, "refunds", counts, models.ClinicRefund.patient_id == patient_id)

    charge_ids = [
        row[0] for row in db.query(models.ClinicCharge.id).filter(models.ClinicCharge.patient_id == patient_id).all()
    ]
    if charge_ids:
        _delete(
            db,
            models.ClinicChargePayment,
            "charge_payments",
            counts,
            models.ClinicChargePayment.charge_id.in_(charge_ids),
        )
        _delete(db, models.ClinicCharge, "charges", counts, models.ClinicCharge.id.in_(charge_ids))

    admission_ids = [
        row[0] for row in db.query(models.Admission.id).filter(models.Admission.patient_id == patient_id).all()
    ]
    if admission_ids:
        _delete(db, models.PatientStay, "patient_stays", counts, models.PatientStay.admission_id.in_(admission_ids))
        _delete(db, models.Admission, "admissions", counts, models.Admission.id.in_(admission_ids))
    _delete(db, models.ClinicalVisit, "visits", counts, models.ClinicalVisit.patient_id == patient_id)

    _delete(
        db,
        models.ClinicalConsultation,
        "consultations",
        counts,
        models.ClinicalConsultation.patient_id == patient_id,
    )

    if hasattr(models, "PatientVisitWorkflowStep") and hasattr(models, "PatientVisitWorkflow"):
        wf_ids = [
            row[0]
            for row in db.query(models.PatientVisitWorkflow.id)
            .filter(models.PatientVisitWorkflow.patient_id == patient_id)
            .all()
        ]
        if wf_ids:
            _delete(
                db,
                models.PatientVisitWorkflowStep,
                "visit_workflow_steps",
                counts,
                models.PatientVisitWorkflowStep.workflow_id.in_(wf_ids),
            )
            _delete(
                db,
                models.PatientVisitWorkflow,
                "visit_workflows",
                counts,
                models.PatientVisitWorkflow.id.in_(wf_ids),
            )

    _delete(db, models.AppointmentReminder, "reminders", counts, models.AppointmentReminder.patient_id == patient_id)
    _delete(db, models.RendezVous, "appointments", counts, models.RendezVous.patient_id == patient_id)
    _delete(db, models.PatientDocument, "documents", counts, models.PatientDocument.patient_id == patient_id)
    _delete(db, models.NutritionAssessment, "nutrition", counts, models.NutritionAssessment.patient_id == patient_id)
    _delete(
        db,
        models.ImmunizationRecord,
        "immunizations",
        counts,
        models.ImmunizationRecord.patient_id == patient_id,
    )
    _delete(db, models.PatientVitalSigns, "vitals", counts, models.PatientVitalSigns.patient_id == patient_id)
    _delete(db, models.PatientAllergy, "allergies", counts, models.PatientAllergy.patient_id == patient_id)
    _delete(
        db,
        models.PatientChronicCondition,
        "chronic_conditions",
        counts,
        models.PatientChronicCondition.patient_id == patient_id,
    )
    _delete(db, models.FollowUpSchedule, "follow_ups", counts, models.FollowUpSchedule.patient_id == patient_id)
    _delete(
        db,
        models.PatientMedicalRecord,
        "medical_records",
        counts,
        models.PatientMedicalRecord.patient_id == patient_id,
    )
    # Keep audit rows but null patient link where allowed
    db.query(models.ClinicalAuditLog).filter(models.ClinicalAuditLog.patient_id == patient_id).update(
        {models.ClinicalAuditLog.patient_id: None},
        synchronize_session=False,
    )

    _delete(db, models.Patient, "patients", counts, models.Patient.id == patient_id)
    return counts


def cleanup_demo_patients(
    db: Session,
    clinic_id: int,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    patients = list_demo_patients(db, clinic_id)
    preview = [
        {
            "id": p.id,
            "patient_number": p.patient_number,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "phone": p.phone,
        }
        for p in patients
    ]
    totals: dict[str, int] = {}
    if execute:
        for p in patients:
            row = purge_patient(db, p.id)
            for k, v in row.items():
                totals[k] = totals.get(k, 0) + v
        db.commit()
    return {
        "clinic_id": clinic_id,
        "matched": len(preview),
        "patients": preview,
        "executed": bool(execute),
        "deleted_counts": totals,
        "patterns": list(TEST_NAME_PATTERNS),
    }
