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
  r = client.post(
      "/auth/change-password",
      json={"current_password": "AdminPass1", "new_password": "NewSecure12!"},
      headers=_auth_headers(admin_user),
  )
  assert r.status_code == 200, r.text
  db_session.refresh(admin_user)
  assert admin_user.hashed_password != old_hash
  assert verify_password("NewSecure12!", admin_user.hashed_password)

  # restore for other tests
  admin_user.hashed_password = old_hash
  admin_user.token_version = 0
  admin_user.must_change_password = False
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
