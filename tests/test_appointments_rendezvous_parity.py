"""H29 — /appointments (canonical) and /rendezvous (legacy) share RBAC + payment policy."""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

import models
from core.provisioning_context import provisioning_channel
from core.roles import effective_role
from routers import appointments as appointments_router
from routers import rendezvous as rendezvous_router
from security import hash_password


def _mk_clinic(db):
    clinic = models.Clinic(name="Parity Clinic", city="Conakry", is_active=True)
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic


def _mk_user(db, *, email, role, clinic_id=None, password="StrongPass12!"):
    with provisioning_channel("test_fixture"):
        user = models.User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            clinic_id=clinic_id,
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _mk_patient(db, user, clinic_id):
    patient = models.Patient(
        user_id=user.id,
        clinic_id=clinic_id,
        first_name="Awa",
        last_name="Diallo",
        age=30,
        gender="F",
        patient_number=f"PAR-{user.id}",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _mk_doctor(db, user, clinic_id):
    doctor = models.Doctor(
        user_id=user.id,
        clinic_id=clinic_id,
        first_name="Dr",
        last_name="Camara",
        specialty="Médecine générale",
        city="Conakry",
        phone="620000000",
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def _mk_rdv(db, *, patient_id, doctor_id, clinic_id):
    rdv = models.RendezVous(
        patient_id=patient_id,
        doctor_id=doctor_id,
        clinic_id=clinic_id,
        date=datetime.utcnow() + timedelta(days=2),
        status="pending",
        payment_status="unpaid",
    )
    db.add(rdv)
    db.commit()
    db.refresh(rdv)
    return rdv


def test_rendezvous_access_uses_effective_role_like_appointments(db_session):
    clinic_a = _mk_clinic(db_session)
    clinic_b = _mk_clinic(db_session)
    admin_a = _mk_user(db_session, email="admin-a@parity.local", role="admin", clinic_id=clinic_a.id)
    patient_u = _mk_user(db_session, email="pat@parity.local", role="patient", clinic_id=clinic_a.id)
    doctor_u = _mk_user(db_session, email="doc@parity.local", role="doctor", clinic_id=clinic_a.id)
    patient = _mk_patient(db_session, patient_u, clinic_a.id)
    doctor = _mk_doctor(db_session, doctor_u, clinic_a.id)
    rdv = _mk_rdv(db_session, patient_id=patient.id, doctor_id=doctor.id, clinic_id=clinic_a.id)

    # Same-clinic admin allowed on both surfaces
    appointments_router._assert_can_access_appointment(db_session, rdv, admin_a)
    rendezvous_router._assert_can_access_appointment(db_session, rdv, admin_a)

    # Cross-clinic admin denied on both
    admin_b = _mk_user(db_session, email="admin-b@parity.local", role="admin", clinic_id=clinic_b.id)

    with pytest.raises(HTTPException) as e1:
        appointments_router._assert_can_access_appointment(db_session, rdv, admin_b)
    with pytest.raises(HTTPException) as e2:
        rendezvous_router._assert_can_access_appointment(db_session, rdv, admin_b)
    assert e1.value.status_code == 403
    assert e2.value.status_code == 403

    # Legacy casing: both helpers normalize via effective_role
    class _LegacyAdmin:
        id = admin_b.id
        role = "Admin"
        clinic_id = clinic_b.id

    assert effective_role(_LegacyAdmin.role) == "admin"
    with pytest.raises(HTTPException):
        rendezvous_router._assert_can_access_appointment(db_session, rdv, _LegacyAdmin())
    with pytest.raises(HTTPException):
        appointments_router._assert_can_access_appointment(db_session, rdv, _LegacyAdmin())


def test_legacy_rendezvous_prefix_documented_as_alias():
    assert appointments_router.router.prefix == "/appointments"
    assert rendezvous_router.router.prefix == "/rendezvous"
    assert "legacy" in (rendezvous_router.router.tags[0] or "").lower()
