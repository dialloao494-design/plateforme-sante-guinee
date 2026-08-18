"""Unified chronological patient timeline across all clinical modules."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

import models
from services.pharmacy_clinical_service import PharmacyClinicalService
from core.tenant import assert_patient_in_clinic


def _dt(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class PatientTimelineService:
    @staticmethod
    def build_timeline(db: Session, *, clinic_id: int, patient_id: int) -> dict:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            return {"patient_id": patient_id, "events": []}

        events: list[dict] = []

        for appt in (
            db.query(models.RendezVous)
            .filter(models.RendezVous.clinic_id == clinic_id, models.RendezVous.patient_id == patient_id)
            .all()
        ):
            events.append(
                {
                    "at": _dt(appt.date),
                    "module": "reception",
                    "type": "appointment",
                    "id": appt.id,
                    "summary": f"Rendez-vous — {appt.clinical_status or appt.status}",
                    "detail": {"status": appt.clinical_status, "date": _dt(appt.date)},
                }
            )

        consultations = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.patient_id == patient_id,
            )
            .all()
        )
        for c in consultations:
            events.append(
                {
                    "at": _dt(c.started_at or c.created_at),
                    "module": "doctor",
                    "type": "consultation",
                    "id": c.id,
                    "summary": f"Consultation — {c.diagnosis or c.chief_complaint or c.status}",
                    "detail": {"status": c.status, "diagnosis": c.diagnosis},
                }
            )

        for row in (
            db.query(models.ImmunizationRecord)
            .filter(
                models.ImmunizationRecord.clinic_id == clinic_id,
                models.ImmunizationRecord.patient_id == patient_id,
                models.ImmunizationRecord.deleted_at.is_(None),
            )
            .all()
        ):
            events.append(
                {
                    "at": _dt(row.administered_at),
                    "module": "pev",
                    "type": "vaccination",
                    "id": row.id,
                    "summary": f"PEV — {row.vaccine_name} ({row.dose_label or row.dose_number or ''})",
                    "detail": {"vaccine_code": row.vaccine_code, "vaccinator": row.vaccinator_name},
                }
            )

        for row in (
            db.query(models.NutritionAssessment)
            .filter(
                models.NutritionAssessment.clinic_id == clinic_id,
                models.NutritionAssessment.patient_id == patient_id,
                models.NutritionAssessment.deleted_at.is_(None),
            )
            .all()
        ):
            events.append(
                {
                    "at": _dt(row.recorded_at),
                    "module": "nutrition",
                    "type": "assessment",
                    "id": row.id,
                    "summary": f"Nutrition — {row.nutritional_status or 'consultation'}",
                    "detail": {
                        "weight_kg": row.weight_kg,
                        "muac_cm": row.muac_cm,
                        "diagnosis": row.nutritional_diagnosis,
                    },
                }
            )

        for row in (
            db.query(models.NursingProcedure)
            .filter(
                models.NursingProcedure.clinic_id == clinic_id,
                models.NursingProcedure.patient_id == patient_id,
                models.NursingProcedure.deleted_at.is_(None),
            )
            .all()
        ):
            events.append(
                {
                    "at": _dt(row.procedure_date),
                    "module": "nursing",
                    "type": "procedure",
                    "id": row.id,
                    "summary": f"Soins — {row.procedure_type}",
                    "detail": {"nurse": row.nurse_name, "notes": row.notes},
                }
            )

        for adm in (
            db.query(models.Admission)
            .options(joinedload(models.Admission.patient))
            .filter(models.Admission.clinic_id == clinic_id, models.Admission.patient_id == patient_id)
            .all()
        ):
            events.append(
                {
                    "at": _dt(adm.admitted_at),
                    "module": "hospitalization",
                    "type": "admission",
                    "id": adm.id,
                    "summary": f"Hospitalisation — {adm.diagnosis_summary or adm.reason or adm.status}",
                    "detail": {
                        "status": adm.status,
                        "outcome": adm.outcome,
                        "discharged_at": _dt(adm.discharged_at),
                    },
                }
            )

        lab_orders = (
            db.query(models.LabOrder)
            .options(joinedload(models.LabOrder.results))
            .filter(
                models.LabOrder.clinic_id == clinic_id,
                models.LabOrder.patient_id == patient_id,
                models.LabOrder.deleted_at.is_(None),
            )
            .all()
        )
        for order in lab_orders:
            events.append(
                {
                    "at": _dt(order.created_at),
                    "module": "lab",
                    "type": "lab_order",
                    "id": order.id,
                    "summary": f"Laboratoire — {order.test_name} ({order.status})",
                    "detail": {"test_code": order.test_code, "priority": order.priority},
                }
            )
            for res in order.results or []:
                events.append(
                    {
                        "at": _dt(res.validated_at or res.created_at),
                        "module": "lab",
                        "type": "lab_result",
                        "id": res.id,
                        "summary": f"Résultat labo — {order.test_name}: {res.result_summary or res.status}",
                        "detail": {"status": res.status, "interpretation": res.interpretation},
                    }
                )

        pharmacy_orders = (
            db.query(models.PharmacyOrder)
            .options(
                joinedload(models.PharmacyOrder.prescription).joinedload(models.Prescription.items)
            )
            .filter(
                models.PharmacyOrder.clinic_id == clinic_id,
                models.PharmacyOrder.patient_id == patient_id,
            )
            .all()
        )
        for po in pharmacy_orders:
            events.append(
                {
                    "at": _dt(po.dispensed_at or po.created_at),
                    "module": "pharmacy",
                    "type": "dispense",
                    "id": po.id,
                    "summary": f"Pharmacie — {po.status}",
                    "detail": {"medications": PharmacyClinicalService._medications_text(po)},
                }
            )

        events.sort(key=lambda e: e.get("at") or "", reverse=True)

        return {
            "patient_id": patient_id,
            "patient": {
                "id": patient.id,
                "patient_number": patient.patient_number,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "age": patient.age,
                "gender": patient.gender,
                "phone": patient.phone,
                "date_of_birth": _dt(patient.date_of_birth),
            },
            "events": events,
            "counts": {
                "reception": sum(1 for e in events if e["module"] == "reception"),
                "doctor": sum(1 for e in events if e["module"] == "doctor"),
                "pev": sum(1 for e in events if e["module"] == "pev"),
                "nutrition": sum(1 for e in events if e["module"] == "nutrition"),
                "nursing": sum(1 for e in events if e["module"] == "nursing"),
                "hospitalization": sum(1 for e in events if e["module"] == "hospitalization"),
                "lab": sum(1 for e in events if e["module"] == "lab"),
                "pharmacy": sum(1 for e in events if e["module"] == "pharmacy"),
            },
        }
