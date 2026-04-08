from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class RendezVous(Base):
    __tablename__ = "rendezvous"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=30, nullable=False)  # 30, 60, 90, 120 minutes
    status = Column(String, default="pending", nullable=False, index=True)  # pending, confirmed, completed, cancelled
    payment_status = Column(String, default="pending", nullable=False, index=True)  # pending, paid, failed
    price = Column(Float, default=0.0, nullable=False)  # Appointment price in GNF or local currency
    payment_intent_id = Column(String, nullable=True, index=True)  # Stripe payment intent ID
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    doctor = relationship("Doctor", back_populates="rendezvous")
    patient = relationship("Patient", back_populates="rendezvous")