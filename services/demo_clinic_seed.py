"""
Optional demo dataset for clinic presentations (Guinea-oriented names, realistic statuses).

Enable with ENABLE_DEMO_CLINIC_SEED=true in the environment.
Safe to run multiple times: skips when demo markers already exist.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import func

import models
from database import SessionLocal
from security import hash_password

logger = logging.getLogger(__name__)

DEMO_PATIENT_PASSWORD = "Patient123!"

# Demo patient accounts (same password for simplicity during demos)
DEMO_PEOPLE = [
    {"email": "demo.ibrahima.camara@patient.gn", "first_name": "Ibrahima", "last_name": "Camara", "age": 34, "gender": "male"},
    {"email": "demo.fatoumata.diallo@patient.gn", "first_name": "Fatoumata", "last_name": "Diallo", "age": 29, "gender": "female"},
    {"email": "demo.mariama.barry@patient.gn", "first_name": "Mariama", "last_name": "Barry", "age": 41, "gender": "female"},
    {"email": "demo.mamadou.sow@patient.gn", "first_name": "Mamadou", "last_name": "Sow", "age": 52, "gender": "male"},
]


def seed_demo_clinic_data() -> None:
    db = SessionLocal()
    try:
        marker = db.query(models.User).filter(models.User.email == "demo.ibrahima.camara@patient.gn").first()
        if marker:
            logger.info("Demo clinic dataset already present; skipping.")
            return

        def _doctor_by_email(email: str) -> models.Doctor | None:
            u = db.query(models.User).filter(func.lower(models.User.email) == email.lower()).first()
            if not u:
                return None
            return db.query(models.Doctor).filter(models.Doctor.user_id == u.id).first()

        doctor_amina = _doctor_by_email("dr.amu@example.com")
        doctor_soul = _doctor_by_email("dr.soulaiman@example.com")

        if not doctor_amina or not doctor_soul:
            logger.warning("Demo clinic seed skipped: demo doctors not found.")
            return

        patient_users: list[tuple[models.User, models.Patient]] = []
        for row in DEMO_PEOPLE:
            email = row["email"].lower().strip()
            user = models.User(
                email=email,
                hashed_password=hash_password(DEMO_PATIENT_PASSWORD),
                role="patient",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            patient = models.Patient(
                user_id=user.id,
                first_name=row["first_name"],
                last_name=row["last_name"],
                age=row["age"],
                gender=row["gender"],
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            patient_users.append((user, patient))

        now = datetime.utcnow()
        scenarios = [
            # patient_idx, doctor, offset_days, duration, status, payment_status, price, consultation_type
            (0, doctor_amina, 1, 30, "confirmed", "paid", 45000.0, "teleconsultation"),
            (1, doctor_amina, 3, 45, "pending", "unpaid", 40000.0, "physical"),
            (2, doctor_soul, -2, 30, "completed", "paid", 35000.0, "physical"),
            (3, doctor_soul, -5, 60, "cancelled", "unpaid", 38000.0, "teleconsultation"),
            (0, doctor_soul, 7, 30, "paid", "paid", 35000.0, "physical"),
            (1, doctor_amina, -1, 30, "pending", "unpaid", 40000.0, "physical"),
        ]

        created_ids: list[int] = []
        for pidx, doctor, day_off, duration, status, pay_status, price, ctype in scenarios:
            user, patient = patient_users[pidx]
            rdv = models.RendezVous(
                date=now + timedelta(days=day_off, hours=10, minutes=30),
                duration_minutes=duration,
                status=status,
                payment_status=pay_status,
                price=price,
                consultation_type=ctype,
                doctor_id=doctor.id,
                patient_id=patient.id,
            )
            db.add(rdv)
            db.commit()
            db.refresh(rdv)
            created_ids.append(rdv.id)

        # Sample conversation on first two seeded appointments
        if len(created_ids) >= 2:
            ap1, ap2 = created_ids[0], created_ids[1]
            doc_user_amina = db.query(models.User).filter(models.User.id == doctor_amina.user_id).first()
            doc_user_soul = db.query(models.User).filter(models.User.id == doctor_soul.user_id).first()
            u0 = patient_users[0][0]
            u1 = patient_users[1][0]

            msgs = [
                (ap1, doc_user_amina.id, "Bonjour, merci de vous être connecté pour la téléconsultation."),
                (ap1, u0.id, "Bonjour docteur, j'ai encore des douleurs depuis hier."),
                (ap1, doc_user_amina.id, "Très bien, nous ferons le point sur vos symptômes dans un instant."),
                (ap2, u1.id, "Bonjour, je souhaite confirmer ma présence au cabinet jeudi."),
                (ap2, doc_user_amina.id, "Merci pour votre message, votre créneau est bien enregistré."),
            ]
            for appt_id, sender_id, text in msgs:
                db.add(
                    models.Message(
                        appointment_id=appt_id,
                        sender_user_id=sender_id,
                        content=text,
                    )
                )
            db.commit()

        logger.info("Demo clinic dataset seeded (%s patients, appointments + messages).", len(patient_users))
    except Exception as exc:
        db.rollback()
        logger.error("Demo clinic seed failed: %s", exc)
    finally:
        db.close()
