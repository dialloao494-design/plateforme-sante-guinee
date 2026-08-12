from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import get_db
from core.patient_ownership_policy import PatientOwnershipPolicy
from core.roles import PLATFORM_SCOPE_ROLES, user_has_any_role
from core.tenant import is_platform_admin, user_clinic_id
from security import get_current_admin, require_roles
from services.patient_record_service import PatientRecordService

router = APIRouter(prefix="/patients", tags=["Patients"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _doctor_for_user(db: Session, user_id: int) -> models.Doctor | None:
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def _assert_doctor_can_access_patient(db: Session, current_user, patient_id: int) -> None:
    doctor = _doctor_for_user(db, current_user.id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    linked = (
        db.query(models.RendezVous)
        .filter(
            models.RendezVous.doctor_id == doctor.id,
            models.RendezVous.patient_id == patient_id,
        )
        .first()
    )
    if not linked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )


@router.get("/account-candidates")
def search_patient_account_candidates(
    q: str = Query("", min_length=0, max_length=120),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Search patient-role accounts in the administrator's clinic for safe linking.

    Returns identity fields (never passwords) so staff can confirm the right
    account instead of typing a raw numeric user id.
    """
    clinic_id = None if is_platform_admin(current_user) else user_clinic_id(current_user, db)
    if not is_platform_admin(current_user) and clinic_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    query = db.query(models.User).filter(models.User.role == "patient", models.User.is_active.is_(True))
    if clinic_id is not None:
        query = query.filter(models.User.clinic_id == clinic_id)

    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        # Match email; numeric terms also match id for recovery workflows.
        if term.isdigit():
            query = query.filter(
                (models.User.email.ilike(like)) | (models.User.id == int(term))
            )
        else:
            query = query.filter(models.User.email.ilike(like))

    # Prefer accounts not already linked to a patient record.
    linked_ids = {
        row[0]
        for row in db.query(models.Patient.user_id)
        .filter(models.Patient.user_id.isnot(None))
        .all()
    }
    users = query.order_by(models.User.id.desc()).limit(limit * 3).all()
    results = []
    for user in users:
        already_linked = user.id in linked_ids
        results.append(
            {
                "id": user.id,
                "email": user.email,
                "clinic_id": user.clinic_id,
                "already_linked": already_linked,
            }
        )
        if len(results) >= limit:
            break
    return results


def _validate_patient_user_link(
    db,
    *,
    user_id: int | None,
    clinic_id: int | None,
    allow_platform: bool,
) -> int | None:
    """Ensure linked account exists, is a patient, clinic-compatible, and unused."""
    if user_id is None:
        return None
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user not found")
    if not target.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user is inactive")
    role = (target.role or "").strip().lower()
    if role != "patient":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linked account must have the patient role",
        )
    target_clinic = getattr(target, "clinic_id", None)
    if clinic_id is not None and target_clinic is not None and int(target_clinic) != int(clinic_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linked account belongs to another clinic",
        )
    if clinic_id is not None and target_clinic is None and not allow_platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linked account has no clinic assignment",
        )
    existing = (
        db.query(models.Patient)
        .filter(models.Patient.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account is already linked to another patient profile",
        )
    return user_id


@router.post("/", response_model=schemas.PatientResponse)
def create_patient(
    patient: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    clinic_id = PatientOwnershipPolicy.resolve_create_clinic_id(db, current_user)

    linked_user_id = patient.user_id
    if linked_user_id is not None:
        PatientOwnershipPolicy.assert_linked_user_for_clinic(
            db,
            user_id=linked_user_id,
            clinic_id=clinic_id,
            current_user=current_user,
        )
        existing = (
            db.query(models.Patient).filter(models.Patient.user_id == linked_user_id).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A patient record is already linked to this account",
            )
    elif not is_platform_admin(current_user):
        # Clinic admins must select a verified account — raw/missing links are unsafe.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient account selection is required",
        )

    new_patient = models.Patient(
        user_id=linked_user_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        age=patient.age,
        gender=patient.gender,
        clinic_id=clinic_id,
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    from services.medical_history_service import ensure_medical_record

    ensure_medical_record(db, new_patient.id)
    return new_patient


@router.get("/", response_model=List[schemas.PatientResponse])
def get_patients(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["doctor", "admin", "platform_admin", "clinic_admin", "platform_owner"])),
):
    if user_has_any_role(current_user.role, PLATFORM_SCOPE_ROLES):
        return db.query(models.Patient).all()

    if current_user.role in ("clinic_admin", "admin"):
        cid = user_clinic_id(current_user, db)
        if not cid:
            return []
        return db.query(models.Patient).filter(models.Patient.clinic_id == cid).all()

    doctor = _doctor_for_user(db, current_user.id)
    if not doctor:
        return []

    # Prefer clinic-scoped list when doctor is assigned to a clinic
    if doctor.clinic_id:
        return (
            db.query(models.Patient)
            .filter(models.Patient.clinic_id == doctor.clinic_id, models.Patient.is_archived.is_(False))
            .all()
        )

    patient_ids = [
        row[0]
        for row in db.query(models.RendezVous.patient_id)
        .filter(models.RendezVous.doctor_id == doctor.id)
        .distinct()
        .all()
    ]
    if not patient_ids:
        return []
    return db.query(models.Patient).filter(models.Patient.id.in_(patient_ids)).all()


@router.get("/linkable-accounts")
def list_linkable_patient_accounts(
    q: str = "",
    limit: int = 20,
    clinic_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Search unlinked patient-role user accounts for clinic-safe patient linking.

    Removes the need for operators to type raw numeric user IDs.
    """
    query = (q or "").strip()
    if len(query) < 2:
        return []
    try:
        limit = max(1, min(int(limit or 20), 50))
    except (TypeError, ValueError):
        limit = 20

    actor_clinic = None if is_platform_admin(current_user) else user_clinic_id(current_user, db)
    if not is_platform_admin(current_user) and actor_clinic is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    scope_clinic = actor_clinic
    if is_platform_admin(current_user) and clinic_id is not None:
        scope_clinic = int(clinic_id)

    linked_ids = {
        row[0]
        for row in db.query(models.Patient.user_id)
        .filter(models.Patient.user_id.isnot(None))
        .all()
    }

    users_q = db.query(models.User).filter(
        models.User.is_active.is_(True),
        models.User.role == "patient",
    )
    if scope_clinic is not None:
        users_q = users_q.filter(models.User.clinic_id == scope_clinic)

    # Match email substring or exact numeric id.
    if query.isdigit():
        users_q = users_q.filter(
            (models.User.id == int(query)) | models.User.email.ilike(f"%{query}%")
        )
    else:
        users_q = users_q.filter(models.User.email.ilike(f"%{query}%"))

    rows = users_q.order_by(models.User.email.asc()).limit(limit * 3).all()
    results = []
    for user in rows:
        if user.id in linked_ids:
            continue
        results.append(
            {
                "id": user.id,
                "email": user.email,
                "clinic_id": getattr(user, "clinic_id", None),
            }
        )
        if len(results) >= limit:
            break
    return results


@router.get("/me", response_model=schemas.PatientResponse)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["patient"])),
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = models.Patient(
            user_id=current_user.id,
            first_name="Patient",
            last_name=f"User{current_user.id}",
            age=0,
            gender="unknown",
            clinic_id=current_user.clinic_id,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    else:
        changed = False
        if patient.first_name is None:
            patient.first_name = "Patient"
            changed = True
        if patient.last_name is None:
            patient.last_name = f"User{current_user.id}"
            changed = True
        if patient.age is None:
            patient.age = 0
            changed = True
        if patient.gender is None:
            patient.gender = "unknown"
            changed = True
        if changed:
            db.commit()
            db.refresh(patient)
    from services.medical_history_service import ensure_medical_record

    ensure_medical_record(db, patient.id)
    return patient


@router.get("/{patient_id}", response_model=schemas.PatientResponse)
def get_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["platform_admin", "clinic_admin", "admin", "doctor", "patient"])),
):
    return PatientRecordService.get_patient_detail(
        db, patient_id, current_user, client_ip=_client_ip(request)
    )


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    PatientOwnershipPolicy.assert_can_mutate_patient(db, current_user, patient)
    has_clinical = (
        db.query(models.ClinicalConsultation)
        .filter(models.ClinicalConsultation.patient_id == patient_id)
        .first()
    )
    if has_clinical:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete patient with clinical history. Archive only.",
        )
    patient.is_archived = True
    patient.archived_at = datetime.utcnow()
    db.commit()
    return {"detail": "Patient archived successfully"}


@router.put("/{patient_id}", response_model=schemas.PatientResponse)
def update_patient(
    patient_id: int,
    patient_update: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "clinic_admin", "platform_admin", "platform_owner", "doctor"])),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if current_user.role == "doctor":
        _assert_doctor_can_access_patient(db, current_user, patient_id)
        patient.first_name = patient_update.first_name
        patient.last_name = patient_update.last_name
        patient.age = patient_update.age
        patient.gender = patient_update.gender
    else:
        PatientOwnershipPolicy.assert_can_mutate_patient(db, current_user, patient)
        # Do not allow arbitrary user_id mass-assignment (account hijack / cross-tenant link).
        patient.first_name = patient_update.first_name
        patient.last_name = patient_update.last_name
        patient.age = patient_update.age
        patient.gender = patient_update.gender
        if patient_update.user_id is not None and patient_update.user_id != patient.user_id:
            PatientOwnershipPolicy.assert_can_relink_user(
                db,
                current_user=current_user,
                patient=patient,
                new_user_id=patient_update.user_id,
            )
            patient.user_id = patient_update.user_id

    db.commit()
    db.refresh(patient)
    return patient
