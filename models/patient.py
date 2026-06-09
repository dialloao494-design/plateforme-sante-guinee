from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    age = Column(Integer)
    gender = Column(String)
    date_of_birth = Column(Date, nullable=True)
    phone = Column(String(32), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", back_populates="patient_profile")
    rendezvous = relationship("RendezVous", back_populates="patient")
    clinical_notes = relationship("ClinicalNote", back_populates="patient")
    consultation_summaries = relationship("ConsultationSummary", back_populates="patient")
    documents = relationship("PatientDocument", back_populates="patient")
