"""Verify Docker uvicorn launcher respects TRUSTED_PROXY_HOSTS."""

from __future__ import annotations

from pathlib import Path


def test_start_uvicorn_script_uses_trusted_proxy_hosts_not_wildcard():
    script = Path("scripts/docker/start-uvicorn.sh").read_text(encoding="utf-8")
    assert "TRUSTED_PROXY_HOSTS" in script
    assert 'forwarded-allow-ips "*"' not in script
    assert "forwarded-allow-ips" in script


def test_bootstrap_autonomous_script_sets_trusted_proxy_and_reminder_token():
    script = Path("deploy/vps/bootstrap-autonomous.sh").read_text(encoding="utf-8")
    assert "TRUSTED_PROXY_HOSTS=" in script
    assert "REMINDER_RESPOND_TOKEN=" in script
    assert "TRUSTED_PROXIES=" in script


def test_backend_env_example_has_security_vars():
    example = Path("deploy/env/.env.backend.example").read_text(encoding="utf-8")
    assert "TRUSTED_PROXY_HOSTS=" in example
    assert "REMINDER_RESPOND_TOKEN=" in example
    assert "ENABLE_STARTUP_TEST_USER=false" in example

