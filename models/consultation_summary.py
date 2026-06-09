from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class ConsultationSummary(Base):
    __tablename__ = "consultation_summaries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=True, index=True)
    diagnostic = Column(Text, nullable=True)
    traitement = Column(Text, nullable=True)
    recommandations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient = relationship("Patient", back_populates="consultation_summaries")
    doctor = relationship("Doctor", back_populates="consultation_summaries")
