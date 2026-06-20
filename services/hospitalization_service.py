"""Admission and hospitalization workflow orchestration."""

from __future__ import annotations

from datetime import datetime, date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from models.user import User
from schemas.hospitalization import (
    AdmissionCreate,
    AdmissionStatusUpdate,
    BedAssignmentRequest,
    HospitalBedCreate,
    HospitalRoomCreate,
)
from services.cis_audit import log_cis


def _patient_name(patient: models.Patient) -> str:
    return f"{patient.first_name} {patient.last_name}".strip()


def _next_admission_number(db: Session, clinic_id: int) -> str:
    count = (
        db.query(models.Admission)
        .filter(models.Admission.clinic_id == clinic_id)
        .count()
    )
    year = datetime.utcnow().year
    return f"ADM-{year}-{clinic_id:03d}-{count + 1:05d}"


class HospitalizationService:
    @staticmethod
    def create_room(
        db: Session,
        *,
        clinic_id: int,
        payload: HospitalRoomCreate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.HospitalRoom:
        existing = (
            db.query(models.HospitalRoom)
            .filter(
                models.HospitalRoom.clinic_id == clinic_id,
                models.HospitalRoom.ward_name == payload.ward_name.strip(),
                models.HospitalRoom.room_number == payload.room_number.strip(),
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Room already exists in this ward")
        room = models.HospitalRoom(
            clinic_id=clinic_id,
            ward_name=payload.ward_name.strip(),
            room_number=payload.room_number.strip(),
            room_type=payload.room_type,
            capacity=payload.capacity,
            notes=payload.notes,
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                action="create",
                resource_type="hospital_room",
                resource_id=room.id,
                client_ip=client_ip,
            )
        return room

    @staticmethod
    def add_bed(
        db: Session,
        *,
        clinic_id: int,
        room_id: int,
        payload: HospitalBedCreate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.HospitalBed:
        room = (
            db.query(models.HospitalRoom)
            .filter(models.HospitalRoom.id == room_id, models.HospitalRoom.clinic_id == clinic_id)
            .first()
        )
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        bed_count = db.query(models.HospitalBed).filter(models.HospitalBed.room_id == room_id).count()
        if bed_count >= room.capacity:
            raise HTTPException(status_code=400, detail="Room at capacity")
        bed = models.HospitalBed(room_id=room_id, bed_number=payload.bed_number.strip())
        db.add(bed)
        db.commit()
        db.refresh(bed)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                action="create",
                resource_type="hospital_bed",
                resource_id=bed.id,
                client_ip=client_ip,
            )
        return bed

    @staticmethod
    def admit_patient(
        db: Session,
        *,
        clinic_id: int,
        payload: AdmissionCreate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Admission:
        if payload.consultation_id:
            return HospitalizationService.admit_from_consultation(
                db, clinic_id=clinic_id, payload=payload, actor=actor, client_ip=client_ip
            )
        from core.tenant import assert_patient_in_clinic

        assert payload.patient_id is not None
        assert_patient_in_clinic(db, patient_id=payload.patient_id, clinic_id=clinic_id)
        existing = (
            db.query(models.Admission)
            .filter(
                models.Admission.patient_id == payload.patient_id,
                models.Admission.clinic_id == clinic_id,
                models.Admission.status.notin_(["discharged", "cancelled"]),
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Patient already has an active admission")
        admission = models.Admission(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            consultation_id=None,
            admission_number=_next_admission_number(db, clinic_id),
            status="pending",
            reason=payload.reason,
            diagnosis_summary=payload.diagnosis_summary,
            attending_clinician_user_id=payload.attending_clinician_user_id,
            notes=payload.notes,
            admitted_by_user_id=actor.id,
        )
        db.add(admission)
        db.commit()
        db.refresh(admission)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            action="create",
            resource_type="admission",
            resource_id=admission.id,
            client_ip=client_ip,
        )
        return admission

    @staticmethod
    def admit_from_consultation(
        db: Session,
        *,
        clinic_id: int,
        payload: AdmissionCreate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Admission:
        consultation = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.id == payload.consultation_id,
                models.ClinicalConsultation.clinic_id == clinic_id,
            )
            .first()
        )
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        if consultation.status not in ("in_progress", "completed"):
            raise HTTPException(status_code=400, detail="Consultation must be active or completed")
        existing = (
            db.query(models.Admission)
            .filter(
                models.Admission.consultation_id == consultation.id,
                models.Admission.status.notin_(["discharged", "cancelled"]),
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Active admission already exists for this consultation")
        admission = models.Admission(
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            consultation_id=consultation.id,
            admission_number=_next_admission_number(db, clinic_id),
            status="pending",
            reason=payload.reason,
            diagnosis_summary=payload.diagnosis_summary or consultation.diagnosis,
            attending_clinician_user_id=payload.attending_clinician_user_id,
            notes=payload.notes,
            admitted_by_user_id=actor.id,
        )
        db.add(admission)
        db.commit()
        db.refresh(admission)
        from services.visit_service import VisitService

        visit = VisitService.ensure_for_consultation(db, consultation)
        VisitService.link_admission(db, visit, admission.id)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            action="create",
            resource_type="admission",
            resource_id=admission.id,
            client_ip=client_ip,
        )
        return admission

    @staticmethod
    def assign_bed(
        db: Session,
        *,
        clinic_id: int,
        admission_id: int,
        payload: BedAssignmentRequest,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Admission:
        admission = HospitalizationService._get_admission(db, clinic_id, admission_id)
        if admission.status in ("discharged", "cancelled"):
            raise HTTPException(status_code=400, detail="Admission is closed")
        bed = (
            db.query(models.HospitalBed)
            .join(models.HospitalRoom)
            .filter(
                models.HospitalBed.id == payload.bed_id,
                models.HospitalRoom.clinic_id == clinic_id,
            )
            .first()
        )
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.status not in ("available", "reserved"):
            raise HTTPException(status_code=409, detail="Bed is not available")

        current_stays = (
            db.query(models.PatientStay)
            .filter(
                models.PatientStay.admission_id == admission.id,
                models.PatientStay.is_current.is_(True),
            )
            .all()
        )
        for stay in current_stays:
            stay.is_current = False
            stay.released_at = datetime.utcnow()
            old_bed = db.query(models.HospitalBed).filter(models.HospitalBed.id == stay.bed_id).first()
            if old_bed:
                old_bed.status = "available"

        new_stay = models.PatientStay(
            admission_id=admission.id,
            bed_id=bed.id,
            transfer_reason=payload.transfer_reason,
            assigned_by_user_id=actor.id,
            is_current=True,
        )
        bed.status = "occupied"
        if admission.status == "pending":
            admission.status = "admitted"
            admission.admitted_at = datetime.utcnow()
        elif admission.status == "admitted":
            admission.status = "transferred" if current_stays else "admitted"
        else:
            admission.status = "transferred" if current_stays else admission.status
        db.add(new_stay)
        db.commit()
        db.refresh(admission)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=admission.patient_id,
            action="assign_bed",
            resource_type="admission",
            resource_id=admission.id,
            client_ip=client_ip,
        )
        return admission

    @staticmethod
    def update_status(
        db: Session,
        *,
        clinic_id: int,
        admission_id: int,
        payload: AdmissionStatusUpdate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Admission:
        admission = HospitalizationService._get_admission(db, clinic_id, admission_id)
        admission.status = payload.status
        if payload.outcome:
            admission.outcome = payload.outcome
        if payload.status == "discharged":
            admission.discharged_at = datetime.utcnow()
            current_stays = (
                db.query(models.PatientStay)
                .filter(
                    models.PatientStay.admission_id == admission.id,
                    models.PatientStay.is_current.is_(True),
                )
                .all()
            )
            for stay in current_stays:
                stay.is_current = False
                stay.released_at = datetime.utcnow()
                bed = db.query(models.HospitalBed).filter(models.HospitalBed.id == stay.bed_id).first()
                if bed:
                    bed.status = "available"
        db.commit()
        db.refresh(admission)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=admission.patient_id,
            action="update_status",
            resource_type="admission",
            resource_id=admission.id,
            client_ip=client_ip,
        )
        return admission

    @staticmethod
    def list_admissions(
        db: Session,
        *,
        clinic_id: int,
        status: str | None = None,
    ) -> list[models.Admission]:
        q = db.query(models.Admission).filter(models.Admission.clinic_id == clinic_id)
        if status:
            q = q.filter(models.Admission.status == status)
        return q.order_by(models.Admission.created_at.desc()).all()

    @staticmethod
    def list_rooms(db: Session, *, clinic_id: int) -> list[models.HospitalRoom]:
        return (
            db.query(models.HospitalRoom)
            .filter(models.HospitalRoom.clinic_id == clinic_id)
            .order_by(models.HospitalRoom.ward_name, models.HospitalRoom.room_number)
            .all()
        )

    @staticmethod
    def list_beds(db: Session, *, clinic_id: int, room_id: int | None = None) -> list[models.HospitalBed]:
        q = (
            db.query(models.HospitalBed)
            .join(models.HospitalRoom)
            .filter(models.HospitalRoom.clinic_id == clinic_id)
        )
        if room_id:
            q = q.filter(models.HospitalBed.room_id == room_id)
        return q.order_by(models.HospitalRoom.ward_name, models.HospitalBed.bed_number).all()

    @staticmethod
    def occupancy_summary(db: Session, *, clinic_id: int) -> dict:
        beds = (
            db.query(models.HospitalBed)
            .join(models.HospitalRoom)
            .filter(models.HospitalRoom.clinic_id == clinic_id)
            .all()
        )
        total = len(beds)
        available = sum(1 for b in beds if b.status == "available")
        occupied = sum(1 for b in beds if b.status == "occupied")
        maintenance = sum(1 for b in beds if b.status == "maintenance")
        active = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.status.in_(["admitted", "in_care", "transferred"]),
            )
            .count()
        )
        pending = (
            db.query(models.Admission)
            .filter(models.Admission.clinic_id == clinic_id, models.Admission.status == "pending")
            .count()
        )
        rate = (occupied / total * 100) if total else 0.0
        return {
            "total_beds": total,
            "available_beds": available,
            "occupied_beds": occupied,
            "maintenance_beds": maintenance,
            "occupancy_rate": round(rate, 1),
            "active_admissions": active,
            "pending_admissions": pending,
        }

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict:
        today = date.today()
        month_start = datetime(today.year, today.month, 1)
        active = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.status.in_(["admitted", "in_care", "transferred"]),
            )
            .count()
        )
        admissions_month = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admitted_at >= month_start,
            )
            .count()
        )
        discharged_rows = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.status == "discharged",
                models.Admission.discharged_at >= month_start,
            )
            .all()
        )
        stays: list[float] = []
        for adm in discharged_rows:
            if adm.admitted_at and adm.discharged_at:
                delta = adm.discharged_at - adm.admitted_at
                stays.append(delta.total_seconds() / 86400)
        avg_stay = round(sum(stays) / len(stays), 1) if stays else 0.0
        return {
            "current_hospitalized": active,
            "admissions_this_month": admissions_month,
            "discharges_this_month": len(discharged_rows),
            "average_length_of_stay_days": avg_stay,
        }

    @staticmethod
    def _get_admission(db: Session, clinic_id: int, admission_id: int) -> models.Admission:
        admission = (
            db.query(models.Admission)
            .filter(models.Admission.id == admission_id, models.Admission.clinic_id == clinic_id)
            .first()
        )
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        return admission

    @staticmethod
    def update_room(
        db: Session,
        *,
        clinic_id: int,
        room_id: int,
        status: str | None = None,
        notes: str | None = None,
        room_type: str | None = None,
    ) -> models.HospitalRoom:
        room = (
            db.query(models.HospitalRoom)
            .filter(models.HospitalRoom.id == room_id, models.HospitalRoom.clinic_id == clinic_id)
            .first()
        )
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        if status:
            room.status = status
        if notes is not None:
            room.notes = notes
        if room_type:
            room.room_type = room_type
        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def update_bed(
        db: Session, *, clinic_id: int, bed_id: int, status: str
    ) -> models.HospitalBed:
        bed = (
            db.query(models.HospitalBed)
            .join(models.HospitalRoom)
            .filter(models.HospitalBed.id == bed_id, models.HospitalRoom.clinic_id == clinic_id)
            .first()
        )
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.status == "occupied" and status == "maintenance":
            raise HTTPException(status_code=400, detail="Cannot maintenance an occupied bed")
        bed.status = status
        db.commit()
        db.refresh(bed)
        return bed
