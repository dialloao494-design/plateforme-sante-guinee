"""Visit workflow API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

WorkflowType = Literal["child", "adult_doctor", "adult_lab", "adult_midwife"]
Department = Literal["reception", "nutrition", "pev", "doctor", "lab", "midwife"]


class VisitWorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    workflow_type: Optional[WorkflowType] = None
    notes: Optional[str] = None


class VisitWorkflowStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department: str
    step_order: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class VisitWorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    patient_id: int
    clinical_visit_id: Optional[int] = None
    workflow_type: str
    current_department: str
    status: str
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    started_at: datetime
    steps: List[VisitWorkflowStepResponse] = Field(default_factory=list)


class VisitWorkflowQueueItem(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    clinical_visit_id: Optional[int] = None
    workflow_type: str
    current_department: str
    status: str
    patient_name: str
    patient_age: Optional[int] = None
    patient_phone: Optional[str] = None
    started_at: datetime
    step_status: str
