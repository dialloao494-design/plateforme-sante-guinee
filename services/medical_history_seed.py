"""
Seed 50 simulated patients with multi-visit clinical history for longitudinal testing.

Run: python -m services.medical_history_seed
Or set ENABLE_MEDICAL_HISTORY_SEED=1 on startup.
"""

from __future__ import annotations

import logging
import os
import random
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

import models
from database import SessionLocal
from services.medical_history_service import ensure_medical_record

logger = logging.getLogger(__name__)

SEED_MARKER = "sim_history_"
SIM_PORTAL_PASSWORD = "SimPatient1!"
SIM_PORTAL_EMAIL_DOMAIN = "pilot.local"

DIAGNOSES = [
    ("Paludisme", "Coartem", "NFS"),
    ("Hypertension", "Amlodipine 5mg", "Glycémie"),
    ("Infection respiratoire", "Amoxicilline", None),
    ("Gastrite", "Oméprazole", None),
    ("Anémie", "Fer + acide folique", "NFS"),
    ("Diabète type 2", "Metformine", "Glycémie"),
]

ALLERGENS = ["Pénicilline", "Arachides", "Sulfamides", "Latex"]
CONDITIONS = ["Hypertension", "Diabète", "Asthme", "Drépanocytose"]


def _pick_doctor(db: Session, clinic_id: int) -> models.Doctor | None:
    return (
        db.query(models.Doctor)
        .filter(models.Doctor.clinic_id == clinic_id)
        .order_by(models.Doctor.id)
        .first()
    )


def link_simulated_portal_accounts(db: Session) -> int:
    """Create portal logins for seeded walk-in patients (idempotent)."""
    from security import hash_password

    linked = 0
    patients = (
        db.query(models.Patient)
        .filter(models.Patient.last_name.like(f"{SEED_MARKER}%"))
        .filter(models.Patient.user_id.is_(None))
        .all()
    )
    for patient in patients:
        suffix = patient.last_name.replace(SEED_MARKER, "")
        email = f"sim.patient.{suffix}@{SIM_PORTAL_EMAIL_DOMAIN}"
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            patient.user_id = existing_user.id
            linked += 1
            continue
        user = models.User(
            email=email,
            hashed_password=hash_password(SIM_PORTAL_PASSWORD),
            role="patient",
        )
        db.add(user)
        db.flush()
        patient.user_id = user.id
        linked += 1
    if linked:
        db.commit()
        logger.info("medical_history_seed: linked %s portal accounts", linked)
    return linked


def ensure_minimum_appointments(db: Session, *, clinic_id: int = 1, min_total: int = 200) -> int:
    """Top up historical appointments so QA volume targets are met."""
    current = db.query(models.RendezVous).count()
    if current >= min_total:
        return 0
    doctor = _pick_doctor(db, clinic_id)
    if not doctor:
        return 0
    patients = (
        db.query(models.Patient)
        .filter(models.Patient.last_name.like(f"{SEED_MARKER}%"))
        .order_by(models.Patient.id)
        .all()
    )
    if not patients:
        return 0
    added = 0
    day_offset = current
    while current + added < min_total:
        patient = patients[(current + added) % len(patients)]
        visit_date = datetime.utcnow() - timedelta(days=30 + (day_offset % 300), hours=day_offset % 8)
        rdv = models.RendezVous(
            date=visit_date,
            duration_minutes=30,
            status="completed",
            payment_status="paid",
            price=150_000,
            consultation_type="physical",
            doctor_id=doctor.id,
            patient_id=patient.id,
            clinic_id=clinic_id,
            clinical_status="completed",
        )
        db.add(rdv)
        added += 1
        day_offset += 1
    db.commit()
    logger.info("medical_history_seed: added %s top-up appointments (target %s)", added, min_total)
    return added


def seed_medical_history(db: Session, *, clinic_id: int = 1, count: int = 50) -> dict:
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic:
        logger.warning("medical_history_seed: clinic_id=%s not found", clinic_id)
        return {"created": 0, "skipped": True}

    doctor = _pick_doctor(db, clinic_id)
    if not doctor:
        logger.warning("medical_history_seed: no doctor for clinic %s", clinic_id)
        return {"created": 0, "skipped": True}

    existing = (
        db.query(models.Patient)
        .filter(models.Patient.last_name.like(f"{SEED_MARKER}%"))
        .count()
    )
    if existing >= count:
        logger.info("medical_history_seed: already seeded (%s patients)", existing)
        link_simulated_portal_accounts(db)
        ensure_minimum_appointments(db, clinic_id=clinic_id)
        return {"created": 0, "skipped": True, "existing": existing}

    created = 0
    base_date = date(2025, 1, 1)

    for i in range(count):
        last_name = f"{SEED_MARKER}{i + 1:03d}"
        if db.query(models.Patient).filter(models.Patient.last_name == last_name).first():
            continue

        patient = models.Patient(
            first_name=f"Simulé{i + 1}",
            last_name=last_name,
            age=random.randint(18, 75),
            gender=random.choice(["M", "F", "other"]),
            phone=f"+224620{i + 1:06d}",
        )
        db.add(patient)
        db.flush()
        ensure_medical_record(db, patient.id)

        if random.random() < 0.4:
            db.add(
                models.PatientAllergy(
                    patient_id=patient.id,
                    allergen=random.choice(ALLERGENS),
                    severity=random.choice(["mild", "moderate", "severe"]),
                    reaction="Urticaire",
                )
            )
        if random.random() < 0.35:
            db.add(
                models.PatientChronicCondition(
                    patient_id=patient.id,
                    condition_name=random.choice(CONDITIONS),
                    diagnosed_at=base_date + timedelta(days=random.randint(0, 365)),
                    status="active",
                )
            )

        visit_count = random.randint(2, 5)
        visit_day = 0
        for v in range(visit_count):
            visit_day += random.randint(30, 120)
            visit_date = datetime.combine(
                base_date + timedelta(days=visit_day), datetime.min.time().replace(hour=9 + v)
            )
            diagnosis, rx_med, lab_test = random.choice(DIAGNOSES)

            rdv = models.RendezVous(
                date=visit_date,
                duration_minutes=30,
                status="completed",
                payment_status="paid",
                price=150_000,
                consultation_type="physical",
                doctor_id=doctor.id,
                patient_id=patient.id,
                clinic_id=clinic_id,
                clinical_status="completed",
            )
            db.add(rdv)
            db.flush()

            consultation = models.ClinicalConsultation(
                clinic_id=clinic_id,
                appointment_id=rdv.id,
                patient_id=patient.id,
                doctor_id=doctor.id,
                status="completed",
                chief_complaint=f"Consultation #{v + 1}",
                diagnosis=diagnosis,
                treatment_plan=rx_med,
                started_at=visit_date,
                completed_at=visit_date + timedelta(minutes=25),
            )
            db.add(consultation)
            db.flush()

            db.add(
                models.PatientVitalSigns(
                    patient_id=patient.id,
                    consultation_id=consultation.id,
                    bp_systolic=random.randint(110, 145),
                    bp_diastolic=random.randint(70, 95),
                    heart_rate=random.randint(60, 100),
                    temperature_c=round(random.uniform(36.2, 37.8), 1),
                    weight_kg=round(random.uniform(50, 90), 1),
                    recorded_at=visit_date,
                )
            )

            rx = models.Prescription(
                clinic_id=clinic_id,
                consultation_id=consultation.id,
                patient_id=patient.id,
                prescriber_doctor_id=doctor.id,
                status="dispensed",
            )
            db.add(rx)
            db.flush()
            db.add(
                models.PrescriptionItem(
                    prescription_id=rx.id,
                    medication_name=rx_med,
                    dosage="1 cp",
                    frequency="2x/jour",
                    duration_days=7,
                )
            )

            if lab_test:
                order = models.LabOrder(
                    clinic_id=clinic_id,
                    consultation_id=consultation.id,
                    patient_id=patient.id,
                    ordered_by_user_id=1,
                    doctor_id=doctor.id,
                    test_code=lab_test[:3].upper(),
                    test_name=lab_test,
                    status="completed",
                )
                db.add(order)
                db.flush()
                db.add(
                    models.LabResult(
                        lab_order_id=order.id,
                        recorded_by_user_id=1,
                        result_summary="Résultats dans les normes",
                        reference_range="—",
                        interpretation="Normal",
                        status="validated",
                        validated_at=visit_date + timedelta(hours=2),
                    )
                )

            db.add(
                models.ConsultationSummary(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    appointment_id=rdv.id,
                    diagnostic=diagnosis,
                    traitement=rx_med,
                )
            )
            db.add(
                models.ClinicalNote(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    appointment_id=rdv.id,
                    note_type="consultation" if v == 0 else "suivi",
                    contenu=f"Visite {v + 1}: {diagnosis}. Traitement: {rx_med}.",
                )
            )

            if v < visit_count - 1:
                fu_date = (visit_date + timedelta(days=random.choice([7, 15, 30, 90]))).date()
                db.add(
                    models.FollowUpSchedule(
                        patient_id=patient.id,
                        clinic_id=clinic_id,
                        consultation_id=consultation.id,
                        doctor_id=doctor.id,
                        scheduled_date=fu_date,
                        interval_type=random.choice(["7d", "15d", "1m", "3m"]),
                        visit_type="follow_up" if v > 0 else "consultation",
                        reason="Contrôle" if v > 0 else "Première consultation",
                        clinical_notes="Symptômes résolus" if v > 0 else None,
                        status="completed" if fu_date < date.today() else "scheduled",
                    )
                )

        created += 1

    db.commit()
    link_simulated_portal_accounts(db)
    ensure_minimum_appointments(db, clinic_id=clinic_id)
    logger.info("medical_history_seed: created %s patients with multi-visit history", created)
    return {"created": created, "skipped": False}


def run_seed() -> dict:
    from database import engine
    from database_migrations import ensure_medical_history_schema

    ensure_medical_history_schema(engine)
    from database import Base
    import models.medical_history  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        return seed_medical_history(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_seed()
    print(result)
