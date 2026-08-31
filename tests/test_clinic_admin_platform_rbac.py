"""Clinic admin vs platform owner — clinic creation and staff scope."""

from __future__ import annotations

from datetime import datetime, timedelta

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
            hashed_password=hash_password("Secret12Pass!"),
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
            "password": "Secret12Pass!",
            "role": "receptionist",
            "clinic_id": clinic_b.id,
        },
        headers=_auth(admin),
    )
    assert response.status_code == 403, response.text

    invitation = client.post(
        "/clinical/staff/invitations",
        json={
            "email": "rbac.cross.invitation@test.gn",
            "role": "nurse",
            "clinic_id": clinic_b.id,
            "first_name": "Cross",
            "last_name": "Clinic",
        },
        headers=_auth(admin),
    )
    assert invitation.status_code == 403, invitation.text

    existing_owner = (
        db_session.query(models.User).filter(models.User.role == "platform_owner").first()
    )
    if existing_owner is None:
        with provisioning_channel("platform_owner_bootstrap"):
            owner = models.User(
                email="rbac.platform.owner@test.gn",
                hashed_password=hash_password("Secret12Pass!"),
                role="platform_owner",
            )
            db_session.add(owner)
            db_session.commit()
            db_session.refresh(owner)
    else:
        owner = existing_owner

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
            hashed_password=hash_password("Secret12Pass!"),
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


def test_clinic_invitation_response_never_exposes_secret(client, db_session, monkeypatch):
    import services.staff_activation_service as activation

    clinic = models.Clinic(name="Secure Invitation Clinic", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    admin = _clinic_admin(db_session, clinic.id, email=f"secure.invite.admin.{clinic.id}@test.gn")
    captured = {}
    monkeypatch.setattr(
        activation,
        "send_staff_activation_email",
        lambda email, link, **kwargs: captured.update(email=email, link=link) or True,
    )
    response = client.post(
        "/clinical/staff/invitations",
        json={
            "email": f"secure.invited.nurse.{clinic.id}@test.gn",
            "role": "nurse",
            "clinic_id": clinic.id,
            "first_name": "Hawa",
            "last_name": "Barry",
        },
        headers=_auth(admin),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["staff"]["is_active"] is False
    assert payload["delivery_status"] == "sent"
    assert "token" not in response.text.lower()
    assert "password" not in payload
    assert "password" not in payload["staff"]
    assert "token=" in captured["link"]


def test_clinic_admin_sends_reset_link_without_seeing_it(client, db_session, monkeypatch):
    import routers.clinical as clinical_router

    clinic = models.Clinic(name="Secure Reset Clinic", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    admin = _clinic_admin(db_session, clinic.id, email=f"secure.reset.admin.{clinic.id}@test.gn")
    with provisioning_channel("test_fixture"):
        staff = models.User(
            email=f"secure.reset.staff.{clinic.id}@test.gn",
            hashed_password=hash_password("Secret12Pass!"),
            role="nurse",
            clinic_id=clinic.id,
        )
        db_session.add(staff)
        db_session.commit()
    captured = {}
    monkeypatch.setattr(clinical_router, "send_reset_email", lambda email, raw: captured.update(email=email, raw=raw) or True)
    response = client.post(
        f"/clinical/staff/{staff.id}/password-reset-link",
        params={"clinic_id": clinic.id},
        headers=_auth(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["delivery_status"] == "sent"
    assert "raw" not in response.text and "token" not in response.text
    assert len(captured["raw"]) >= 32


def test_clinic_admin_can_deactivate_and_reactivate_staff(client, db_session):
    clinic = models.Clinic(name="Lifecycle Clinic", is_active=True)
    db_session.add(clinic); db_session.commit()
    admin = _clinic_admin(db_session, clinic.id, email=f"lifecycle.admin.{clinic.id}@test.gn")
    with provisioning_channel("test_fixture"):
        staff = models.User(
            email=f"lifecycle.nurse.{clinic.id}@test.gn",
            hashed_password=hash_password("Secret12Pass!"), role="nurse", clinic_id=clinic.id,
            email_verified_at=datetime.utcnow(), is_active=True,
        )
        db_session.add(staff); db_session.flush()
        db_session.add(models.ClinicStaff(clinic_id=clinic.id, user_id=staff.id, is_active=True)); db_session.commit()

    response = client.patch(f"/clinical/staff/{staff.id}/deactivate", params={"clinic_id": clinic.id}, json={"reason": "Fin de remplacement"}, headers=_auth(admin))
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False
    db_session.expire_all()
    assert db_session.query(models.ClinicStaff).filter_by(user_id=staff.id).one().is_active is False

    response = client.patch(f"/clinical/staff/{staff.id}/reactivate", params={"clinic_id": clinic.id}, json={"reason": "Retour planifié"}, headers=_auth(admin))
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is True


def test_clinic_admin_can_edit_staff_name_and_role_with_audit(client, db_session):
    clinic = models.Clinic(name="Editable Staff Clinic", is_active=True)
    db_session.add(clinic); db_session.commit()
    admin = _clinic_admin(db_session, clinic.id, email=f"edit.admin.{clinic.id}@test.gn")
    with provisioning_channel("test_fixture"):
        staff = models.User(
            email=f"edit.staff.{clinic.id}@test.gn", hashed_password=hash_password("Secret12Pass!"),
            role="receptionist", clinic_id=clinic.id, first_name="Ancien", last_name="Nom",
        )
        db_session.add(staff); db_session.flush()
        db_session.add(models.ClinicStaff(clinic_id=clinic.id, user_id=staff.id, is_active=True)); db_session.commit()

    response = client.patch(
        f"/clinical/staff/{staff.id}",
        json={"clinic_id": clinic.id, "first_name": "Aïssatou", "last_name": "Camara", "role": "nurse", "reason": "Affectation au service infirmier"},
        headers=_auth(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["first_name"] == "Aïssatou"
    assert response.json()["last_name"] == "Camara"
    assert response.json()["role"] == "nurse"
    audit = db_session.query(models.ClinicalAuditLog).filter_by(
        clinic_id=clinic.id, resource_type="staff", resource_id=staff.id, action="update_profile",
    ).one()
    assert audit.reason == "Affectation au service infirmier"
    assert '"role": "receptionist"' in audit.before_json
    assert '"role": "nurse"' in audit.after_json


def test_clinic_admin_cannot_promote_staff_to_administrator(client, db_session):
    clinic = models.Clinic(name="Guarded Staff Clinic", is_active=True)
    db_session.add(clinic); db_session.commit()
    admin = _clinic_admin(db_session, clinic.id, email=f"guard.edit.admin.{clinic.id}@test.gn")
    with provisioning_channel("test_fixture"):
        staff = models.User(email=f"guard.edit.staff.{clinic.id}@test.gn", hashed_password=hash_password("Secret12Pass!"), role="nurse", clinic_id=clinic.id)
        db_session.add(staff); db_session.commit()
    response = client.patch(
        f"/clinical/staff/{staff.id}",
        json={"clinic_id": clinic.id, "first_name": "Mariam", "last_name": "Bah", "role": "clinic_admin", "reason": "Promotion non autorisée"},
        headers=_auth(admin),
    )
    assert response.status_code == 403
    assert db_session.get(models.User, staff.id).role == "nurse"


def test_delete_is_limited_to_unused_inactive_invitation(client, db_session):
    clinic = models.Clinic(name="Delete Invitation Clinic", is_active=True)
    db_session.add(clinic); db_session.commit()
    admin = _clinic_admin(db_session, clinic.id, email=f"delete.admin.{clinic.id}@test.gn")
    with provisioning_channel("test_fixture"):
        invited = models.User(
            email=f"unused.invite.{clinic.id}@test.gn",
            hashed_password=hash_password("Secret12Pass!"), role="receptionist", clinic_id=clinic.id,
            is_active=False,
        )
        db_session.add(invited); db_session.flush()
        db_session.add(models.ClinicStaff(clinic_id=clinic.id, user_id=invited.id, is_active=False))
        db_session.add(models.StaffActivationToken(
            user_id=invited.id, created_by_user_id=admin.id, token_hash=f"unused-{invited.id}",
            expires_at=datetime.utcnow() + timedelta(hours=1), delivery_status="sent",
        )); db_session.commit(); invited_id=invited.id

    response = client.request("DELETE", f"/clinical/staff/{invited_id}", params={"clinic_id": clinic.id}, json={"reason": "Invitation créée par erreur"}, headers=_auth(admin))
    assert response.status_code == 204, response.text
    assert db_session.query(models.User).filter_by(id=invited_id).first() is None


def test_delete_rejects_account_with_history(client, db_session):
    clinic = models.Clinic(name="Preserve History Clinic", is_active=True)
    db_session.add(clinic); db_session.commit()
    admin = _clinic_admin(db_session, clinic.id, email=f"history.admin.{clinic.id}@test.gn")
    with provisioning_channel("test_fixture"):
        former = models.User(
            email=f"former.staff.{clinic.id}@test.gn",
            hashed_password=hash_password("Secret12Pass!"), role="cashier", clinic_id=clinic.id,
            is_active=False, email_verified_at=datetime.utcnow(), last_login_at=datetime.utcnow(),
        )
        db_session.add(former); db_session.commit()
    response = client.request("DELETE", f"/clinical/staff/{former.id}", params={"clinic_id": clinic.id}, json={"reason": "Demande de suppression"}, headers=_auth(admin))
    assert response.status_code == 409, response.text
    assert db_session.query(models.User).filter_by(id=former.id).first() is not None
