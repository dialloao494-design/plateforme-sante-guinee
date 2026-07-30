"""
Production boot guard tests — A3 (pilot seed) and A4 (availability bypass) + secrets.
"""

from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet

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
    monkeypatch.setenv("ENABLE_STARTUP_TEST_USER", "false")
    monkeypatch.setenv("ENABLE_STARTUP_SEED", "false")
    monkeypatch.setenv("ENABLE_DEMO_CLINIC_SEED", "false")
    monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "127.0.0.1,backend")
    monkeypatch.setenv("REMINDER_RESPOND_TOKEN", "reminder-respond-token-" + "R" * 32)
    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
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


class TestProductionBootGuardSeedFlags:
    """Demo/dev seed flags must abort production startup."""

    @pytest.mark.parametrize(
        "flag_name",
        [
            "ENABLE_STARTUP_TEST_USER",
            "ENABLE_STARTUP_SEED",
            "ENABLE_DEMO_CLINIC_SEED",
        ],
    )
    def test_seed_flags_forbidden_in_production(self, monkeypatch, flag_name: str):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.setenv(flag_name, "true")
        settings = AppSettings()
        with pytest.raises(RuntimeError, match=flag_name):
            settings.enforce_production_boot()


class TestTrustedProxyHosts:
    def test_wildcard_proxy_hosts_rejected_in_production(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "*")
        settings = AppSettings()
        with pytest.raises(RuntimeError, match="TRUSTED_PROXY_HOSTS"):
            settings.enforce_production_boot()

    def test_railway_defaults_trusted_proxy_when_unset(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.delenv("TRUSTED_PROXY_HOSTS", raising=False)
        hosts = AppSettings().resolve_trusted_proxy_hosts()
        assert "127.0.0.1" in hosts
        assert "backend" in hosts

    def test_explicit_proxy_hosts_allowed_in_production(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        AppSettings().resolve_trusted_proxy_hosts()


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
    def test_missing_jitsi_secret_rejected_off_railway(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
        monkeypatch.delenv("JITSI_SECRET", raising=False)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        with pytest.raises(RuntimeError, match="JITSI_SECRET"):
            AppSettings().enforce_production_boot()

    def test_missing_jitsi_secret_allowed_on_railway_without_require_flag(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
        monkeypatch.delenv("JITSI_SECRET", raising=False)
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://sante:StrongProductionDb!"
            + "Z" * 8
            + "@postgres.railway.internal:5432/railway",
        )
        monkeypatch.delenv("REQUIRE_JITSI_SECRET", raising=False)
        AppSettings().enforce_production_boot()

    def test_missing_reminder_token_derived_from_jwt_in_production(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("REMINDER_RESPOND_TOKEN", raising=False)
        AppSettings().enforce_production_boot()
        token = __import__("os").environ.get("REMINDER_RESPOND_TOKEN") or ""
        assert len(token) >= 32


    def test_staging_bootstrap_env_passes_boot_guard(self, monkeypatch):
        """Mirrors deploy/vps/bootstrap-autonomous.sh generated env."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("DOMAIN", "staging.sante.example.gn")
        monkeypatch.setenv("JWT_SECRET", "staging-jwt-secret-" + "A" * 32)
        monkeypatch.setenv("SECRET_KEY", "staging-jwt-secret-" + "A" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "StrongStagingDb!" + "Z" * 8)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://sante:StrongStagingDb!" + "Z" * 8 + "@db:5432/sante",
        )
        monkeypatch.setenv("JITSI_APP_SECRET", "jitsi-staging-secret-" + "C" * 8)
        monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "127.0.0.1,backend")
        monkeypatch.setenv("REMINDER_RESPOND_TOKEN", "reminder-staging-token-" + "R" * 16)
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


class TestAttachmentEncryptionBoot:
    def test_attachment_encryption_required_in_production(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("REQUIRE_ATTACHMENT_ENCRYPTION", raising=False)
        # Strong JWT/SECRET_KEY → deterministic Fernet derivation (encryption still on).
        AppSettings().enforce_production_boot()
        assert (os.environ.get("ATTACHMENT_ENCRYPTION_KEY") or "").strip()

    def test_attachment_encryption_emergency_bypass_requires_attestation(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("REQUIRE_ATTACHMENT_ENCRYPTION", "false")
        monkeypatch.delenv("EMERGENCY_SECURITY_BYPASS_ATTESTATION", raising=False)
        with pytest.raises(RuntimeError, match="ATTACHMENT_ENCRYPTION_KEY"):
            AppSettings().enforce_production_boot()

    def test_attachment_encryption_emergency_bypass_with_attestation(self, monkeypatch):
        _apply_valid_production_env(monkeypatch)
        monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("REQUIRE_ATTACHMENT_ENCRYPTION", "false")
        monkeypatch.setenv(
            "EMERGENCY_SECURITY_BYPASS_ATTESTATION",
            "I_ACCEPT_PRODUCTION_PHI_RISK",
        )
        AppSettings().enforce_production_boot()
