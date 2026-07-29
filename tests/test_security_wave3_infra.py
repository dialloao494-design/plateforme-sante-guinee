"""
Security Wave 3 — Docker, Postgres TLS, Railway, Vercel, Nginx, secrets, headers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.deploy_hardening import (
    assert_database_tls_policy,
    compose_publishes_postgres,
    database_url_sslmode,
    dockerfile_runs_as_non_root,
    nginx_blocks_uploads,
    nginx_enforces_tls12_plus,
    postgres_password_is_weak,
    vercel_has_security_headers,
)
from core.security_headers import SecurityHeadersMiddleware


ROOT = Path(__file__).resolve().parents[1]


class TestDockerHardening:
    def test_backend_dockerfile_drops_to_non_root(self):
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert dockerfile_runs_as_non_root(text)
        assert "gosu" in text
        assert "appuser" in text
        assert "HEALTHCHECK" in text

    def test_entrypoint_drops_privileges(self):
        text = (ROOT / "scripts/docker/entrypoint-backend.sh").read_text(encoding="utf-8")
        assert "gosu appuser" in text
        assert "Dropping privileges" in text

    def test_compose_requires_postgres_password_and_no_host_publish(self):
        base = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        prod = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        assert "POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD" in base or "POSTGRES_PASSWORD:?" in base
        assert "no-new-privileges:true" in base
        assert "cap_drop:" in base
        assert "read_only: true" in base
        assert not compose_publishes_postgres(base)
        assert not compose_publishes_postgres(prod)
        assert "ATTACHMENT_ENCRYPTION_KEY" in prod

    def test_pilot_documents_lab_only_postgres_publish(self):
        pilot = (ROOT / "docker-compose.pilot.yml").read_text(encoding="utf-8")
        assert "LAB ONLY" in pilot or "Lab-only" in pilot
        assert compose_publishes_postgres(pilot)


class TestPostgresTlsPolicy:
    def test_sslmode_disable_rejected_in_production(self):
        with pytest.raises(RuntimeError, match="sslmode=disable"):
            assert_database_tls_policy(
                "postgresql://u:p@db/sante?sslmode=disable",
                is_production=True,
            )

    def test_railway_requires_sslmode(self):
        with pytest.raises(RuntimeError, match="sslmode=require"):
            assert_database_tls_policy(
                "postgresql://u:strongpassword12@db/sante",
                is_production=True,
                railway_environment="production",
            )

    def test_railway_accepts_require(self):
        assert_database_tls_policy(
            "postgresql://u:strongpassword12@db/sante?sslmode=require",
            is_production=True,
            railway_environment="production",
        )

    def test_compose_internal_production_without_railway_ok(self):
        assert_database_tls_policy(
            "postgresql://u:strongpassword12@db/sante",
            is_production=True,
            railway_environment=None,
        )

    def test_parse_sslmode(self):
        assert database_url_sslmode("postgresql://u:p@h/db?sslmode=require") == "require"
        assert database_url_sslmode("sqlite:///x.db") is None

    def test_weak_password_detection(self):
        assert postgres_password_is_weak("sante_dev_password") is True
        assert postgres_password_is_weak("StrongProductionDb!ZZZZZZZZ") is False


class TestNginxTlsAndUploads:
    def test_prod_template_tls_and_uploads(self):
        conf = (ROOT / "deploy/nginx/conf.d/app.conf.template").read_text(encoding="utf-8")
        assert nginx_enforces_tls12_plus(conf)
        assert nginx_blocks_uploads(conf)
        assert "Strict-Transport-Security" in conf
        assert "Content-Security-Policy" in conf
        assert 'return 301 https://' in conf

    def test_http_only_still_blocks_uploads(self):
        conf = (ROOT / "deploy/nginx/conf.d/app.http-only.conf").read_text(encoding="utf-8")
        assert nginx_blocks_uploads(conf)


class TestVercelAndRailway:
    def test_vercel_security_headers(self):
        text = (ROOT / "frontend-sante/frontend/vercel.json").read_text(encoding="utf-8")
        assert vercel_has_security_headers(text)

    def test_railway_healthcheck_configured(self):
        text = (ROOT / "railway.toml").read_text(encoding="utf-8")
        assert "healthcheckPath" in text
        assert "/health/ready" in text
        assert 'builder = "DOCKERFILE"' in text

    def test_env_templates_document_wave3_secrets(self):
        prod = (ROOT / ".env.production.example").read_text(encoding="utf-8")
        railway = (ROOT / "deploy/railway-vercel.env.template").read_text(encoding="utf-8")
        backend = (ROOT / "deploy/env/.env.backend.example").read_text(encoding="utf-8")
        assert "ATTACHMENT_ENCRYPTION_KEY" in prod
        assert "JWT_SECRET" in prod
        assert "sslmode=require" in railway or "DB_SSLMODE=require" in railway
        assert "ATTACHMENT_ENCRYPTION_KEY" in backend
        assert "JWT_SECRET" in backend


class TestFastapiSecurityHeaders:
    def test_health_response_includes_security_headers(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert "frame-ancestors" in (response.headers.get("content-security-policy") or "")

    def test_hsts_when_forwarded_proto_https(self, client):
        response = client.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert response.status_code == 200
        assert "max-age=" in (response.headers.get("strict-transport-security") or "")

    def test_middleware_class_exported(self):
        assert SecurityHeadersMiddleware is not None
