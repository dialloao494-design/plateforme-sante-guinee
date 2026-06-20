"""Shared helpers for paper-register row building across clinical modules."""

from __future__ import annotations

from datetime import date

import models


def patient_snapshot(patient: models.Patient, on_date: date | None = None) -> dict:
    on_date = on_date or date.today()
    age_display = None
    if patient.date_of_birth:
        total_days = max(0, (on_date - patient.date_of_birth).days)
        months = total_days // 30
        days = total_days % 30
        if months < 24:
            age_display = f"{months} mois {days} j"
        else:
            years = months // 12
            rem = months % 12
            age_display = f"{years} an(s) {rem} mois"
    elif patient.age is not None:
        age_display = f"{patient.age} an(s)"
    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "gender": patient.gender,
        "date_of_birth": patient.date_of_birth,
        "age_display": age_display,
        "mother_or_guardian": patient.emergency_contact,
        "address": patient.address,
        "phone": patient.phone,
    }


def wrap_register_rows(records: list, *, patient_attr: str = "patient", on_date_attr: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for idx, rec in enumerate(records, start=1):
        patient = getattr(rec, patient_attr, None) if patient_attr else None
        if not patient:
            continue
        on_date = getattr(rec, on_date_attr) if on_date_attr and hasattr(rec, on_date_attr) else None
        if isinstance(on_date, date):
            snap_date = on_date
        else:
            snap_date = on_date.date() if on_date is not None and hasattr(on_date, "date") else date.today()
        rows.append(
            {
                "line_number": idx,
                "record": rec,
                "patient": patient_snapshot(patient, snap_date),
            }
        )
    return rows


def serialize_row(entry: dict, record_fields: list[str]) -> dict:
    rec = entry.get("record")
    payload = {f: getattr(rec, f, None) for f in record_fields} if rec else {}
    for k, v in list(payload.items()):
        if hasattr(v, "isoformat"):
            payload[k] = v.isoformat()
    return {
        "line_number": entry.get("line_number"),
        "patient": entry.get("patient"),
        "record": payload,
    }


def serialize_admission_row(entry: dict) -> dict:
    adm = entry.get("admission")
    if not adm:
        return entry
    payload = {
        "id": adm.id,
        "admission_number": adm.admission_number,
        "admitted_at": adm.admitted_at.isoformat() if adm.admitted_at else None,
        "discharged_at": adm.discharged_at.isoformat() if adm.discharged_at else None,
        "diagnosis_summary": adm.diagnosis_summary,
        "reason": adm.reason,
        "status": adm.status,
        "outcome": adm.outcome,
        "notes": adm.notes,
    }
    return {
        "line_number": entry.get("line_number"),
        "patient": entry.get("patient"),
        "length_of_stay_days": entry.get("length_of_stay_days"),
        "admission": payload,
    }
