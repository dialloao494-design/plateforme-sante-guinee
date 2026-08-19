"""Auth profile and password change API tests."""

from __future__ import annotations

import models
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password, verify_password


def _auth_headers(user):
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
            "session_version": user.session_version,
            "tv": int(getattr(user, "token_version", 0) or 0),
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_auth_me_includes_profile_fields(client, db_session, admin_user):
  clinic = models.Clinic(name="Test Clinic Auth", city="Conakry", is_active=True)
  db_session.add(clinic)
  db_session.commit()
  db_session.refresh(clinic)

  admin_user.clinic_id = clinic.id
  db_session.commit()

  r = client.get("/auth/me", headers=_auth_headers(admin_user))
  assert r.status_code == 200, r.text
  body = r.json()
  assert body["email"] == admin_user.email
  assert body.get("full_name")
  assert body.get("clinic_id") == clinic.id
  assert body.get("clinic_name") == clinic.name


def test_user_can_update_own_display_name(client, db_session, admin_user):
  r = client.patch(
      "/auth/me",
      json={"first_name": "Mouctar", "last_name": "Diallo"},
      headers=_auth_headers(admin_user),
  )
  assert r.status_code == 200, r.text
  assert r.json()["first_name"] == "Mouctar"
  assert r.json()["last_name"] == "Diallo"
  assert r.json()["full_name"] == "Mouctar Diallo"
  db_session.refresh(admin_user)
  assert admin_user.first_name == "Mouctar"
  assert admin_user.last_name == "Diallo"


def test_doctor_name_update_propagates_to_reception_profile(client, db_session):
  clinic = models.Clinic(name="Clinique identité médecin", city="Conakry", is_active=True)
  db_session.add(clinic)
  db_session.flush()
  with provisioning_channel("test_fixture"):
    doctor_user = models.User(
        email="placeholder.doctor@test.gn",
        hashed_password=hash_password("DoctorSecure12!"),
        role="doctor",
        clinic_id=clinic.id,
    )
    db_session.add(doctor_user)
    db_session.flush()
  doctor = models.Doctor(
      user_id=doctor_user.id,
      first_name="Doctor",
      last_name=f"User{doctor_user.id}",
      specialty="Médecine générale",
      city="Conakry",
      phone="000000000",
      clinic_id=clinic.id,
  )
  db_session.add(doctor)
  db_session.commit()

  r = client.patch(
      "/auth/me",
      json={"first_name": "Aïssatou", "last_name": "Bah"},
      headers=_auth_headers(doctor_user),
  )
  assert r.status_code == 200, r.text
  db_session.refresh(doctor)
  assert doctor.full_name == "Aïssatou Bah"
  assert r.json()["full_name"] == "Aïssatou Bah"


def test_profile_name_rejects_numbers_and_extra_fields(client, admin_user):
  invalid = client.patch(
      "/auth/me",
      json={"first_name": "User151", "last_name": "Diallo"},
      headers=_auth_headers(admin_user),
  )
  assert invalid.status_code == 422

  privileged = client.patch(
      "/auth/me",
      json={"first_name": "Mamadou", "last_name": "Diallo", "role": "platform_owner"},
      headers=_auth_headers(admin_user),
  )
  assert privileged.status_code == 422


def test_change_password_updates_hash(client, db_session, admin_user):
  old_hash = admin_user.hashed_password
  old_session_version = admin_user.session_version
  old_token_version = int(getattr(admin_user, "token_version", 0) or 0)
  old_headers = _auth_headers(admin_user)
  r = client.post(
      "/auth/change-password",
      json={"current_password": "AdminPass12!", "new_password": "NewSecure12!"},
      headers=old_headers,
  )
  assert r.status_code == 200, r.text
  db_session.refresh(admin_user)
  assert admin_user.hashed_password != old_hash
  assert verify_password("NewSecure12!", admin_user.hashed_password)
  assert r.json()["access_token"]
  assert client.get("/auth/me", headers=old_headers).status_code == 401
  replacement_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
  assert client.get("/auth/me", headers=replacement_headers).status_code == 200

  # restore for other tests
  admin_user.hashed_password = old_hash
  admin_user.session_version = old_session_version
  admin_user.must_change_password = False
  admin_user.token_version = old_token_version
  db_session.add(admin_user)
  db_session.commit()


def test_change_password_rejects_wrong_current(client, db_session, admin_user):
  admin_user.token_version = 0
  db_session.add(admin_user)
  db_session.commit()
  r = client.post(
      "/auth/change-password",
      json={"current_password": "wrong-password", "new_password": "NewSecure12!"},
      headers=_auth_headers(admin_user),
  )
  assert r.status_code == 400


def test_logout_revokes_previously_issued_token(client, db_session, admin_user):
  old_session_version = admin_user.session_version
  headers = _auth_headers(admin_user)

  response = client.post("/auth/logout", headers=headers)
  assert response.status_code == 200, response.text
  assert client.get("/auth/me", headers=headers).status_code == 401

  admin_user.session_version = old_session_version
  db_session.add(admin_user)
  db_session.commit()
