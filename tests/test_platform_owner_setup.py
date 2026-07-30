"""First-time Platform Owner setup API."""

from __future__ import annotations

import pytest

from core.provisioning_context import provisioning_channel
from models.user import User
from security import hash_password


@pytest.fixture(autouse=True)
def _clear_platform_owners(db_session):
    db_session.query(User).filter(User.role == "platform_owner").delete(
        synchronize_session=False
    )
    db_session.commit()
    yield
    db_session.query(User).filter(User.role == "platform_owner").delete(
        synchronize_session=False
    )
    db_session.commit()


class TestPlatformOwnerSetup:
    def test_status_required_when_no_owner(self, client):
        response = client.get("/platform/setup/status")
        assert response.status_code == 200
        assert response.json()["setup_required"] is True

    def test_setup_creates_owner_and_returns_token(self, client, db_session):
        response = client.post(
            "/platform/setup",
            json={
                "email": "owner.production@example.com",
                "password": "SecureOwner12!",
                "password_confirm": "SecureOwner12!",
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["role"] == "platform_owner"
        assert payload["access_token"]

        owner = db_session.query(User).filter(User.role == "platform_owner").first()
        assert owner is not None
        assert owner.email == "owner.production@example.com"

    def test_status_closed_after_owner_exists(self, client):
        client.post(
            "/platform/setup",
            json={
                "email": "owner.closed@example.com",
                "password": "SecureOwner12!",
                "password_confirm": "SecureOwner12!",
            },
        )
        response = client.get("/platform/setup/status")
        assert response.json()["setup_required"] is False

    def test_second_setup_rejected(self, client):
        client.post(
            "/platform/setup",
            json={
                "email": "owner.first@example.com",
                "password": "SecureOwner12!",
                "password_confirm": "SecureOwner12!",
            },
        )
        response = client.post(
            "/platform/setup",
            json={
                "email": "owner.second@example.com",
                "password": "SecureOwner12b!",
                "password_confirm": "SecureOwner12b!",
            },
        )
        assert response.status_code == 403

    def test_setup_rejects_mismatched_passwords(self, client):
        response = client.post(
            "/platform/setup",
            json={
                "email": "owner.mismatch@example.com",
                "password": "SecureOwner12!",
                "password_confirm": "DifferentPass12!",
            },
        )
        assert response.status_code == 422

    def test_setup_not_available_when_owner_preexists(self, client, db_session):
        with provisioning_channel("platform_owner_setup"):
            db_session.add(
                User(
                    email="existing.owner@example.com",
                    hashed_password=hash_password("SecureOwner12!"),
                    role="platform_owner",
                )
            )
            db_session.commit()

        response = client.post(
            "/platform/setup",
            json={
                "email": "new.owner@example.com",
                "password": "SecureOwner12!",
                "password_confirm": "SecureOwner12!",
            },
        )
        assert response.status_code == 403

    def test_owner_can_access_platform_settings(self, client):
        setup = client.post(
            "/platform/setup",
            json={
                "email": "owner.api@example.com",
                "password": "SecureOwner12!",
                "password_confirm": "SecureOwner12!",
            },
        )
        token = setup.json()["access_token"]
        response = client.get(
            "/platform/settings",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
