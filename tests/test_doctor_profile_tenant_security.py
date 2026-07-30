"""Tenant isolation for legacy doctor profile administration routes."""

from __future__ import annotations

import uuid

import models
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password
from services.user_provisioning import register_public_user


def _headers(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "session_version": user.session_version,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_clinic_admin_cannot_update_or_delete_other_clinic_doctor(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    clinic_a = models.Clinic(name=f"Clinic A {suffix}", city="Conakry")
    clinic_b = models.Clinic(name=f"Clinic B {suffix}", city="Conakry")
    db_session.add_all([clinic_a, clinic_b])
    db_session.commit()

    with provisioning_channel("test_fixture"):
        admin = models.User(
            email=f"clinic.admin.{suffix}@test.gn",
            hashed_password=hash_password("AdminPass12!"),
            role="clinic_admin",
            clinic_id=clinic_a.id,
        )
        db_session.add(admin)
        db_session.commit()

    doctor_user = register_public_user(
        db_session,
        email=f"doctor.tenant.{suffix}@test.gn",
        password="DoctorPass12!",
        role="doctor",
    ).user
    doctor = db_session.query(models.Doctor).filter(models.Doctor.user_id == doctor_user.id).one()
    doctor.clinic_id = clinic_b.id
    doctor_user.clinic_id = clinic_b.id
    db_session.commit()

    update = client.put(
        f"/doctors/{doctor.id}",
        json={"specialty": "Cardiologie"},
        headers=_headers(admin),
    )
    delete = client.delete(f"/doctors/{doctor.id}", headers=_headers(admin))

    assert update.status_code == 403
    assert delete.status_code == 403
    db_session.refresh(doctor)
    assert doctor.specialty != "Cardiologie"
