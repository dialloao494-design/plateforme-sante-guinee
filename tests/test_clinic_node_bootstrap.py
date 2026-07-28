"""Phase 1 Clinic Node local auth / bootstrap tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from core.settings import AppSettings, get_settings
from database import Base, engine
from services.clinic_node_bootstrap import bootstrap_clinic_node


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    yield
    _clear_settings_cache()


class TestClinicNodePilotSeedDefault:
    def test_clinic_node_is_not_production_but_is_deployed(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "clinic-node")
        monkeypatch.setenv("DOMAIN", "sante-locale")
        monkeypatch.setenv("JWT_SECRET", "clinic-node-jwt-secret-" + "A" * 32)
        monkeypatch.setenv("SECRET_KEY", "clinic-node-jwt-secret-" + "A" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "StrongClinicNodeDb!" + "Z" * 8)
        monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "proxy,127.0.0.1")
        monkeypatch.setenv("ALLOWED_HOSTS", "sante-locale,backend")
        _clear_settings_cache()
        settings = AppSettings()
        assert settings.is_clinic_node is True
        assert settings.is_production is False
        assert settings.is_deployed is True


class TestClinicNodeBootstrap:
    def test_bootstrap_creates_clinic_and_admin(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "clinic-node")
        monkeypatch.setenv("ENABLE_CLINIC_NODE_BOOTSTRAP", "true")
        monkeypatch.setenv("CLINIC_NODE_CLINIC_NAME", "Clinique E2E Phase1")
        monkeypatch.setenv("CLINIC_NODE_ADMIN_EMAIL", "admin.phase1@clinic.local")
        monkeypatch.setenv("CLINIC_NODE_ADMIN_PASSWORD", "Phase1AdminPass1!")
        monkeypatch.setenv("CLINIC_NODE_ADMIN_MUST_CHANGE_PASSWORD", "true")
        monkeypatch.setenv("CLINIC_NODE_BOOTSTRAP_STAFF", "false")

        # Use isolated sqlite for unit test
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker as sm
        import models  # noqa: F401

        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        Session = sm(bind=test_engine)
        db = Session()
        try:
            first = bootstrap_clinic_node(db)
            assert first is not None
            assert first["created_clinic"] is True
            assert first["created_admin"] is True
            assert first["clinic_id"]
            assert first["admin_user_id"]

            second = bootstrap_clinic_node(db)
            assert second["created_clinic"] is False
            assert second["created_admin"] is False
            assert second["clinic_id"] == first["clinic_id"]
            assert second["admin_user_id"] == first["admin_user_id"]

            from models.user import User

            admin = db.query(User).filter(User.id == first["admin_user_id"]).one()
            assert admin.role == "clinic_admin"
            assert admin.clinic_id == first["clinic_id"]
            assert admin.must_change_password is True
        finally:
            db.close()

    def test_bootstrap_noop_outside_clinic_node(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ENABLE_CLINIC_NODE_BOOTSTRAP", "true")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker as sm
        import models  # noqa: F401

        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        db = sm(bind=test_engine)()
        try:
            assert bootstrap_clinic_node(db) is None
        finally:
            db.close()
