from sqlalchemy import CheckConstraint, Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

_CLINICAL_ROLES = (
    "'patient', 'doctor', 'platform_admin', 'clinic_admin', 'admin', "
    "'receptionist', 'cashier', 'lab_technician', 'pharmacist'"
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            f"role IN ({_CLINICAL_ROLES})",
            name="ck_users_role_allowed",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    clinic_id = Column(Integer, nullable=True, index=True)  # staff home clinic

    patient_profile = relationship("Patient", back_populates="user", uselist=False)
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)
    notification_events = relationship("NotificationEvent", back_populates="user")

    @property
    def password_hash(self) -> str:
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        self.hashed_password = value