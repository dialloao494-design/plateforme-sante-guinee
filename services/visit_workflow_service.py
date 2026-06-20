"""Patient visit workflow — multi-department queues."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

import models
from models.user import User
from services.visit_service import VisitService

WORKFLOW_STEPS: dict[str, list[str]] = {
    "child": ["reception", "nutrition", "pev", "doctor"],
    "adult_doctor": ["reception", "doctor"],
    "adult_lab": ["reception", "lab"],
    "adult_midwife": ["reception", "midwife"],
    "nursing_visit": ["reception", "nursing"],
}

DEPARTMENT_LABELS = {
    "reception": "Réception",
    "nutrition": "Nutrition",
    "pev": "PEV / Vaccination",
    "doctor": "Médecin",
    "lab": "Laboratoire",
    "midwife": "Sage-femme",
    "nursing": "Soins infirmiers",
}

CHILD_AGE_THRESHOLD = 18


class VisitWorkflowService:
    @staticmethod
    def infer_workflow_type(patient: models.Patient, explicit: str | None) -> str:
        if explicit and explicit in WORKFLOW_STEPS:
            return explicit
        age = patient.age
        if patient.date_of_birth:
            age = (datetime.utcnow().date() - patient.date_of_birth).days // 365
        if age is not None and age < CHILD_AGE_THRESHOLD:
            return "child"
        return "adult_doctor"

    @staticmethod
    def create_visit(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        actor: User,
        workflow_type: str | None = None,
        notes: str | None = None,
    ) -> models.PatientVisitWorkflow:
        patient = (
            db.query(models.Patient)
            .filter(models.Patient.id == patient_id, models.Patient.clinic_id == clinic_id)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        active = (
            db.query(models.PatientVisitWorkflow)
            .filter(
                models.PatientVisitWorkflow.clinic_id == clinic_id,
                models.PatientVisitWorkflow.patient_id == patient_id,
                models.PatientVisitWorkflow.status == "active",
            )
            .first()
        )
        if active:
            raise HTTPException(
                status_code=409,
                detail="Une visite est déjà en cours pour ce patient",
            )

        wf_type = VisitWorkflowService.infer_workflow_type(patient, workflow_type)
        steps = WORKFLOW_STEPS.get(wf_type)
        if not steps:
            raise HTTPException(status_code=400, detail="Type de parcours invalide")

        visit = VisitService.get_or_create_for_patient_clinic(
            db, clinic_id=clinic_id, patient_id=patient_id
        )

        now = datetime.utcnow()
        workflow = models.PatientVisitWorkflow(
            clinic_id=clinic_id,
            patient_id=patient_id,
            clinical_visit_id=visit.id,
            workflow_type=wf_type,
            current_department=steps[0],
            status="active",
            notes=notes,
            created_by_user_id=actor.id,
            started_at=now,
        )
        db.add(workflow)
        db.flush()

        for i, dept in enumerate(steps):
            step_status = "in_progress" if i == 0 else "waiting"
            db.add(
                models.PatientVisitWorkflowStep(
                    workflow_id=workflow.id,
                    department=dept,
                    step_order=i + 1,
                    status=step_status,
                    started_at=now if i == 0 else None,
                )
            )
        db.commit()
        db.refresh(workflow)
        return workflow

    @staticmethod
    def _patient_display(patient: models.Patient) -> dict:
        return {
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_age": patient.age,
            "patient_phone": patient.phone,
        }

    @staticmethod
    def department_queue(
        db: Session, *, clinic_id: int, department: str
    ) -> list[dict]:
        if department not in {d for steps in WORKFLOW_STEPS.values() for d in steps}:
            raise HTTPException(status_code=400, detail="Invalid department")

        rows = (
            db.query(models.PatientVisitWorkflow)
            .options(
                joinedload(models.PatientVisitWorkflow.steps),
                joinedload(models.PatientVisitWorkflow.patient),
            )
            .filter(
                models.PatientVisitWorkflow.clinic_id == clinic_id,
                models.PatientVisitWorkflow.status == "active",
                models.PatientVisitWorkflow.current_department == department,
            )
            .order_by(models.PatientVisitWorkflow.started_at.asc())
            .all()
        )

        items: list[dict] = []
        for wf in rows:
            current_step = next(
                (s for s in wf.steps if s.department == department and s.status != "completed"),
                None,
            )
            if not current_step:
                continue
            patient = wf.patient
            items.append(
                {
                    "id": wf.id,
                    "clinic_id": wf.clinic_id,
                    "patient_id": wf.patient_id,
                    "clinical_visit_id": wf.clinical_visit_id,
                    "workflow_type": wf.workflow_type,
                    "current_department": wf.current_department,
                    "status": wf.status,
                    "started_at": wf.started_at,
                    "step_status": current_step.status,
                    **VisitWorkflowService._patient_display(patient),
                }
            )
        return items

    @staticmethod
    def complete_department_step(
        db: Session,
        *,
        clinic_id: int,
        workflow_id: int,
        department: str,
        actor: User,
    ) -> models.PatientVisitWorkflow:
        workflow = (
            db.query(models.PatientVisitWorkflow)
            .options(
                joinedload(models.PatientVisitWorkflow.steps),
                joinedload(models.PatientVisitWorkflow.patient),
            )
            .filter(
                models.PatientVisitWorkflow.id == workflow_id,
                models.PatientVisitWorkflow.clinic_id == clinic_id,
            )
            .first()
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Visite introuvable")
        if workflow.status != "active":
            raise HTTPException(status_code=400, detail="Cette visite n'est plus active")
        if workflow.current_department != department:
            raise HTTPException(
                status_code=400,
                detail=f"Étape actuelle : {DEPARTMENT_LABELS.get(workflow.current_department, workflow.current_department)}",
            )

        current_step = next(
            (s for s in workflow.steps if s.department == department),
            None,
        )
        if not current_step or current_step.status == "completed":
            raise HTTPException(status_code=400, detail="Étape déjà terminée")

        now = datetime.utcnow()
        current_step.status = "completed"
        current_step.completed_at = now
        current_step.completed_by_user_id = actor.id

        next_step = next(
            (s for s in sorted(workflow.steps, key=lambda x: x.step_order) if s.status == "waiting"),
            None,
        )
        if next_step:
            next_step.status = "in_progress"
            next_step.started_at = now
            workflow.current_department = next_step.department
        else:
            workflow.status = "completed"
            workflow.completed_at = now
            workflow.current_department = department

        workflow.updated_at = now
        db.commit()
        db.refresh(workflow)
        return workflow

    @staticmethod
    def get_workflow(db: Session, *, clinic_id: int, workflow_id: int) -> models.PatientVisitWorkflow:
        workflow = (
            db.query(models.PatientVisitWorkflow)
            .options(
                joinedload(models.PatientVisitWorkflow.steps),
                joinedload(models.PatientVisitWorkflow.patient),
            )
            .filter(
                models.PatientVisitWorkflow.id == workflow_id,
                models.PatientVisitWorkflow.clinic_id == clinic_id,
            )
            .first()
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Visite introuvable")
        return workflow
