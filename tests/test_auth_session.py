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
