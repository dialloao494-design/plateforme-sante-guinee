"""Patient visit workflow — department queues (Reception → Nutrition → PEV → Doctor, etc.)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class PatientVisitWorkflow(Base):
    __tablename__ = "patient_visit_workflows"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    clinical_visit_id = Column(Integer, ForeignKey("clinical_visits.id"), nullable=True, index=True)
    workflow_type = Column(String(32), nullable=False, index=True)
    # child | adult_doctor | adult_lab | adult_midwife
    current_department = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    # active | completed | cancelled
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="visit_workflows")
    steps = relationship(
        "PatientVisitWorkflowStep",
        back_populates="workflow",
        order_by="PatientVisitWorkflowStep.step_order",
        cascade="all, delete-orphan",
    )


class PatientVisitWorkflowStep(Base):
    __tablename__ = "patient_visit_workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("patient_visit_workflows.id"), nullable=False, index=True)
    department = Column(String(32), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="waiting", index=True)
    # waiting | in_progress | completed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    workflow = relationship("PatientVisitWorkflow", back_populates="steps")
