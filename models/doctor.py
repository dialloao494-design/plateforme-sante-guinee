from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    first_name = Column(String, nullable=False, index=True)
    last_name = Column(String, nullable=False, index=True)
    specialty = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=False)
    photo_url = Column(String, nullable=True)
    consultation_fee = Column(Float, default=0.0, nullable=False)  # Price per consultation in GNF or local currency
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=True, index=True)

    user = relationship("User", back_populates="doctor_profile")
    clinic = relationship("Clinic", back_populates="doctors")

    @property
    def location(self):
        return self.city

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def name(self) -> str:
        # Public API-friendly display name.
        return f"Dr {self.full_name}".strip()

    def __repr__(self) -> str:
        return f'<Doctor id={self.id} name="{self.name}" specialty="{self.specialty}">'

    rendezvous = relationship("RendezVous", back_populates="doctor")
    availabilities = relationship("DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="doctor")
    consultation_summaries = relationship("ConsultationSummary", back_populates="doctor")