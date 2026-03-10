from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class RendezVous(Base):
    __tablename__ = "rendezvous"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")

    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))

    doctor = relationship("Doctor", back_populates="rendezvous")
    patient = relationship("Patient", back_populates="rendezvous")