"""Resolve which patient records belong to a clinic (cross-clinic isolation)."""

from __future__ import annotations

from sqlalchemy import union
from sqlalchemy.orm import Query, Session

import models


def clinic_patient_ids_query(db: Session, clinic_id: int) -> Query:
    """
    Distinct patient IDs linked to a clinic via appointments, visits, billing,
    admissions, or reception intake audit rows.
    """
    sources = [
        db.query(models.RendezVous.patient_id.label("patient_id")).filter(
            models.RendezVous.clinic_id == clinic_id,
            models.RendezVous.patient_id.isnot(None),
        ),
        db.query(models.ClinicalVisit.patient_id.label("patient_id")).filter(
            models.ClinicalVisit.clinic_id == clinic_id
        ),
        db.query(models.Invoice.patient_id.label("patient_id")).filter(
            models.Invoice.clinic_id == clinic_id
        ),
        db.query(models.Admission.patient_id.label("patient_id")).filter(
            models.Admission.clinic_id == clinic_id
        ),
        db.query(models.ClinicalAuditLog.patient_id.label("patient_id")).filter(
            models.ClinicalAuditLog.clinic_id == clinic_id,
            models.ClinicalAuditLog.resource_type == "patient",
            models.ClinicalAuditLog.patient_id.isnot(None),
        ),
    ]
    linked = union(*sources).subquery()
    return db.query(linked.c.patient_id).distinct()
