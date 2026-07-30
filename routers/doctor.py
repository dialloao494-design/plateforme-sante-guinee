# FastAPI router for Doctor CRUD with SQLAlchemy
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models.doctor import Doctor
from models.availability import DoctorAvailability
from schemas.doctor import (
    DoctorCreate,
    DoctorGeoUpdate,
    DoctorResponse,
    DoctorUpdate,
)
from schemas.availability import DoctorAvailabilityCreate, DoctorAvailabilityResponse, DoctorAvailabilityUpdate
from security import get_current_doctor, get_current_admin, require_roles, get_current_user_or_none
from services.availability_service import AvailabilityService
from services.doctor_availability_access import DoctorAvailabilityAccessService
from services.doctor_search import apply_doctor_search_filter
from core.doctor_ownership_policy import DoctorOwnershipPolicy

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)


@router.post("/", response_model=DoctorResponse)
def create_doctor(
    doctor: DoctorCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_doctor),
):
    """Create a new doctor profile for the authenticated doctor user."""
    existing_doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if existing_doctor:
        raise HTTPException(status_code=400, detail="Doctor profile already exists for this user")
    
    new_doctor = Doctor(
        user_id=current_user.id,
        first_name=doctor.first_name,
        last_name=doctor.last_name,
        specialty=doctor.specialty,
        city=doctor.location,
        phone=doctor.phone,
        photo_url=doctor.photo_url,
        consultation_fee=doctor.consultation_fee,
        latitude=doctor.latitude,
        longitude=doctor.longitude,
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    return new_doctor


@router.get("/", response_model=list[DoctorResponse])
def get_doctors(
    db: Session = Depends(get_db),
    specialty: str | None = Query(None, description="Filter by specialty (substring, case-insensitive)"),
    location: str | None = Query(None, description="Filter by city / zone (substring, case-insensitive)"),
    search: str | None = Query(None, description="Search name, specialty, or location"),
):
    q = db.query(Doctor)
    if specialty and specialty.strip().lower() not in {"", "all"}:
        q = q.filter(Doctor.specialty.ilike(f"%{specialty.strip()}%"))
    if location and location.strip().lower() not in {"", "all"}:
        q = q.filter(Doctor.city.ilike(f"%{location.strip()}%"))
    if search and search.strip():
        q = apply_doctor_search_filter(q, search)
    doctors = q.order_by(Doctor.last_name.asc(), Doctor.first_name.asc()).all()
    return doctors


@router.get("/nearby", response_model=list[DoctorResponse])
def get_doctors_nearby(
    lat: float = Query(..., ge=-90, le=90, description="Patient latitude (WGS84)"),
    lon: float = Query(..., ge=-180, le=180, description="Patient longitude (WGS84)"),
    radius_km: float = Query(80.0, gt=0, le=500),
    specialty: str | None = Query(None, description="Filter by specialty (substring)"),
    db: Session = Depends(get_db),
):
    """List doctors with saved practice coordinates within radius, sorted by distance."""
    from services.geo import haversine_km

    q = db.query(Doctor).filter(Doctor.latitude.isnot(None), Doctor.longitude.isnot(None))
    if specialty and specialty.strip().lower() not in {"", "all"}:
        q = q.filter(Doctor.specialty.ilike(f"%{specialty.strip()}%"))
    rows = q.all()
    ranked: list[tuple[float, Doctor]] = []
    for d in rows:
        dist = haversine_km(lat, lon, float(d.latitude), float(d.longitude))
        if dist <= radius_km:
            ranked.append((dist, d))
    ranked.sort(key=lambda t: t[0])
    out: list[DoctorResponse] = []
    for dist, d in ranked:
        base = DoctorResponse.model_validate(d)
        out.append(base.model_copy(update={"distance_km": round(dist, 2)}))
    return out


@router.patch("/me/geo", response_model=DoctorResponse)
def patch_my_practice_geo(
    body: DoctorGeoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_doctor),
):
    """Doctor updates cabinet coordinates (for nearby discovery)."""
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    if body.latitude is not None:
        doctor.latitude = body.latitude
    if body.longitude is not None:
        doctor.longitude = body.longitude
    if body.location is not None:
        doctor.city = body.location.strip()
    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_or_none),
):
    """
    Get detailed information about a specific doctor.
    
    Public endpoint - accessible to patients without authentication.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int,
    doctor_update: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Update doctor profile (Admin only)."""
    DoctorOwnershipPolicy.assert_can_mutate_doctor_resource(
        db,
        target_doctor_id=doctor_id,
        current_user=current_user,
        resource="doctor profile",
    )
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    # Update only provided fields
    if doctor_update.first_name is not None:
        doctor.first_name = doctor_update.first_name
    if doctor_update.last_name is not None:
        doctor.last_name = doctor_update.last_name
    if doctor_update.specialty is not None:
        doctor.specialty = doctor_update.specialty
    if doctor_update.location is not None:
        doctor.city = doctor_update.location
    if doctor_update.phone is not None:
        doctor.phone = doctor_update.phone
    if doctor_update.photo_url is not None:
        doctor.photo_url = doctor_update.photo_url
    if doctor_update.consultation_fee is not None:
        doctor.consultation_fee = doctor_update.consultation_fee
    if doctor_update.latitude is not None:
        doctor.latitude = doctor_update.latitude
    if doctor_update.longitude is not None:
        doctor.longitude = doctor_update.longitude

    db.commit()
    db.refresh(doctor)
    return doctor


@router.delete("/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    DoctorOwnershipPolicy.assert_can_mutate_doctor_resource(
        db,
        target_doctor_id=doctor_id,
        current_user=current_user,
        resource="doctor profile",
    )
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    db.delete(doctor)
    db.commit()
    return {"detail": "Doctor deleted successfully"}


@router.post("/{doctor_id}/availability", response_model=DoctorAvailabilityResponse)
def create_doctor_availability(
    doctor_id: int,
    availability: DoctorAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["platform_admin", "clinic_admin", "admin", "doctor"])),
):
    """Create a working hours availability slot (doctor owns schedule; admin may assist)."""
    return DoctorAvailabilityAccessService.create_slot(
        db, doctor_id=doctor_id, payload=availability, current_user=current_user
    )


@router.get("/{doctor_id}/availability", response_model=list[DoctorAvailabilityResponse])
def get_doctor_availability(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["platform_admin", "clinic_admin", "admin", "doctor", "patient"])),
):
    """Get all active working hours for a doctor."""
    return (
        db.query(DoctorAvailability)
        .filter(DoctorAvailability.doctor_id == doctor_id, DoctorAvailability.is_active == True)
        .order_by(DoctorAvailability.day_of_week)
        .all()
    )


@router.put("/{doctor_id}/availability/{availability_id}", response_model=DoctorAvailabilityResponse)
def update_doctor_availability(
    doctor_id: int,
    availability_id: int,
    availability_update: DoctorAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["platform_admin", "clinic_admin", "admin", "doctor"])),
):
    """Update a doctor's availability slot (ownership enforced)."""
    return DoctorAvailabilityAccessService.update_slot(
        db,
        doctor_id=doctor_id,
        availability_id=availability_id,
        payload=availability_update,
        current_user=current_user,
    )


@router.delete("/{doctor_id}/availability/{availability_id}")
def delete_doctor_availability(
    doctor_id: int,
    availability_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["platform_admin", "clinic_admin", "admin", "doctor"])),
):
    """Delete (deactivate) a doctor's availability slot (ownership enforced)."""
    return DoctorAvailabilityAccessService.deactivate_slot(
        db,
        doctor_id=doctor_id,
        availability_id=availability_id,
        current_user=current_user,
    )


@router.get("/{doctor_id}/schedule")
def get_doctor_schedule(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_or_none),
):
    """Get doctor's complete weekly schedule (working hours).
    
    Returns:
        dict: Schedule for each day (Monday through Sunday)
        Example:
        {
            "Monday": {"start": "09:00", "end": "17:00"},
            "Tuesday": {"start": "09:00", "end": "17:00"},
            ...
        }
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    schedule = AvailabilityService.get_doctor_schedule(doctor_id, db)
    return {
        "doctor_id": doctor_id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "schedule": schedule
    }
