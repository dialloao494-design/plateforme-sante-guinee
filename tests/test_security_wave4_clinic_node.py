"""
Security Wave 4 — Clinic Node / mini-PC / LAN / local HTTPS / backups / encryption.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from core.clinic_node_security import (
    assert_clinic_node_secret_separation,
    clinic_compose_publishes_postgres,
    clinic_compose_uses_bridge_network,
    clinic_host_compose_binds_postgres_localhost,
    clinic_nginx_blocks_uploads,
    clinic_nginx_enforces_tls12_plus,
    clinic_nginx_redirects_http_to_https,
    env_file_permissions_are_secure,
    is_clinic_node_environment,
    pki_permissions_are_secure,
    secrets_are_distinct,
)
from core.settings import AppSettings, get_settings


ROOT = Path(__file__).resolve().parents[1]
NODE = ROOT / "deploy" / "clinic-node"


def _clear() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings():
    yield
    _clear()


def _clinic_env(monkeypatch, **extra) -> None:
    monkeypatch.setenv("ENVIRONMENT", "clinic-node")
    monkeypatch.setenv("DOMAIN", "sante-locale")
    monkeypatch.setenv("JWT_SECRET", "clinic-jwt-secret-" + "J" * 32)
    monkeypatch.setenv("SECRET_KEY", "clinic-jwt-secret-" + "J" * 32)
    monkeypatch.setenv("POSTGRES_PASSWORD", "StrongClinicDbPass!" + "Z" * 8)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://sante:StrongClinicDbPass!ZZZZZZZZ@db:5432/sante",
    )
    monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "proxy,127.0.0.1,localhost,backend")
    monkeypatch.setenv("REMINDER_RESPOND_TOKEN", "clinic-reminder-token-" + "R" * 16)
    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("CLINIC_NODE_LICENSE_SECRET", "clinic-license-secret-" + "L" * 16)
    monkeypatch.setenv("CLINIC_NODE_UPDATE_SECRET", "clinic-update-secret-" + "U" * 16)
    monkeypatch.setenv("CLINIC_NODE_NETWORK", "bridge")
    monkeypatch.setenv("ENABLE_PILOT_SEED", "false")
    monkeypatch.setenv("ENABLE_STARTUP_TEST_USER", "false")
    monkeypatch.setenv("ENABLE_STARTUP_SEED", "false")
    monkeypatch.setenv("ENABLE_DEMO_CLINIC_SEED", "false")
    for k, v in extra.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    _clear()


class TestClinicNodePackageLayout:
    def test_compose_bridge_no_postgres_publish(self):
        text = (NODE / "compose.yml").read_text(encoding="utf-8")
        assert clinic_compose_uses_bridge_network(text)
        assert not clinic_compose_publishes_postgres(text)
        assert "no-new-privileges:true" in text
        assert "ATTACHMENT_ENCRYPTION_KEY" in text

    def test_host_compose_localhost_postgres_and_lab_only(self):
        text = (NODE / "compose.host.yml").read_text(encoding="utf-8")
        assert clinic_host_compose_binds_postgres_localhost(text)
        assert "LAB ONLY" in text
        assert not clinic_compose_publishes_postgres(text)

    def test_nginx_tls_https_redirect_uploads(self):
        conf = (NODE / "proxy/app.https.conf").read_text(encoding="utf-8")
        assert clinic_nginx_enforces_tls12_plus(conf)
        assert clinic_nginx_blocks_uploads(conf)
        assert clinic_nginx_redirects_http_to_https(conf)
        assert "Strict-Transport-Security" in conf
        assert "Content-Security-Policy" in conf

    def test_security_scripts_present(self):
        for name in (
            "generate-pki.sh",
            "harden-host-firewall.sh",
            "verify-luks.sh",
            "encrypt-backup.sh",
            "decrypt-backup.sh",
            "audit-pki-perms.sh",
            "validate-clinic-node-security.sh",
        ):
            assert (NODE / "scripts" / name).is_file(), name

    def test_installer_generates_wave4_secrets(self):
        install = (NODE / "install/install.sh").read_text(encoding="utf-8")
        assert "ATTACHMENT_ENCRYPTION_KEY" in install
        assert "CLINIC_NODE_LICENSE_SECRET" in install
        assert "CLINIC_NODE_UPDATE_SECRET" in install
        assert "Fernet" in install


class TestClinicNodeBootGuards:
    def test_clinic_node_is_deployed(self, monkeypatch):
        _clinic_env(monkeypatch)
        s = AppSettings()
        assert s.is_clinic_node is True
        assert s.is_deployed is True

    def test_valid_clinic_node_boot_passes(self, monkeypatch):
        _clinic_env(monkeypatch)
        AppSettings().enforce_production_boot()

    def test_pilot_seed_forbidden(self, monkeypatch):
        _clinic_env(monkeypatch, ENABLE_PILOT_SEED="true")
        with pytest.raises(RuntimeError, match="ENABLE_PILOT_SEED"):
            AppSettings().enforce_production_boot()

    def test_missing_attachment_key_rejected(self, monkeypatch):
        _clinic_env(monkeypatch, ATTACHMENT_ENCRYPTION_KEY="")
        monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ATTACHMENT_ENCRYPTION_KEY"):
            AppSettings().enforce_production_boot()

    def test_jwt_reuse_as_license_rejected(self, monkeypatch):
        jwt = "clinic-jwt-secret-" + "J" * 32
        _clinic_env(monkeypatch, CLINIC_NODE_LICENSE_SECRET=jwt)
        with pytest.raises(RuntimeError, match="LICENSE_SECRET"):
            AppSettings().enforce_production_boot()

    def test_host_network_requires_ack(self, monkeypatch):
        _clinic_env(
            monkeypatch,
            CLINIC_NODE_NETWORK="host",
            CLINIC_NODE_ALLOW_HOST_NETWORK="false",
        )
        with pytest.raises(RuntimeError, match="host"):
            AppSettings().enforce_production_boot()

    def test_host_network_allowed_when_acked(self, monkeypatch):
        _clinic_env(
            monkeypatch,
            CLINIC_NODE_NETWORK="host",
            CLINIC_NODE_ALLOW_HOST_NETWORK="true",
        )
        AppSettings().enforce_production_boot()

    def test_jitsi_not_required_on_clinic_node(self, monkeypatch):
        _clinic_env(monkeypatch)
        monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
        monkeypatch.delenv("JITSI_SECRET", raising=False)
        AppSettings().enforce_production_boot()


class TestClinicNodeHelpers:
    def test_is_clinic_node_environment(self):
        assert is_clinic_node_environment("clinic-node") is True
        assert is_clinic_node_environment("production") is False

    def test_secret_separation(self):
        with pytest.raises(RuntimeError):
            assert_clinic_node_secret_separation(
                jwt_secret="same",
                license_secret="same",
            )
        assert_clinic_node_secret_separation(
            jwt_secret="a" * 40,
            license_secret="b" * 40,
            update_secret="c" * 40,
        )

    def test_secrets_are_distinct(self):
        assert secrets_are_distinct("a", "b", "c") is True
        assert secrets_are_distinct("a", "a") is False

    def test_pki_and_env_permission_helpers(self, tmp_path):
        pki = tmp_path / "pki"
        pki.mkdir()
        key = pki / "ca.key"
        key.write_bytes(b"x")
        key.chmod(0o644)
        ok, issues = pki_permissions_are_secure(pki)
        assert ok is False
        assert issues

        key.chmod(0o600)
        ok, _ = pki_permissions_are_secure(pki)
        assert ok is True

        env = tmp_path / ".env"
        env.write_text("x=1\n")
        env.chmod(0o644)
        ok, msg = env_file_permissions_are_secure(env)
        assert ok is False
        env.chmod(0o600)
        ok, _ = env_file_permissions_are_secure(env)
        assert ok is True


class TestBackupEncryptionScript:
    def test_encrypt_backup_script_mentions_age_and_sha(self):
        text = (NODE / "scripts/encrypt-backup.sh").read_text(encoding="utf-8")
        assert "age" in text
        assert "sha256" in text.lower() or "SHA" in text
