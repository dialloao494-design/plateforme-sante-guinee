"""Production deployment verification must never seed accounts or create patients."""
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from scripts.deploy import post_deploy_verify, staging_e2e_seed


@pytest.mark.parametrize("environment,enabled", [("production", "true"), ("development", "true"), ("", "true"), ("staging", "false")])
def test_staging_seed_refuses_before_opening_database(monkeypatch, environment, enabled):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("ENABLE_STAGING_E2E_SEED", enabled)
    opened = []

    def database():
        opened.append(True)
        raise AssertionError("Disallowed seed opened database")

    monkeypatch.setattr(staging_e2e_seed, "SessionLocal", database)
    assert staging_e2e_seed.main() == 2
    assert not opened


def test_explicit_staging_seed_remains_available(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("ENABLE_STAGING_E2E_SEED", "true")
    calls = []
    monkeypatch.setattr(staging_e2e_seed, "SessionLocal", lambda: SimpleNamespace(close=lambda: calls.append("close")))
    monkeypatch.setattr(staging_e2e_seed, "_get_or_create_clinic", lambda db, name: name)
    monkeypatch.setattr(staging_e2e_seed, "_ensure_platform_admin", lambda db: calls.append("platform"))
    monkeypatch.setattr(staging_e2e_seed, "_ensure_clinic_staff", lambda db, role, clinics: calls.append(role))
    assert staging_e2e_seed.main() == 0
    assert calls[0] == "platform" and calls[-1] == "close"
    assert len(calls) == 10


def test_production_smoke_defaults_to_get_only(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["verify", "--backend", "https://backend.example.test"])
    calls = []
    monkeypatch.setattr(post_deploy_verify, "check_health", lambda url: calls.append("health"))
    monkeypatch.setattr(post_deploy_verify, "check_ready", lambda url: calls.append("ready"))

    def mutation(*args):
        raise AssertionError("Production smoke attempted authentication or patient mutation")

    monkeypatch.setattr(post_deploy_verify, "check_auth", mutation)
    monkeypatch.setattr(post_deploy_verify, "check_clinic_isolation", mutation)
    assert post_deploy_verify.main() == 0
    assert calls == ["health", "ready"]


def test_staging_smoke_requires_environment_acknowledgment(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["verify", "--backend", "https://backend.example.test", "--staging-e2e"])
    monkeypatch.setenv("DEPLOY_VERIFICATION_ENVIRONMENT", "production")
    with pytest.raises(SystemExit) as error:
        post_deploy_verify.main()
    assert error.value.code == 2


def test_staging_smoke_explicit_mode_still_runs_isolation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["verify", "--backend", "https://backend.example.test", "--staging-e2e"])
    monkeypatch.setenv("DEPLOY_VERIFICATION_ENVIRONMENT", "staging")
    calls = []
    monkeypatch.setattr(post_deploy_verify, "check_health", lambda url: None)
    monkeypatch.setattr(post_deploy_verify, "check_ready", lambda url: None)
    monkeypatch.setattr(post_deploy_verify, "check_auth", lambda *args: calls.append("auth"))
    monkeypatch.setattr(post_deploy_verify, "check_clinic_isolation", lambda url: calls.append("isolation"))
    assert post_deploy_verify.main() == 0
    assert calls == ["auth"] * len(post_deploy_verify.DEFAULT_ACCOUNTS) + ["isolation"]


def test_production_workflow_does_not_invoke_staging_seed():
    text = Path(".github/workflows/deploy-railway-vercel.yml").read_text()
    assert "staging_e2e_seed.py" not in text
