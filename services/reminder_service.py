"""Appointment reminder scheduling and patient responses."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import models
from services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

REMINDER_OFFSETS = {"48h": 48, "24h": 24}


class ReminderService:
    @staticmethod
    def schedule_for_appointment(db: Session, appointment: models.RendezVous) -> None:
        if appointment.status in ("cancelled", "completed"):
            return
        existing = (
            db.query(models.AppointmentReminder)
            .filter(models.AppointmentReminder.appointment_id == appointment.id)
            .count()
        )
        if existing:
            return
        appt_dt = appointment.date
        for rtype, hours in REMINDER_OFFSETS.items():
            scheduled = appt_dt - timedelta(hours=hours)
            if scheduled <= datetime.utcnow():
                continue
            db.add(
                models.AppointmentReminder(
                    appointment_id=appointment.id,
                    patient_id=appointment.patient_id,
                    reminder_type=rtype,
                    scheduled_at=scheduled,
                )
            )
        db.commit()

    @staticmethod
    def process_due_reminders(db: Session) -> int:
        now = datetime.utcnow()
        due = (
            db.query(models.AppointmentReminder)
            .filter(
                models.AppointmentReminder.status == "pending",
                models.AppointmentReminder.scheduled_at <= now,
            )
            .all()
        )
        wa = WhatsAppService()
        sent = 0
        for reminder in due:
            appt = reminder.appointment
            patient = reminder.patient
            doctor = appt.doctor if appt else None
            if not patient or not appt:
                reminder.status = "cancelled"
                continue
            phone = patient.phone or ""
            if not phone and patient.user:
                phone = getattr(patient.user, "phone", "") or ""
            hours = REMINDER_OFFSETS.get(reminder.reminder_type, 24)
            body = wa.appointment_reminder_message(
                patient_name=f"{patient.first_name} {patient.last_name}".strip(),
                doctor_name=doctor.name if doctor else "—",
                appt_date=appt.date.strftime("%d/%m/%Y %H:%M"),
                hours_before=hours,
            )
            try:
                result = wa.send_text(phone, body)
                reminder.status = "sent"
                reminder.sent_at = datetime.utcnow()
                reminder.whatsapp_message_id = str(result.get("messages", [{}])[0].get("id", "")) if isinstance(result, dict) else None
                db.add(
                    models.ReminderEvent(
                        reminder_id=reminder.id,
                        event_type="sent",
                        payload=json.dumps(result, default=str)[:1000],
                    )
                )
                sent += 1
            except Exception as exc:
                logger.error("Reminder send failed id=%s: %s", reminder.id, exc)
                reminder.status = "failed"
                db.add(
                    models.ReminderEvent(
                        reminder_id=reminder.id,
                        event_type="failed",
                        payload=str(exc)[:500],
                    )
                )
        db.commit()
        return sent

    @staticmethod
    def handle_patient_response(
        db: Session, *, appointment_id: int, action: str, payload: str | None = None
    ) -> models.ReminderEvent:
        action = action.lower().strip()
        if action not in ("confirmed", "cancelled", "reschedule_requested"):
            action = "confirmed" if action in ("confirmer", "confirm", "oui", "yes") else action
        if action in ("annuler", "cancel"):
            action = "cancelled"
        if action in ("reporter", "reschedule"):
            action = "reschedule_requested"

        reminder = (
            db.query(models.AppointmentReminder)
            .filter(models.AppointmentReminder.appointment_id == appointment_id)
            .order_by(models.AppointmentReminder.created_at.desc())
            .first()
        )
        if not reminder:
            raise ValueError("No reminder for appointment")

        event = models.ReminderEvent(
            reminder_id=reminder.id,
            event_type=action,
            payload=payload,
        )
        db.add(event)

        appt = reminder.appointment
        if action == "confirmed" and appt:
            appt.clinical_status = appt.clinical_status or "scheduled"
        elif action == "cancelled" and appt:
            appt.status = "cancelled"
            appt.clinical_status = "cancelled"
        elif action == "reschedule_requested" and appt:
            appt.clinical_status = "reschedule_requested"

        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def staff_notifications(db: Session, *, clinic_id: int | None = None, limit: int = 50) -> list[dict]:
        q = (
            db.query(models.ReminderEvent)
            .join(models.AppointmentReminder)
            .join(models.RendezVous)
            .filter(models.ReminderEvent.event_type.in_(["confirmed", "cancelled", "reschedule_requested"]))
        )
        if clinic_id:
            q = q.filter(models.RendezVous.clinic_id == clinic_id)
        events = q.order_by(models.ReminderEvent.created_at.desc()).limit(limit).all()
        out = []
        for ev in events:
            rem = ev.reminder
            appt = rem.appointment if rem else None
            out.append(
                {
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "created_at": ev.created_at.isoformat(),
                    "appointment_id": rem.appointment_id if rem else None,
                    "patient_id": rem.patient_id if rem else None,
                    "appointment_date": appt.date.isoformat() if appt else None,
                }
            )
        return out

    @staticmethod
    def _phone_suffix(phone: str) -> str:
        return "".join(c for c in phone if c.isdigit())[-9:]

    @staticmethod
    def resolve_appointment_id_by_phone(db: Session, phone: str) -> int | None:
        """Find the next upcoming appointment for a patient matched by phone suffix."""
        suffix = ReminderService._phone_suffix(phone)
        if len(suffix) < 7:
            return None
        patient_ids = [
            p.id
            for p in db.query(models.Patient).filter(models.Patient.phone.isnot(None)).all()
            if ReminderService._phone_suffix(p.phone or "") == suffix
        ]
        if not patient_ids:
            return None
        appt = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.patient_id.in_(patient_ids),
                models.RendezVous.status.notin_(["cancelled", "completed"]),
                models.RendezVous.date >= datetime.utcnow(),
            )
            .order_by(models.RendezVous.date.asc())
            .first()
        )
        return appt.id if appt else None
