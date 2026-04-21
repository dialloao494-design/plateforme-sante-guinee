# FastAPI router for Doctor CRUD with SQLAlchemy
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.doctor import Doctor
from models.availability import DoctorAvailability
from schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from schemas.availability import DoctorAvailabilityCreate, DoctorAvailabilityResponse, DoctorAvailabilityUpdate
from security import get_current_doctor, get_current_admin, require_roles, get_current_user_or_none
from services.availability_service import AvailabilityService

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
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    return new_doctor


@router.get("/", response_model=list[DoctorResponse])
def get_doctors(db: Session = Depends(get_db)):
    doctors = db.query(Doctor).all()
    print("DOCTORS:", doctors)
    return doctors


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
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
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
    
    db.commit()
    db.refresh(doctor)
    return doctor


@router.delete("/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    db.delete(doctor)
    db.commit()
    return {"detail": "Doctor deleted successfully"}


@router.post("/{doctor_id}/availability", response_model=DoctorAvailabilityResponse)
def create_doctor_availability(
    doctor_id: int,
    availability: DoctorAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor"])),
):
    """Create a working hours availability slot for a doctor.
    
    Args:
        day_of_week: 0=Monday, 1=Tuesday, ..., 6=Sunday
        start_time: Working hours start time (e.g., 09:00)
        end_time: Working hours end time (e.g., 17:00)
    """
    if doctor_id != availability.doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID mismatch")

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Check if slot already exists for this day
    existing = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.day_of_week == availability.day_of_week,
            DoctorAvailability.is_active == True,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Doctor already has an availability slot for day {availability.day_of_week}"
        )

    new_slot = DoctorAvailability(
        doctor_id=doctor_id,
        day_of_week=availability.day_of_week,
        start_time=availability.start_time,
        end_time=availability.end_time,
    )
    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)
    return new_slot


@router.get("/{doctor_id}/availability", response_model=list[DoctorAvailabilityResponse])
def get_doctor_availability(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
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
    current_user=Depends(require_roles(["admin", "doctor"])),
):
    """Update a doctor's availability slot."""
    slot = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.id == availability_id,
        )
        .first()
    )

    if not slot:
        raise HTTPException(status_code=404, detail="Availability slot not found")

    # Update only provided fields
    if availability_update.day_of_week is not None:
        # Check if another slot exists for this day
        existing = (
            db.query(DoctorAvailability)
            .filter(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.day_of_week == availability_update.day_of_week,
                DoctorAvailability.id != availability_id,
                DoctorAvailability.is_active == True,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Slot already exists for this day")
        slot.day_of_week = availability_update.day_of_week

    if availability_update.start_time is not None:
        slot.start_time = availability_update.start_time

    if availability_update.end_time is not None:
        slot.end_time = availability_update.end_time

    if availability_update.is_active is not None:
        slot.is_active = availability_update.is_active

    # Validate times
    if slot.end_time <= slot.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/{doctor_id}/availability/{availability_id}")
def delete_doctor_availability(
    doctor_id: int,
    availability_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor"])),
):
    """Delete (deactivate) a doctor's availability slot."""
    slot = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.id == availability_id,
        )
        .first()
    )

    if not slot:
        raise HTTPException(status_code=404, detail="Availability slot not found")

    slot.is_active = False
    db.commit()
    return {"detail": "Availability slot disabled"}


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


