"""Verify Docker uvicorn launcher respects TRUSTED_PROXY_HOSTS."""

from __future__ import annotations

from pathlib import Path

from core.deploy_hardening import (
    is_railway_private_db_host,
    normalize_database_url_for_runtime,
    resolve_db_sslmode_connect_arg,
)


def test_start_uvicorn_script_uses_trusted_proxy_hosts_not_wildcard():
    script = Path("scripts/docker/start-uvicorn.sh").read_text(encoding="utf-8")
    assert "TRUSTED_PROXY_HOSTS" in script
    assert 'forwarded-allow-ips "*"' not in script
    assert "forwarded-allow-ips" in script


def test_railway_json_clears_stale_start_command_override():
    import json

    cfg = json.loads(Path("railway.json").read_text(encoding="utf-8"))
    assert cfg["build"]["builder"] == "DOCKERFILE"
    assert cfg["deploy"]["startCommand"] is None
    assert cfg["deploy"]["healthcheckPath"] is None
    # Ensure obsolete railway.toml with invalid TOML null is not reintroduced.
    assert not Path("railway.toml").exists()


def test_normalize_strips_sslmode_on_railway_private_mesh():
    raw = (
        "postgresql://u:p@postgres.railway.internal:5432/railway"
        "?sslmode=require&application_name=web"
    )
    fixed = normalize_database_url_for_runtime(raw)
    assert "sslmode" not in fixed
    assert "postgres.railway.internal" in fixed
    assert "application_name=web" in fixed
    assert is_railway_private_db_host("postgres.railway.internal")


def test_normalize_keeps_sslmode_on_public_hosts():
    raw = "postgresql://u:p@maglev.proxy.rlwy.net:1234/railway?sslmode=require"
    fixed = normalize_database_url_for_runtime(raw)
    assert "sslmode=require" in fixed


def test_resolve_sslmode_connect_arg_skips_private_mesh(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("DB_SSLMODE", raising=False)
    url = "postgresql://u:p@postgres.railway.internal:5432/railway?sslmode=require"
    assert resolve_db_sslmode_connect_arg(url) is None


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

