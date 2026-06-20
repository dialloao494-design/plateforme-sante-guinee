"""Child growth and nutrition monitoring."""

from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class NutritionAssessment(Base):
    """Growth monitoring visit — weight, height, MUAC."""

    __tablename__ = "nutrition_assessments"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    age_months = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    muac_cm = Column(Float, nullable=True)  # mid-upper arm circumference
    nutritional_status = Column(String(32), nullable=True)  # normal | moderate_malnutrition | severe_malnutrition
    nutritional_diagnosis = Column(Text, nullable=True)
    is_follow_up = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(Date, nullable=True)
    recommendations = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="nutrition_assessments")
