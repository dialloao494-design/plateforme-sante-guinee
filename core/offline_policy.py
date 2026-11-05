"""Reject writes originating before a clinic reset, including legacy outboxes."""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session


def enforce_offline_epoch(request: Request, user, db: Session) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    if not request.url.path.startswith(("/clinical/", "/api/clinical/")):
        return
    from core.tenant import user_clinic_id
    from models.clinic import Clinic
    from services.platform_admin_service import clinic_offline_policy
    clinic_id = user_clinic_id(user, db)
    if not clinic_id:
        return
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        return
    current = clinic_offline_policy(clinic)["offline_data_epoch"]
    try:
        supplied = int(request.headers.get("X-Offline-Data-Epoch", "1"))
    except (TypeError, ValueError):
        supplied = 0
    if supplied != current:
        raise HTTPException(status_code=409, detail={
            "code": "offline_epoch_mismatch",
            "message": "La clinique a été remise à zéro. Actualisez votre session; exportez les anciennes opérations sans les renvoyer.",
            "offline_data_epoch": current,
        })
