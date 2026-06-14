"""WhatsApp appointment reminders and reminder events."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class AppointmentReminder(Base):
    __tablename__ = "appointment_reminders"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    channel = Column(String(32), nullable=False, default="whatsapp")
    reminder_type = Column(String(16), nullable=False, index=True)
    # 48h | 24h
    scheduled_at = Column(DateTime, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    # pending | sent | failed | cancelled
    whatsapp_message_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    appointment = relationship("RendezVous", back_populates="reminders")
    patient = relationship("Patient", back_populates="appointment_reminders")
    events = relationship("ReminderEvent", back_populates="reminder", cascade="all, delete-orphan")


class ReminderEvent(Base):
    __tablename__ = "reminder_events"

    id = Column(Integer, primary_key=True, index=True)
    reminder_id = Column(Integer, ForeignKey("appointment_reminders.id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, index=True)
    # sent | delivered | read | confirmed | cancelled | reschedule_requested | failed
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    reminder = relationship("AppointmentReminder", back_populates="events")
