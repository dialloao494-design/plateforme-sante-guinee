"""
Production boot guard tests — A3 (pilot seed) and A4 (availability bypass) + secrets.
"""

from __future__ import annotations

import pytest

from core.settings import AppSettings, get_settings, is_insecure_secret


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def _apply_valid_production_env(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DOMAIN", "api.plateforme-sante.gn")
    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret-" + "A" * 32)
    monkeypatch.setenv("SECRET_KEY", "prod-jwt-secret-" + "A" * 32)
    monkeypatch.setenv("POSTGRES_PASSWORD", "StrongProductionDb!" + "Z" * 8)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://sante:StrongProductionDb!" + "Z" * 8 + "@db:5432/sante",
    )
    monkeypatch.setenv("JITSI_APP_ID", "prod-jitsi-app")
    monkeypatch.setenv("JITSI_APP_SECRET", "jitsi-production-secret-" + "C" * 8)
    monkeypatch.setenv("ENABLE_PILOT_SEED", "false")
    monkeypatch.setenv("BYPASS_AVAILABILITY_VALIDATION", "false")
    _clear_settings_cache()


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    yield
    _clear_settings_cache()


class TestInsecureSecretDetection:
    def test_rejects_empty_and_short_values(self):
        assert is_insecure_secret("", min_length=32) is True
        assert is_insecure_secret("short", min_length=32) is True

    def test_rejects_changeme_and_demo_patterns(self):
        assert is_insecure_secret("change-me-in-production-use-strong-random-string", min_length=32) is True
        assert is_insecure_secret("demo-jitsi-secret-value-here", min_length=16) is True
        assert is_insecure_secret("sk_test_abcdefghijklmnopqrst", min_length=20) is True


class TestProductionBootGuardA3:
    """ENABLE_PILOT_SEED=true must abort production startup."""

    def test_pilot_seed_forbidden_in_production(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.setenv("ENABLE_PILOT_SEED", "true")
        settings = AppSettings()
        with pytest.raises(RuntimeError, match="ENABLE_PILOT_SEED"):
            settings.enforce_production_boot()

    def test_pilot_seed_allowed_in_development(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ENABLE_PILOT_SEED", "true")
        settings = AppSettings()
        settings.enforce_production_boot()


class TestProductionBootGuardA4:
    """BYPASS_AVAILABILITY_VALIDATION=true must abort production startup."""

    def test_bypass_availability_forbidden_in_production(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.setenv("BYPASS_AVAILABILITY_VALIDATION", "true")
        settings = AppSettings()
        with pytest.raises(RuntimeError, match="BYPASS_AVAILABILITY_VALIDATION"):
            settings.enforce_production_boot()

    def test_bypass_allowed_in_development(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("BYPASS_AVAILABILITY_VALIDATION", "true")
        settings = AppSettings()
        settings.enforce_production_boot()


class TestProductionBootSecrets:
    def test_valid_production_configuration_passes(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        AppSettings().enforce_production_boot()

    def test_weak_jwt_secret_rejected(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
        monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            AppSettings().enforce_production_boot()

    def test_weak_db_password_rejected(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.setenv("POSTGRES_PASSWORD", "sante_dev_password")
        monkeypatch.setenv("DATABASE_URL", "postgresql://sante:sante_dev_password@db:5432/sante")
        with pytest.raises(RuntimeError, match="DB_PASSWORD"):
            AppSettings().enforce_production_boot()
    def test_missing_jitsi_secret_rejected(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
        monkeypatch.delenv("JITSI_SECRET", raising=False)
        with pytest.raises(RuntimeError, match="JITSI_SECRET"):
            AppSettings().enforce_production_boot()


class TestProductionStartupIntegration:
    def test_main_module_loads_in_development(self):
        import main  # noqa: F401 — must not SystemExit

    def test_enforce_production_boot_via_get_settings(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        get_settings().enforce_production_boot()

    def test_production_boot_blocks_all_dangerous_flags_together(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.setenv("ENABLE_PILOT_SEED", "true")
        monkeypatch.setenv("BYPASS_AVAILABILITY_VALIDATION", "true")
        monkeypatch.setenv("SECRET_KEY", "change-me")
        settings = AppSettings()
        with pytest.raises(RuntimeError):
            settings.enforce_production_boot()
