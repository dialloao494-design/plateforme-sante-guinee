from sqlalchemy import Column, Integer, Time, ForeignKey, Boolean, String
from sqlalchemy.orm import relationship
from database import Base


class DoctorAvailability(Base):
    __tablename__ = "doctor_availabilities"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    start_time = Column(Time, nullable=False)  # e.g., 09:00:00
    end_time = Column(Time, nullable=False)  # e.g., 17:00:00
    is_active = Column(Boolean, default=True)

    doctor = relationship("Doctor", back_populates="availabilities")
