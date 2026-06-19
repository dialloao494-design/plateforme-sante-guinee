"""Doctor portal RBAC — role normalization for appointments and notifications."""

from __future__ import annotations

from types import SimpleNamespace

import models
from core.provisioning_context import provisioning_channel
from core.roles import effective_role, user_has_any_role
from security import create_access_token, hash_password
from services.rendezvous_service import RendezVousService


def _auth_headers(user, *, token_role: str | None = None):
    role = token_role if token_role is not None else user.role
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": role, "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_effective_role_normalizes_doctor_aliases():
    assert effective_role("Doctor") == "doctor"
    assert effective_role(" medecin ") == "doctor"
    assert effective_role("physician") == "doctor"
    assert user_has_any_role("Médecin", ["doctor"])
    assert user_has_any_role("Doctor", ["admin", "doctor", "patient"])


def test_list_appointments_accepts_legacy_doctor_role_casing(db_session):
    user = SimpleNamespace(id=999, role="Doctor", clinic_id=None)
    result = RendezVousService.list_appointments_for_user(user, db_session)
    assert result == []


def test_standalone_doctor_can_list_appointments_and_notifications(client, db_session):
    with provisioning_channel("test_fixture"):
        user = models.User(
            email="standalone.doctor.rbac@test.gn",
            hashed_password=hash_password("Secret12"),
            role="doctor",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    db_session.add(
        models.Doctor(
            user_id=user.id,
            first_name="Doctor",
            last_name=f"User{user.id}",
            specialty="Médecine générale",
            city="Conakry",
            phone="000000000",
            consultation_fee=0.0,
        )
    )
    db_session.commit()

    headers = _auth_headers(user, token_role="Doctor")
    appointments = client.get("/appointments/", headers=headers)
    assert appointments.status_code == 200, appointments.text

    notifications = client.get("/notifications/", headers=headers)
    assert notifications.status_code == 200, notifications.text

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["role"] == "doctor"
