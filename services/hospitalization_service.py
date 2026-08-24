"""Admission and hospitalization workflow orchestration."""

from __future__ import annotations

from datetime import datetime, date, timedelta
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

import models
from models.user import User
from schemas.hospitalization import (
    AdmissionCreate,
    AdmissionStatusUpdate,
    BedAssignmentRequest,
    HospitalBedCreate,
    HospitalRoomCreate,
    HospitalWardCreate,
    HospitalWardUpdate,
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
    def create_ward(
        db: Session, *, clinic_id: int, payload: HospitalWardCreate, actor: User,
        client_ip: str | None = None,
    ) -> models.HospitalWard:
        ward = models.HospitalWard(
            clinic_id=clinic_id,
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            service_type=payload.service_type,
            location=payload.location,
            notes=payload.notes,
        )
        db.add(ward)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Ward code or name already exists")
        db.refresh(ward)
        log_cis(db, actor=actor, clinic_id=clinic_id, action="create", resource_type="hospital_ward", resource_id=ward.id, client_ip=client_ip)
        return ward

    @staticmethod
    def list_wards(db: Session, *, clinic_id: int) -> list[models.HospitalWard]:
        return db.query(models.HospitalWard).options(joinedload(models.HospitalWard.rooms).joinedload(models.HospitalRoom.beds)).filter(models.HospitalWard.clinic_id == clinic_id).order_by(models.HospitalWard.name).all()

    @staticmethod
    def update_ward(
        db: Session, *, clinic_id: int, ward_id: int, payload: HospitalWardUpdate, actor: User,
        client_ip: str | None = None,
    ) -> models.HospitalWard:
        ward = db.query(models.HospitalWard).filter(models.HospitalWard.id == ward_id, models.HospitalWard.clinic_id == clinic_id).first()
        if not ward:
            raise HTTPException(status_code=404, detail="Ward not found")
        previous_name = ward.name
        for field in ("name", "service_type", "status", "location", "notes"):
            value = getattr(payload, field)
            if value is not None:
                setattr(ward, field, value.strip() if isinstance(value, str) else value)
        if ward.name != previous_name:
            for room in ward.rooms:
                room.ward_name = ward.name
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Ward name already exists")
        db.refresh(ward)
        log_cis(db, actor=actor, clinic_id=clinic_id, action="update", resource_type="hospital_ward", resource_id=ward.id, client_ip=client_ip)
        return ward

    @staticmethod
    def create_room(
        db: Session,
        *,
        clinic_id: int,
        payload: HospitalRoomCreate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.HospitalRoom:
        ward = None
        if payload.ward_id is not None:
            ward = db.query(models.HospitalWard).filter(models.HospitalWard.id == payload.ward_id, models.HospitalWard.clinic_id == clinic_id).first()
            if not ward:
                raise HTTPException(status_code=404, detail="Ward not found")
        ward_name = ward.name if ward else (payload.ward_name or "").strip()
        if ward is None:
            ward = db.query(models.HospitalWard).filter(
                models.HospitalWard.clinic_id == clinic_id,
                models.HospitalWard.name == ward_name,
            ).first()
            if ward is None:
                base_code = "".join(char if char.isalnum() else "-" for char in ward_name.upper()).strip("-")[:24] or "WARD"
                code = base_code
                suffix = 2
                while db.query(models.HospitalWard).filter(models.HospitalWard.clinic_id == clinic_id, models.HospitalWard.code == code).first():
                    code = f"{base_code[:27]}-{suffix}"
                    suffix += 1
                ward = models.HospitalWard(clinic_id=clinic_id, code=code, name=ward_name)
                db.add(ward)
                db.flush()
        existing = (
            db.query(models.HospitalRoom)
            .filter(
                models.HospitalRoom.clinic_id == clinic_id,
                models.HospitalRoom.ward_name == ward_name,
                models.HospitalRoom.room_number == payload.room_number.strip(),
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Room already exists in this ward")
        room = models.HospitalRoom(
            clinic_id=clinic_id,
            ward_id=ward.id,
            ward_name=ward_name,
            room_number=payload.room_number.strip(),
            room_type=payload.room_type,
            capacity=payload.capacity,
            notes=payload.notes,
            isolation_capable=payload.isolation_capable,
            accessible=payload.accessible,
            sex_policy=payload.sex_policy,
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
        bed = models.HospitalBed(
            room_id=room_id,
            bed_number=payload.bed_number.strip(),
            stable_code=f"BED-{clinic_id:03d}-{uuid.uuid4().hex[:10].upper()}",
            accommodation_type=payload.accommodation_type,
            pediatric_suitable=payload.pediatric_suitable or payload.newborn_suitable,
            newborn_suitable=payload.newborn_suitable or payload.accommodation_type == "cradle",
            isolation_suitable=payload.isolation_suitable,
            accessible=payload.accessible,
        )
        db.add(bed)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Bed number already exists in this room")
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
            expected_discharge_at=payload.expected_discharge_at,
            placement_age_group=payload.placement_age_group,
            requires_isolation=payload.requires_isolation,
            requires_accessible=payload.requires_accessible,
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
            admission_type="hospitalization",
            reason=payload.reason,
            diagnosis_summary=payload.diagnosis_summary or consultation.diagnosis,
            attending_clinician_user_id=payload.attending_clinician_user_id,
            notes=payload.notes,
            admitted_by_user_id=actor.id,
            expected_discharge_at=payload.expected_discharge_at,
            placement_age_group=payload.placement_age_group,
            requires_isolation=payload.requires_isolation,
            requires_accessible=payload.requires_accessible,
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
        admission = (
            db.query(models.Admission)
            .filter(models.Admission.id == admission_id, models.Admission.clinic_id == clinic_id)
            .with_for_update()
            .first()
        )
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        if admission.status in ("discharged", "cancelled"):
            raise HTTPException(status_code=400, detail="Admission is closed")
        bed = (
            db.query(models.HospitalBed)
            .join(models.HospitalRoom)
            .filter(
                models.HospitalBed.id == payload.bed_id,
                models.HospitalRoom.clinic_id == clinic_id,
            )
            .with_for_update()
            .first()
        )
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.status == "reserved" and bed.reserved_until and bed.reserved_until <= datetime.utcnow():
            HospitalizationService._transition_bed(db, bed=bed, clinic_id=clinic_id, to_status="available", actor=actor, reason="Reservation expirée")
        if bed.status not in ("available", "reserved"):
            raise HTTPException(status_code=409, detail="Bed is not available")
        if bed.status == "reserved" and bed.reserved_for_admission_id not in (None, admission.id):
            raise HTTPException(status_code=409, detail="Bed is reserved for another admission")
        if payload.expected_bed_version is not None and bed.version != payload.expected_bed_version:
            raise HTTPException(status_code=409, detail="Bed state changed; refresh the ward board")
        mismatches = HospitalizationService._placement_mismatches(admission, bed)
        if mismatches and not payload.suitability_override_reason:
            raise HTTPException(status_code=409, detail={"message": "Bed does not meet placement requirements", "requirements": mismatches})
        if mismatches and actor.role not in ("platform_owner", "platform_admin", "clinic_admin", "admin", "doctor"):
            raise HTTPException(status_code=403, detail="Clinical or admin approval is required for a suitability override")

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
                HospitalizationService._transition_bed(db, bed=old_bed, clinic_id=clinic_id, to_status="cleaning", actor=actor, admission_id=admission.id, reason=payload.transfer_reason or "Transfert")

        new_stay = models.PatientStay(
            admission_id=admission.id,
            bed_id=bed.id,
            transfer_reason=payload.transfer_reason,
            assigned_by_user_id=actor.id,
            is_current=True,
        )
        HospitalizationService._transition_bed(db, bed=bed, clinic_id=clinic_id, to_status="occupied", actor=actor, admission_id=admission.id, reason=payload.suitability_override_reason)
        if admission.status == "pending":
            admission.status = "admitted"
            admission.admitted_at = datetime.utcnow()
        elif admission.status == "admitted":
            admission.status = "transferred" if current_stays else "admitted"
        else:
            admission.status = "transferred" if current_stays else admission.status
        db.add(new_stay)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Bed was allocated by another user; refresh the ward board")
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
                    HospitalizationService._transition_bed(db, bed=bed, clinic_id=clinic_id, to_status="cleaning", actor=actor, admission_id=admission.id, reason="Sortie patient")
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
        reserved = sum(1 for b in beds if b.status == "reserved")
        cleaning = sum(1 for b in beds if b.status == "cleaning")
        unavailable = sum(1 for b in beds if b.status == "unavailable")
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
            "reserved_beds": reserved,
            "cleaning_beds": cleaning,
            "unavailable_beds": unavailable,
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
    def monthly_report(db: Session, *, clinic_id: int, year: int, month: int) -> dict:
        from calendar import monthrange

        from services.clinical_register_utils import patient_snapshot, serialize_admission_row

        start = datetime(year, month, 1)
        end = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        rows = (
            db.query(models.Admission)
            .options(joinedload(models.Admission.patient))
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admitted_at >= start,
                models.Admission.admitted_at <= end,
            )
            .order_by(models.Admission.admitted_at)
            .all()
        )
        register_rows = []
        for idx, adm in enumerate(rows, start=1):
            if not adm.patient:
                continue
            los = None
            if adm.admitted_at and adm.discharged_at:
                los = round((adm.discharged_at - adm.admitted_at).total_seconds() / 86400, 1)
            register_rows.append(
                serialize_admission_row(
                    {
                        "line_number": idx,
                        "admission": adm,
                        "patient": patient_snapshot(
                            adm.patient, adm.admitted_at.date() if adm.admitted_at else date.today()
                        ),
                        "length_of_stay_days": los,
                    }
                )
            )
        discharged = sum(1 for a in rows if a.status == "discharged")
        active_end = sum(1 for a in rows if a.status in ("admitted", "in_care", "transferred"))
        return {
            "year": year,
            "month": month,
            "clinic_id": clinic_id,
            "total_admissions": len(rows),
            "discharges": discharged,
            "still_hospitalized": active_end,
            "register_rows": register_rows,
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
        db: Session, *, clinic_id: int, bed_id: int, status: str, actor: User,
        reason: str | None = None, expected_version: int | None = None,
    ) -> models.HospitalBed:
        bed = (
            db.query(models.HospitalBed)
            .join(models.HospitalRoom)
            .filter(models.HospitalBed.id == bed_id, models.HospitalRoom.clinic_id == clinic_id)
            .with_for_update()
            .first()
        )
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.status == "occupied":
            raise HTTPException(status_code=400, detail="Occupied beds can only be released through transfer or discharge")
        if expected_version is not None and bed.version != expected_version:
            raise HTTPException(status_code=409, detail="Bed state changed; refresh the ward board")
        allowed = {
            "available": {"maintenance", "unavailable"},
            "reserved": {"available", "maintenance", "unavailable"},
            "cleaning": {"available", "maintenance", "unavailable"},
            "maintenance": {"available", "unavailable"},
            "unavailable": {"available", "maintenance"},
        }
        if status != bed.status and status not in allowed.get(bed.status, set()):
            raise HTTPException(status_code=409, detail=f"Invalid bed transition: {bed.status} -> {status}")
        HospitalizationService._transition_bed(db, bed=bed, clinic_id=clinic_id, to_status=status, actor=actor, reason=reason)
        db.commit()
        db.refresh(bed)
        return bed

    @staticmethod
    def reserve_bed(db: Session, *, clinic_id: int, bed_id: int, admission_id: int, reserved_until: datetime, actor: User, expected_version: int | None = None) -> models.HospitalBed:
        if reserved_until <= datetime.utcnow() or reserved_until > datetime.utcnow() + timedelta(hours=48):
            raise HTTPException(status_code=400, detail="Reservation must end within the next 48 hours")
        admission = HospitalizationService._get_admission(db, clinic_id, admission_id)
        bed = db.query(models.HospitalBed).join(models.HospitalRoom).filter(models.HospitalBed.id == bed_id, models.HospitalRoom.clinic_id == clinic_id).with_for_update().first()
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.status != "available":
            raise HTTPException(status_code=409, detail="Bed is not available")
        if expected_version is not None and bed.version != expected_version:
            raise HTTPException(status_code=409, detail="Bed state changed; refresh the ward board")
        mismatches = HospitalizationService._placement_mismatches(admission, bed)
        if mismatches:
            raise HTTPException(status_code=409, detail={"message": "Bed does not meet placement requirements", "requirements": mismatches})
        bed.reserved_for_admission_id = admission.id
        bed.reserved_until = reserved_until
        HospitalizationService._transition_bed(db, bed=bed, clinic_id=clinic_id, to_status="reserved", actor=actor, admission_id=admission.id, reason="Réservation admission")
        db.commit()
        db.refresh(bed)
        return bed

    @staticmethod
    def ward_board(db: Session, *, clinic_id: int) -> dict:
        wards = HospitalizationService.list_wards(db, clinic_id=clinic_id)
        current_stays = db.query(models.PatientStay).join(models.Admission).filter(models.Admission.clinic_id == clinic_id, models.PatientStay.is_current.is_(True)).options(joinedload(models.PatientStay.admission).joinedload(models.Admission.patient)).all()
        stays_by_bed = {stay.bed_id: stay for stay in current_stays}
        result = []
        for ward in wards:
            rooms = []
            for room in sorted(ward.rooms, key=lambda item: item.room_number):
                beds = []
                for bed in sorted(room.beds, key=lambda item: item.bed_number):
                    stay = stays_by_bed.get(bed.id)
                    beds.append({
                        "id": bed.id, "stable_code": bed.stable_code, "bed_number": bed.bed_number,
                        "status": bed.status, "version": bed.version, "accommodation_type": bed.accommodation_type,
                        "pediatric_suitable": bed.pediatric_suitable, "newborn_suitable": bed.newborn_suitable,
                        "isolation_suitable": bed.isolation_suitable, "accessible": bed.accessible,
                        "reserved_for_admission_id": bed.reserved_for_admission_id, "reserved_until": bed.reserved_until,
                        "patient": ({"id": stay.admission.patient_id, "name": _patient_name(stay.admission.patient), "admission_id": stay.admission_id, "admission_number": stay.admission.admission_number, "expected_discharge_at": stay.admission.expected_discharge_at} if stay and stay.admission.patient else None),
                    })
                rooms.append({"id": room.id, "room_number": room.room_number, "room_type": room.room_type, "status": room.status, "beds": beds})
            result.append({"id": ward.id, "code": ward.code, "name": ward.name, "service_type": ward.service_type, "status": ward.status, "location": ward.location, "rooms": rooms})
        return {"summary": HospitalizationService.occupancy_summary(db, clinic_id=clinic_id), "wards": result, "generated_at": datetime.utcnow()}

    @staticmethod
    def _placement_mismatches(admission: models.Admission, bed: models.HospitalBed) -> list[str]:
        mismatches = []
        if admission.placement_age_group == "newborn" and not bed.newborn_suitable:
            mismatches.append("newborn")
        if admission.placement_age_group == "pediatric" and not bed.pediatric_suitable:
            mismatches.append("pediatric")
        if admission.requires_isolation and not bed.isolation_suitable:
            mismatches.append("isolation")
        if admission.requires_accessible and not bed.accessible:
            mismatches.append("accessible")
        return mismatches

    @staticmethod
    def _transition_bed(db: Session, *, bed: models.HospitalBed, clinic_id: int, to_status: str, actor: User, admission_id: int | None = None, reason: str | None = None) -> None:
        old = bed.status
        if old == to_status:
            return
        bed.status = to_status
        bed.status_reason = reason
        bed.version = (bed.version or 0) + 1
        if to_status != "reserved":
            bed.reserved_for_admission_id = None
            bed.reserved_until = None
        if to_status == "available":
            bed.last_cleaned_at = datetime.utcnow()
        db.add(models.BedStatusEvent(clinic_id=clinic_id, bed_id=bed.id, admission_id=admission_id, from_status=old, to_status=to_status, reason=reason, actor_user_id=actor.id))
