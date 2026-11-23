"""Clinic Node (ENVIRONMENT=clinic-node) settings and isolation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.frontend_url import resolve_frontend_url
from core.settings import AppSettings, get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    yield
    _clear_settings_cache()


def _apply_valid_clinic_node_env(monkeypatch) -> None:
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENVIRONMENT", "clinic-node")
    monkeypatch.setenv("DOMAIN", "sante-locale")
    monkeypatch.setenv("JWT_SECRET", "clinic-node-jwt-secret-" + "A" * 32)
    monkeypatch.setenv("SECRET_KEY", "clinic-node-jwt-secret-" + "A" * 32)
    monkeypatch.setenv("POSTGRES_PASSWORD", "StrongClinicNodeDb!" + "Z" * 8)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://sante:StrongClinicNodeDb!" + "Z" * 8 + "@db:5432/sante",
    )
    monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "proxy,127.0.0.1,localhost,backend")
    monkeypatch.setenv("ALLOWED_HOSTS", "sante-locale,localhost,127.0.0.1,backend,proxy")
    monkeypatch.setenv("FRONTEND_URL", "https://sante-locale")
    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("CLINIC_NODE_LICENSE_SECRET", "node-license-independent-" + "L" * 32)
    monkeypatch.setenv("CLINIC_NODE_UPDATE_SECRET", "node-update-independent-" + "U" * 32)
    monkeypatch.setenv("CLINIC_NODE_NETWORK", "bridge")
    monkeypatch.setenv("ENABLE_PILOT_SEED", "false")
    monkeypatch.setenv("ENABLE_STARTUP_TEST_USER", "false")
    monkeypatch.setenv("ENABLE_STARTUP_SEED", "false")
    monkeypatch.setenv("ENABLE_DEMO_CLINIC_SEED", "false")
    _clear_settings_cache()


class TestClinicNodeSettings:
    @pytest.mark.parametrize("name", ["CLINIC_NODE_LICENSE_SECRET", "CLINIC_NODE_UPDATE_SECRET"])
    @pytest.mark.parametrize("value", [None, "", "too-short"])
    def test_clinic_node_requires_dedicated_license_and_update_secrets(self, monkeypatch, name, value):
        _apply_valid_clinic_node_env(monkeypatch)
        if value is None:
            monkeypatch.delenv(name)
        else:
            monkeypatch.setenv(name, value)
        with pytest.raises(RuntimeError, match=name):
            AppSettings().enforce_production_boot()

    @pytest.mark.parametrize("key", [None, "invalid-fernet-key"])
    def test_clinic_node_requires_valid_explicit_attachment_key(self, monkeypatch, key):
        _apply_valid_clinic_node_env(monkeypatch)
        if key is None:
            monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY")
        else:
            monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", key)
        with pytest.raises(RuntimeError, match="ATTACHMENT_ENCRYPTION_KEY"):
            AppSettings().enforce_production_boot()

    def test_clinic_node_rejects_encryption_bypass(self, monkeypatch):
        _apply_valid_clinic_node_env(monkeypatch)
        monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY")
        monkeypatch.setenv("REQUIRE_ATTACHMENT_ENCRYPTION", "false")
        monkeypatch.setenv("EMERGENCY_SECURITY_BYPASS_ATTESTATION", "I_ACCEPT_PRODUCTION_PHI_RISK")
        with pytest.raises(RuntimeError, match="ATTACHMENT_ENCRYPTION_KEY"):
            AppSettings().enforce_production_boot()

    @pytest.mark.parametrize("name", ["CLINIC_NODE_LICENSE_SECRET", "CLINIC_NODE_UPDATE_SECRET", "ATTACHMENT_ENCRYPTION_KEY"])
    def test_clinic_node_rejects_signing_key_reuse(self, monkeypatch, name):
        from cryptography.fernet import Fernet

        _apply_valid_clinic_node_env(monkeypatch)
        key = Fernet.generate_key().decode("ascii")
        monkeypatch.setenv("JWT_SECRET", key)
        monkeypatch.setenv("SECRET_KEY", key)
        monkeypatch.setenv(name, key)
        with pytest.raises(RuntimeError, match=name):
            AppSettings().enforce_production_boot()

    def test_clinic_node_rejects_shared_license_update_secret(self, monkeypatch):
        _apply_valid_clinic_node_env(monkeypatch)
        monkeypatch.setenv("CLINIC_NODE_UPDATE_SECRET", "node-license-independent-" + "L" * 32)
        with pytest.raises(RuntimeError, match="CLINIC_NODE_UPDATE_SECRET"):
            AppSettings().enforce_production_boot()

    def test_clinic_node_host_network_requires_acknowledgment(self, monkeypatch):
        _apply_valid_clinic_node_env(monkeypatch)
        monkeypatch.setenv("CLINIC_NODE_NETWORK", "host")
        monkeypatch.setenv("CLINIC_NODE_ALLOW_HOST_NETWORK", "false")
        with pytest.raises(RuntimeError, match="CLINIC_NODE_ALLOW_HOST_NETWORK"):
            AppSettings().enforce_production_boot()
        monkeypatch.setenv("CLINIC_NODE_ALLOW_HOST_NETWORK", "true")
        AppSettings().enforce_production_boot()

    def test_clinic_node_flags(self, monkeypatch):
        _apply_valid_clinic_node_env(monkeypatch)
        settings = AppSettings()
        assert settings.is_clinic_node is True
        assert settings.is_production is False
        assert settings.is_staging is False
        assert settings.is_deployed is True

    def test_clinic_node_boot_ok_without_jitsi(self, monkeypatch):
        _apply_valid_clinic_node_env(monkeypatch)
        monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
        monkeypatch.delenv("JITSI_SECRET", raising=False)
        settings = AppSettings()
        settings.enforce_production_boot()

    def test_clinic_node_rejects_demo_seeds(self, monkeypatch):
        _apply_valid_clinic_node_env(monkeypatch)
        monkeypatch.setenv("ENABLE_DEMO_CLINIC_SEED", "true")
        settings = AppSettings()
        with pytest.raises(RuntimeError, match="ENABLE_DEMO_CLINIC_SEED"):
            settings.enforce_production_boot()

    def test_clinic_node_allowed_hosts_include_sante_locale(self, monkeypatch):
        _apply_valid_clinic_node_env(monkeypatch)
        settings = AppSettings()
        hosts = settings.resolve_allowed_hosts()
        assert "sante-locale" in hosts
        assert "backend" in hosts

    def test_production_guards_unchanged(self, monkeypatch):
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
        monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "127.0.0.1,backend")
        monkeypatch.setenv("REMINDER_RESPOND_TOKEN", "reminder-respond-token-" + "R" * 32)
        monkeypatch.setenv("ENABLE_PILOT_SEED", "true")
        _clear_settings_cache()
        settings = AppSettings()
        assert settings.is_clinic_node is False
        with pytest.raises(RuntimeError, match="ENABLE_PILOT_SEED"):
            settings.enforce_production_boot()

    def test_frontend_url_clinic_node_not_vercel(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "clinic-node")
        monkeypatch.delenv("FRONTEND_URL", raising=False)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        assert resolve_frontend_url(allow_localhost_fallback=False) == "https://sante-locale"


class TestClinicNodeDeployAssets:
    def test_compose_and_installer_exist(self):
        root = Path("deploy/clinic-node")
        assert (root / "compose.yml").is_file()
        assert (root / "install" / "install.sh").is_file()
        assert (root / "scripts" / "generate-pki.sh").is_file()
        assert (root / "scripts" / "validate-reboot-safe.sh").is_file()
        assert (root / "proxy" / "app.https.conf").is_file()
        assert (root / "systemd" / "clinic-node.service").is_file()
        assert (root / "README.md").is_file()

    def test_compose_uses_isolated_project_name(self):
        text = Path("deploy/clinic-node/compose.yml").read_text(encoding="utf-8")
        assert "name: clinic-node" in text
        assert "ENVIRONMENT: clinic-node" in text
        assert "restart: unless-stopped" in text

    def test_installer_is_executable_happy_path(self):
        script = Path("deploy/clinic-node/install/install.sh").read_text(encoding="utf-8")
        assert "generate-pki.sh" in script
        assert "up -d --build" in script
        assert "health/ready" in script
