"""Server-derived clinic readiness and resumable onboarding state."""

from __future__ import annotations

import json
from datetime import datetime

import models
from sqlalchemy.orm import Session

ALLOWED_MODULES = {
    "reception", "billing", "consultation", "laboratory", "pharmacy",
    "hospitalization", "nursing", "pev", "nutrition",
}
ALLOWED_PAYMENT_METHODS = {"cash", "orange_money", "mobile_money", "transfer", "insurance"}
ALLOWED_RECEIPT_FORMATS = {"a4", "thermal"}

DEFAULT_CONFIG = {
    "enabled_modules": ["reception", "billing"],
    "payment_methods": ["cash"],
    "receipt_format": "a4",
    "printing_tested": False,
    "offline_workstation_tested": False,
    "test_journey_completed": False,
    "current_step": "identity",
}


def _config(clinic: models.Clinic) -> dict:
    try:
        stored = json.loads(clinic.onboarding_config_json or "{}")
    except (TypeError, ValueError):
        stored = {}
    config = {**DEFAULT_CONFIG, **stored}
    config["enabled_modules"] = [value for value in config["enabled_modules"] if value in ALLOWED_MODULES]
    config["payment_methods"] = [value for value in config["payment_methods"] if value in ALLOWED_PAYMENT_METHODS]
    return config


def _item(key: str, label: str, complete: bool, detail: str, target: str, blocking: bool = True) -> dict:
    return {"key": key, "label": label, "complete": complete, "blocking": blocking, "detail": detail, "target": target}


def readiness(db: Session, clinic: models.Clinic) -> dict:
    config = _config(clinic)
    staff_count = db.query(models.User).filter(
        models.User.clinic_id == clinic.id,
        models.User.is_active.is_(True),
        models.User.role.notin_(("clinic_admin", "admin")),
    ).count()
    needs_beds = "hospitalization" in config["enabled_modules"]
    bed_count = (
        db.query(models.HospitalBed)
        .join(models.HospitalRoom)
        .filter(models.HospitalRoom.clinic_id == clinic.id, models.HospitalRoom.status == "active")
        .count()
    ) if needs_beds else 0
    identity_complete = all(str(value or "").strip() for value in (clinic.name, clinic.address, clinic.city, clinic.phone))
    checklist = [
        _item("identity", "Identité et coordonnées", identity_complete, "Nom, adresse, ville et téléphone de la clinique.", "identity"),
        _item("modules", "Services activés", bool(config["enabled_modules"]), "Choisissez uniquement les espaces réellement utilisés.", "modules"),
        _item("staff", "Équipe opérationnelle", staff_count > 0, f"{staff_count} compte(s) personnel actif(s).", "staff"),
        _item("payments", "Paiements et reçu", bool(config["payment_methods"]), "Modes de paiement et format du reçu.", "payments"),
        _item("capacity", "Capacité d'hospitalisation", (not needs_beds) or bed_count > 0, "Non requis" if not needs_beds else f"{bed_count} lit(s) configuré(s).", "capacity"),
        _item("printing", "Impression vérifiée", bool(config["printing_tested"]), "Imprimez un reçu de test sur le poste d'accueil.", "verification"),
        _item("offline", "Poste hors ligne vérifié", bool(config["offline_workstation_tested"]), "Testez ouverture, saisie, facture et synchronisation.", "verification"),
        _item("journey", "Parcours patient test terminé", bool(config["test_journey_completed"]), "Patient test : accueil, admission, facture et paiement.", "verification"),
    ]
    complete = sum(1 for item in checklist if item["complete"])
    operational = all(item["complete"] for item in checklist if item["blocking"])
    if operational and clinic.onboarding_completed_at is None:
        clinic.onboarding_completed_at = datetime.utcnow()
    elif not operational and clinic.onboarding_completed_at is not None:
        clinic.onboarding_completed_at = None
    db.flush()
    return {
        "clinic_id": clinic.id,
        "clinic_name": clinic.name,
        "identity": {"name": clinic.name, "address": clinic.address or "", "city": clinic.city or "", "phone": clinic.phone or "", "email": clinic.email or ""},
        "configuration": config,
        "checklist": checklist,
        "completed_count": complete,
        "total_count": len(checklist),
        "percent": round(complete / len(checklist) * 100),
        "is_operational": operational,
        "current_step": config.get("current_step") or next((item["target"] for item in checklist if not item["complete"]), "verification"),
        "completed_at": clinic.onboarding_completed_at,
    }


def update_onboarding(db: Session, clinic: models.Clinic, changes: dict) -> dict:
    config = _config(clinic)
    for field in ("name", "address", "city", "phone", "email"):
        if field in changes and changes[field] is not None:
            setattr(clinic, field, changes[field].strip())
    if changes.get("enabled_modules") is not None:
        unknown = set(changes["enabled_modules"]) - ALLOWED_MODULES
        if unknown:
            raise ValueError(f"Modules inconnus: {', '.join(sorted(unknown))}")
        config["enabled_modules"] = list(dict.fromkeys(changes["enabled_modules"]))
    if changes.get("payment_methods") is not None:
        unknown = set(changes["payment_methods"]) - ALLOWED_PAYMENT_METHODS
        if unknown:
            raise ValueError(f"Modes de paiement inconnus: {', '.join(sorted(unknown))}")
        config["payment_methods"] = list(dict.fromkeys(changes["payment_methods"]))
    if changes.get("receipt_format") is not None:
        if changes["receipt_format"] not in ALLOWED_RECEIPT_FORMATS:
            raise ValueError("Format de reçu inconnu")
        config["receipt_format"] = changes["receipt_format"]
    for field in ("printing_tested", "offline_workstation_tested", "test_journey_completed", "current_step"):
        if changes.get(field) is not None:
            config[field] = changes[field]
    clinic.onboarding_config_json = json.dumps(config, ensure_ascii=False)
    clinic.updated_at = datetime.utcnow()
    db.add(clinic)
    result = readiness(db, clinic)
    db.commit()
    return result
