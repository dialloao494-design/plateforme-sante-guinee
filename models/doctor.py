from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, index=True)
    specialty = Column(String)
    consultation_fee = Column(Float, default=0.0, nullable=False)  # Price per consultation in GNF or local currency

    user = relationship("User", back_populates="doctor_profile")
    rendezvous = relationship("RendezVous", back_populates="doctor")
    availabilities = relationship("DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan")