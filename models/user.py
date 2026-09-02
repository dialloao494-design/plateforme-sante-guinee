from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from database import Base

_CLINICAL_ROLES = (
    "'patient', 'doctor', 'platform_owner', 'platform_admin', 'clinic_admin', 'admin', "
    "'receptionist', 'cashier', 'lab_technician', 'pharmacist', 'nutritionist', 'midwife', "
    "'pev_agent', 'nurse'"
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
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    clinic_id = Column(Integer, nullable=True, index=True)  # staff home clinic
    is_active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    session_version = Column(Integer, nullable=False, default=0)
    email_verified_at = Column(DateTime, nullable=True)
    # Security Wave 0 — identity / session hardening
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)
    token_version = Column(Integer, nullable=False, default=0)
    password_changed_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient_profile = relationship("Patient", back_populates="user", uselist=False)
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)
    notification_events = relationship("NotificationEvent", back_populates="user")

    @property
    def password_hash(self) -> str:
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        self.hashed_password = value
