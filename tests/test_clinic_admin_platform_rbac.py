"""Clinic admin vs platform owner — clinic creation and staff scope."""

from __future__ import annotations

import models
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password


def _auth(user):
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def _clinic_admin(db_session, clinic_id: int, *, email: str | None = None):
    with provisioning_channel("test_fixture"):
        user = models.User(
            email=email or f"rbac.clinic.admin.{clinic_id}@test.gn",
            hashed_password=hash_password("Secret12"),
            role="clinic_admin",
            clinic_id=clinic_id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_clinic_admin_cannot_create_clinic(client, db_session):
    clinic = models.Clinic(name="RBAC Clinic", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)

    admin = _clinic_admin(db_session, clinic.id)
    response = client.post(
        "/clinical/clinics",
        json={"name": "Unauthorized Clinic", "city": "Conakry"},
        headers=_auth(admin),
    )
    assert response.status_code == 403, response.text


def test_clinic_admin_cannot_provision_staff_for_other_clinic(client, db_session):
    clinic_a = models.Clinic(name="RBAC Clinic A", city="Conakry", is_active=True)
    clinic_b = models.Clinic(name="RBAC Clinic B", city="Kindia", is_active=True)
    db_session.add_all([clinic_a, clinic_b])
    db_session.commit()
    db_session.refresh(clinic_a)
    db_session.refresh(clinic_b)

    admin = _clinic_admin(db_session, clinic_a.id)
    response = client.post(
        "/clinical/staff",
        json={
            "email": "rbac.cross.clinic@test.gn",
            "password": "Secret12!",
            "role": "receptionist",
            "clinic_id": clinic_b.id,
        },
        headers=_auth(admin),
    )
    assert response.status_code == 403, response.text


    with provisioning_channel("platform_owner_bootstrap"):
        owner = models.User(
            email="rbac.platform.owner@test.gn",
            hashed_password=hash_password("Secret12"),
            role="platform_owner",
        )
        db_session.add(owner)
        db_session.commit()
        db_session.refresh(owner)

    response = client.post(
        "/clinical/clinics",
        json={"name": "Owner Created Clinic", "city": "Kindia"},
        headers=_auth(owner),
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Owner Created Clinic"


def test_platform_admin_can_create_clinic(client, db_session):
    with provisioning_channel("test_fixture"):
        admin = models.User(
            email="rbac.platform.admin@test.gn",
            hashed_password=hash_password("Secret12"),
            role="platform_admin",
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    response = client.post(
        "/clinical/clinics",
        json={"name": "Platform Admin Clinic", "city": "Conakry"},
        headers=_auth(admin),
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Platform Admin Clinic"
