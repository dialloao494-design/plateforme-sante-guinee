"""Patient visit workflow queues — shared across department dashboards."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.clinical_access import assert_role, resolve_clinic_for_user
from database import get_db
from models.user import User
from schemas.visit_workflow import (
    VisitWorkflowCreate,
    VisitWorkflowQueueItem,
    VisitWorkflowResponse,
    VisitWorkflowStepResponse,
)
from security import get_current_user
from services.visit_workflow_service import DEPARTMENT_LABELS, VisitWorkflowService

router = APIRouter(prefix="/clinical/workflow", tags=["Visit Workflow"])

RECEPTION_ROLES = ("receptionist", "cashier", "clinic_admin", "admin")
NUTRITION_ROLES = ("nutritionist", "midwife", "clinic_admin", "admin")
PEV_ROLES = ("midwife", "receptionist", "clinic_admin", "admin")
DOCTOR_ROLES = ("doctor", "clinic_admin", "admin")
LAB_ROLES = ("lab_technician", "clinic_admin", "admin")
MIDWIFE_ROLES = ("midwife", "clinic_admin", "admin")
NURSING_ROLES = ("nurse", "midwife", "clinic_admin", "admin", "receptionist", "doctor")
READ_ROLES = RECEPTION_ROLES + NUTRITION_ROLES + PEV_ROLES + DOCTOR_ROLES + LAB_ROLES + MIDWIFE_ROLES + NURSING_ROLES

DEPARTMENT_ACCESS = {
    "reception": RECEPTION_ROLES,
    "nutrition": NUTRITION_ROLES,
    "pev": PEV_ROLES,
    "doctor": DOCTOR_ROLES,
    "lab": LAB_ROLES,
    "midwife": MIDWIFE_ROLES,
    "nursing": NURSING_ROLES,
}


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    assert_role(user, allowed)


def _workflow_response(wf) -> VisitWorkflowResponse:
    patient = wf.patient
    name = None
    age = None
    if patient:
        name = f"{patient.first_name} {patient.last_name}".strip()
        age = patient.age
    return VisitWorkflowResponse(
        id=wf.id,
        clinic_id=wf.clinic_id,
        patient_id=wf.patient_id,
        clinical_visit_id=wf.clinical_visit_id,
        workflow_type=wf.workflow_type,
        current_department=wf.current_department,
        status=wf.status,
        patient_name=name,
        patient_age=age,
        started_at=wf.started_at,
        steps=[
            VisitWorkflowStepResponse(
                id=s.id,
                department=s.department,
                step_order=s.step_order,
                status=s.status,
                started_at=s.started_at,
                completed_at=s.completed_at,
            )
            for s in sorted(wf.steps, key=lambda x: x.step_order)
        ],
    )


@router.post("/visits", response_model=VisitWorkflowResponse, status_code=status.HTTP_201_CREATED)
def start_visit(
    body: VisitWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, RECEPTION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    wf = VisitWorkflowService.create_visit(
        db,
        clinic_id=clinic.id,
        patient_id=body.patient_id,
        actor=current_user,
        workflow_type=body.workflow_type,
        notes=body.notes,
    )
    wf = VisitWorkflowService.get_workflow(db, clinic_id=clinic.id, workflow_id=wf.id)
    return _workflow_response(wf)


@router.get("/queue/{department}", response_model=List[VisitWorkflowQueueItem])
def department_queue(
    department: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dept = department.strip().lower()
    allowed = DEPARTMENT_ACCESS.get(dept)
    if not allowed:
        raise HTTPException(status_code=404, detail="Unknown department")
    _require_role(current_user, allowed)
    clinic = resolve_clinic_for_user(db, current_user)
    items = VisitWorkflowService.department_queue(db, clinic_id=clinic.id, department=dept)
    return [VisitWorkflowQueueItem(**item) for item in items]


@router.post("/visits/{workflow_id}/complete/{department}", response_model=VisitWorkflowResponse)
def complete_step(
    workflow_id: int,
    department: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dept = department.strip().lower()
    allowed = DEPARTMENT_ACCESS.get(dept)
    if not allowed:
        raise HTTPException(status_code=404, detail="Unknown department")
    _require_role(current_user, allowed)
    clinic = resolve_clinic_for_user(db, current_user)
    wf = VisitWorkflowService.complete_department_step(
        db,
        clinic_id=clinic.id,
        workflow_id=workflow_id,
        department=dept,
        actor=current_user,
    )
    wf = VisitWorkflowService.get_workflow(db, clinic_id=clinic.id, workflow_id=wf.id)
    return _workflow_response(wf)


@router.get("/visits/{workflow_id}", response_model=VisitWorkflowResponse)
def get_visit(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    wf = VisitWorkflowService.get_workflow(db, clinic_id=clinic.id, workflow_id=workflow_id)
    return _workflow_response(wf)


@router.get("/departments")
def list_departments():
    return [{"code": k, "label": v} for k, v in DEPARTMENT_LABELS.items()]
