"""
Security tests for public registration and admin provisioning (audit item #1).
"""

from __future__ import annotations

import pytest

from core.roles import PublicRegistrationRoleError
from models.user import User
from services.user_provisioning import register_public_user


class TestPublicRegistrationEndpoint:
    def test_register_patient_succeeds(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "patient.secure@example.com",
                "password": "Secret12",
                "role": "patient",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["role"] == "patient"
        assert body["email"] == "patient.secure@example.com"

    def test_register_doctor_succeeds(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "doctor.secure@example.com",
                "password": "Secret12",
                "role": "doctor",
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == "doctor"
        assert response.json().get("doctor_id") is not None

    def test_register_weak_password_rejected(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "weak.pass@example.com",
                "password": "short1",
                "role": "patient",
            },
        )
        assert response.status_code == 422

    def test_register_admin_role_rejected(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "evil.admin@example.com",
                "password": "Secret12",
                "role": "admin",
            },
        )
        assert response.status_code == 422
        detail = response.json().get("detail")
        assert detail
        assert "admin" in str(detail).lower() or "registration" in str(detail).lower()

    def test_register_admin_role_case_variants_rejected(self, client):
        for role_value in ("Admin", "ADMIN", " admin "):
            response = client.post(
                "/auth/register",
                json={
                    "email": f"case.{role_value.strip().lower()}@example.com",
                    "password": "Secret12",
                    "role": role_value,
                },
            )
            assert response.status_code == 422, f"Expected 422 for role={role_value!r}"

    def test_register_unknown_role_rejected(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "superuser@example.com",
                "password": "Secret12",
                "role": "superadmin",
            },
        )
        assert response.status_code == 422

    def test_register_extra_fields_forbidden(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "inject@example.com",
                "password": "Secret12",
                "role": "patient",
                "is_admin": True,
            },
        )
        assert response.status_code == 422

    def test_register_admin_via_typosquat_role_rejected(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "adm1n@example.com",
                "password": "Secret12",
                "role": "adm1n",
            },
        )
        assert response.status_code == 422

    def test_no_admin_created_after_attack(self, client, db_session):
        client.post(
            "/auth/register",
            json={
                "email": "blocked.admin@example.com",
                "password": "Secret12",
                "role": "admin",
            },
        )
        user = (
            db_session.query(User)
            .filter(User.email == "blocked.admin@example.com")
            .first()
        )
        assert user is None


class TestAdminProvisioningEndpoint:
    def test_create_admin_requires_authentication(self, client):
        response = client.post(
            "/users/admins",
            json={
                "email": "new.admin@example.com",
                "password": "StrongPass1",
            },
        )
        assert response.status_code == 401

    def test_create_admin_requires_admin_role(self, client):
        client.post(
            "/auth/register",
            json={
                "email": "not.admin@example.com",
                "password": "Secret12",
                "role": "patient",
            },
        )
        login = client.post(
            "/auth/login-json",
            json={"email": "not.admin@example.com", "password": "Secret12"},
        )
        token = login.json()["access_token"]
        response = client.post(
            "/users/admins",
            json={
                "email": "should.fail@example.com",
                "password": "StrongPass1",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_can_create_admin(self, client, admin_headers):
        response = client.post(
            "/users/admins",
            json={
                "email": "ops.admin@example.com",
                "password": "StrongPass1",
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["role"] == "clinic_admin"

    def test_admin_create_weak_password_rejected(self, client, admin_headers):
        response = client.post(
            "/users/admins",
            json={
                "email": "weak.admin@example.com",
                "password": "weak",
            },
            headers=admin_headers,
        )
        assert response.status_code == 422


class TestUserProvisioningService:
    def test_service_rejects_admin_on_public_channel(self, db_session):
        with pytest.raises(PublicRegistrationRoleError):
            register_public_user(
                db_session,
                email="service.admin@example.com",
                password="Secret12",
                role="admin",
            )


class TestOrmPrivilegedRoleGuard:
    def test_direct_admin_insert_blocked_without_channel(self, db_session):
        from core.roles import PrivilegedRoleAssignmentError
        from models.user import User
        from security import hash_password

        with pytest.raises(PrivilegedRoleAssignmentError):
            user = User(
                email="orm.bypass@example.com",
                hashed_password=hash_password("Secret12"),
                role="admin",
            )
            db_session.add(user)
            db_session.commit()

    def test_direct_admin_insert_allowed_in_test_fixture_channel(self, db_session):
        from core.provisioning_context import provisioning_channel
        from models.user import User
        from security import hash_password

        with provisioning_channel("test_fixture"):
            user = User(
                email="orm.allowed@example.com",
                hashed_password=hash_password("Secret12"),
                role="admin",
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        assert user.role == "admin"

    def test_role_escalation_to_admin_blocked_without_channel(self, db_session):
        from core.roles import PrivilegedRoleAssignmentError
        from models.user import User
        from security import hash_password

        user = User(
            email="escalate@example.com",
            hashed_password=hash_password("Secret12"),
            role="patient",
        )
        db_session.add(user)
        db_session.commit()
        user.role = "admin"
        with pytest.raises(PrivilegedRoleAssignmentError):
            db_session.commit()


class TestJwtRoleIntegrity:
    def test_forged_admin_claim_in_token_rejected(self, client, db_session):
        from security import create_access_token

        client.post(
            "/auth/register",
            json={
                "email": "jwt.victim@example.com",
                "password": "Secret12",
                "role": "patient",
            },
        )
        user = (
            db_session.query(User)
            .filter(User.email == "jwt.victim@example.com")
            .first()
        )
        assert user is not None
        assert user.role == "patient"

        forged = create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id,
                "user_role": "admin",
                "role": "admin",
            }
        )
        response = client.get(
            "/users/",
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert response.status_code == 401


class TestAdminProvisioningChannels:
    def test_create_admin_rejects_invalid_channel(self, db_session):
        from services.user_provisioning import create_admin_user
        from core.roles import PrivilegedRoleAssignmentError

        with pytest.raises(PrivilegedRoleAssignmentError):
            create_admin_user(
                db_session,
                email="bad.channel@example.com",
                password="StrongPass1",
                channel="public_register",
            )


class TestAdminBootstrap:
    def test_bootstrap_disabled_by_default(self, db_session, monkeypatch):
        from services.user_provisioning import bootstrap_initial_admin

        monkeypatch.delenv("ENABLE_ADMIN_BOOTSTRAP", raising=False)
        assert bootstrap_initial_admin(db_session) is None

    def test_bootstrap_does_not_escalate_existing_non_admin(self, db_session, monkeypatch):
        from models.user import User
        from security import hash_password
        from services.user_provisioning import bootstrap_initial_admin

        email = "existing.patient@bootstrap.test"
        user = User(
            email=email,
            hashed_password=hash_password("Secret12"),
            role="patient",
        )
        db_session.add(user)
        db_session.commit()

        monkeypatch.setenv("ENABLE_ADMIN_BOOTSTRAP", "true")
        monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAIL", email)
        monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "StrongPass1")

        result = bootstrap_initial_admin(db_session)
        assert result is None
        db_session.refresh(user)
        assert user.role == "patient"
