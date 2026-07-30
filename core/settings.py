"""
Centralized environment settings for production, staging, and development.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from urllib.parse import unquote, urlparse


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _first_env(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def _password_from_database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    return unquote(parsed.password or "")


def _is_jaas_jitsi_mode() -> bool:
    app_id = (os.getenv("JITSI_APP_ID") or "").strip()
    if app_id.startswith("vpaas-magic-cookie-"):
        return True
    return (os.getenv("JITSI_JAAS") or "").lower() in {"1", "true", "yes", "on"}


def _resolve_jitsi_secret() -> str:
    if _is_jaas_jitsi_mode():
        path = (os.getenv("JITSI_PRIVATE_KEY_PATH") or "").strip()
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                return handle.read().strip()
        return (os.getenv("JITSI_PRIVATE_KEY") or "").replace("\\n", "\n").strip()
    return _first_env("JITSI_SECRET", "JITSI_APP_SECRET", "JITSI_APP_KEY")


_WEAK_SECRET_PATTERNS = re.compile(
    r"(changeme|change-me|change_me|default|demo|placeholder|your_|"
    r"sante_dev|pytest|example\.com|sk_test_|sk_live_YOUR|CHANGE_ME|"
    r"password123|secret12|test-secret)",
    re.IGNORECASE,
)


def is_insecure_secret(
    value: str,
    *,
    min_length: int = 16,
    extra_weak_tokens: tuple[str, ...] = (),
) -> bool:
    """Return True when a secret is empty, too short, or matches known-weak patterns."""
    cleaned = (value or "").strip()
    if not cleaned or len(cleaned) < min_length:
        return True
    if _WEAK_SECRET_PATTERNS.search(cleaned):
        return True
    lowered = cleaned.lower()
    for token in extra_weak_tokens:
        if token and token.lower() in lowered:
            return True
    if lowered in {"test", "demo", "default", "password", "secret"}:
        return True
    return False


@lru_cache(maxsize=1)
def get_settings() -> "AppSettings":
    return AppSettings()


class AppSettings:
    def __init__(self) -> None:
        self.environment = (os.getenv("ENVIRONMENT") or "development").lower().strip()
        self.debug = _env_flag("DEBUG", default=False)
        self.is_production = self.environment == "production"
        self.is_staging = self.environment == "staging"
        # Local Clinic Node appliance (offline-first). Isolated from Railway/Vercel.
        self.is_clinic_node = self.environment in {"clinic-node", "clinic_node"}
        # Deployed = hardened secrets/proxy rules (cloud staging/prod OR local node).
        self.is_deployed = self.is_production or self.is_staging or self.is_clinic_node
        self.domain = (os.getenv("DOMAIN") or "").strip()
        self.log_level = (os.getenv("LOG_LEVEL") or ("INFO" if self.is_deployed else "DEBUG")).upper()
        self.log_format = (os.getenv("LOG_FORMAT") or ("json" if self.is_deployed else "text")).lower()
        self.sentry_dsn = (os.getenv("SENTRY_DSN") or "").strip()
        self.disable_api_docs = _env_flag("DISABLE_API_DOCS", default=False)
        self.docs_enabled = not self.is_production and not self.disable_api_docs
        if self.is_staging and _env_flag("ENABLE_STAGING_API_DOCS", default=False):
            self.docs_enabled = True
        if self.is_clinic_node and _env_flag("ENABLE_CLINIC_NODE_API_DOCS", default=False):
            self.docs_enabled = True

    def resolve_allowed_hosts(self) -> list[str]:
        raw = (os.getenv("ALLOWED_HOSTS") or "").strip()
        if not self.is_deployed:
            if not raw or raw == "*":
                return ["*"]
            return [h.strip() for h in raw.split(",") if h.strip()]

        hosts: list[str] = []
        if self.domain:
            hosts.append(self.domain)
            if self.domain.startswith("www."):
                hosts.append(self.domain[4:])
            else:
                hosts.append(f"www.{self.domain}")

        for part in raw.split(","):
            part = part.strip()
            if part and part != "*" and part not in hosts:
                hosts.append(part)

        for internal in ("backend", "localhost", "127.0.0.1"):
            if internal not in hosts:
                hosts.append(internal)

        if self.is_clinic_node:
            for local_host in ("sante-locale", "proxy", "*.local"):
                if local_host not in hosts:
                    hosts.append(local_host)

        # Railway edge + health probe hosts (required for deploy healthchecks).
        if os.getenv("RAILWAY_ENVIRONMENT"):
            for railway_host in (
                "healthcheck.railway.app",
                "*.up.railway.app",
            ):
                if railway_host not in hosts:
                    hosts.append(railway_host)
            public_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
            if public_domain and public_domain not in hosts:
                hosts.append(public_domain)

        if not hosts or (len(hosts) <= 3 and not self.domain and not raw.replace("*", "").strip()):
            raise RuntimeError(
                "ALLOWED_HOSTS or DOMAIN must be set for staging/production/clinic-node "
                "(e.g. ALLOWED_HOSTS=staging.example.com,backend)"
            )
        return hosts

    def resolve_trusted_proxy_hosts(self) -> list[str]:
        """
        Hosts allowed to set X-Forwarded-* via ProxyHeadersMiddleware.
        Never use '*' in staging/production — restrict to the reverse proxy.
        """
        raw = (os.getenv("TRUSTED_PROXY_HOSTS") or "").strip()
        if not self.is_deployed:
            if not raw or raw == "*":
                return ["127.0.0.1", "localhost", "::1"]
            return [h.strip() for h in raw.split(",") if h.strip()]

        # Railway edge terminates TLS; private CIDRs + loopback are safe defaults
        # when the operator has not yet set TRUSTED_PROXY_HOSTS explicitly.
        if (not raw or raw == "*") and (os.getenv("RAILWAY_ENVIRONMENT") or "").strip():
            raw = "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,::1,backend"
            os.environ["TRUSTED_PROXY_HOSTS"] = raw

        hosts: list[str] = []
        for part in raw.split(","):
            part = part.strip()
            if part and part != "*" and part not in hosts:
                hosts.append(part)

        for internal in ("127.0.0.1", "localhost", "::1", "backend"):
            if internal not in hosts:
                hosts.append(internal)

        if not raw or raw == "*":
            raise RuntimeError(
                "TRUSTED_PROXY_HOSTS must list your reverse proxy IPs/hostnames in "
                "staging/production (never '*')"
            )
        return hosts

    def validate_production_secrets(self) -> None:
        """Validate required secrets for staging/production deployments."""
        if not self.is_deployed:
            return

        jwt_secret = _first_env("JWT_SECRET", "SECRET_KEY")
        # Prefer the password embedded in DATABASE_URL (Railway Postgres plugin).
        # A leftover weak POSTGRES_PASSWORD env must not override a strong URL password.
        url_password = _password_from_database_url()
        explicit_password = _first_env("DB_PASSWORD", "POSTGRES_PASSWORD")
        if url_password:
            db_password = url_password
        else:
            db_password = explicit_password
        jitsi_secret = _resolve_jitsi_secret()

        failures: list[str] = []

        if is_insecure_secret(jwt_secret, min_length=32):
            failures.append("JWT_SECRET/SECRET_KEY must be a strong random value (32+ chars)")

        if is_insecure_secret(db_password, min_length=12, extra_weak_tokens=("sante_dev", "postgres")):
            failures.append("DB_PASSWORD/POSTGRES_PASSWORD must be a strong database password")

        # Teleconsult/Jitsi is optional on Clinic Node (LAN offline V1).
        if not self.is_clinic_node:
            jitsi_min = 16 if _is_jaas_jitsi_mode() else 12
            if is_insecure_secret(jitsi_secret, min_length=jitsi_min):
                failures.append(
                    "JITSI_SECRET/JITSI_APP_SECRET (or JaaS private key) must be configured securely"
                )

        reminder_token = (os.getenv("REMINDER_RESPOND_TOKEN") or "").strip()
        if self.is_production and is_insecure_secret(reminder_token, min_length=32):
            failures.append(
                "REMINDER_RESPOND_TOKEN must be a strong random value (32+ chars) in production"
            )
        if self.is_clinic_node and reminder_token and is_insecure_secret(reminder_token, min_length=32):
            failures.append(
                "REMINDER_RESPOND_TOKEN must be a strong random value (32+ chars) when set on clinic-node"
            )

        # PHI attachment encryption — required in production (no silent kill-switch)
        if self.is_production:
            enc_key = (os.getenv("ATTACHMENT_ENCRYPTION_KEY") or "").strip()
            bypass = not _env_flag("REQUIRE_ATTACHMENT_ENCRYPTION", default=True)
            attested = (
                os.getenv("EMERGENCY_SECURITY_BYPASS_ATTESTATION", "").strip()
                == "I_ACCEPT_PRODUCTION_PHI_RISK"
            )
            if (
                not enc_key
                and not bypass
                and jwt_secret
                and not is_insecure_secret(jwt_secret, min_length=32)
            ):
                # Auto-provision a Fernet key derived from the strong app secret so
                # PHI stays encrypted when Railway has no separate encryption var yet.
                # Prefer an explicit ATTACHMENT_ENCRYPTION_KEY for independent rotation.
                try:
                    import base64
                    import hashlib
                    import logging

                    digest = hashlib.sha256(
                        b"sante-guinee-attachment-v1:" + jwt_secret.encode("utf-8")
                    ).digest()
                    derived = base64.urlsafe_b64encode(digest).decode("ascii")
                    from cryptography.fernet import Fernet

                    Fernet(derived.encode("utf-8"))
                    os.environ["ATTACHMENT_ENCRYPTION_KEY"] = derived
                    enc_key = derived
                    logging.getLogger(__name__).warning(
                        "ATTACHMENT_ENCRYPTION_KEY was missing; derived a Fernet key from "
                        "JWT_SECRET/SECRET_KEY. Set an explicit ATTACHMENT_ENCRYPTION_KEY "
                        "in Railway for independent key rotation."
                    )
                except Exception:
                    enc_key = ""
            if enc_key:
                try:
                    from cryptography.fernet import Fernet

                    Fernet(enc_key.encode("utf-8"))
                except Exception:
                    failures.append(
                        "ATTACHMENT_ENCRYPTION_KEY must be a valid Fernet key when set"
                    )
            else:
                if not (bypass and attested):
                    failures.append(
                        "ATTACHMENT_ENCRYPTION_KEY must be set in production "
                        "(to disable temporarily set REQUIRE_ATTACHMENT_ENCRYPTION=false "
                        "AND EMERGENCY_SECURITY_BYPASS_ATTESTATION=I_ACCEPT_PRODUCTION_PHI_RISK)"
                    )

        # TLS to Postgres — reject sslmode=disable; require SSL on Railway production
        try:
            from core.deploy_hardening import assert_database_tls_policy

            allow_insecure = _env_flag("ALLOW_INSECURE_DB_SSL", default=False) and (
                os.getenv("EMERGENCY_SECURITY_BYPASS_ATTESTATION", "").strip()
                == "I_ACCEPT_PRODUCTION_PHI_RISK"
            )
            assert_database_tls_policy(
                os.getenv("DATABASE_URL") or "",
                is_production=self.is_production,
                railway_environment=os.getenv("RAILWAY_ENVIRONMENT"),
                allow_insecure_db_ssl=allow_insecure,
            )
        except RuntimeError as exc:
            failures.append(str(exc))

        if failures:
            raise RuntimeError("Insecure deployment secrets: " + "; ".join(failures))

    def enforce_production_boot(self) -> None:
        """Run all boot guards: production ops flags + deployed secret validation."""
        if self.is_production:
            if _env_flag("ENABLE_PILOT_SEED", default=False):
                raise RuntimeError(
                    "ENABLE_PILOT_SEED=true is forbidden in production — "
                    "remove pilot/demo accounts before go-live"
                )

            if _env_flag("ENABLE_STARTUP_TEST_USER", default=False):
                raise RuntimeError(
                    "ENABLE_STARTUP_TEST_USER=true is forbidden in production — "
                    "remove weak startup test accounts before go-live"
                )

            if _env_flag("ENABLE_STARTUP_SEED", default=False):
                raise RuntimeError(
                    "ENABLE_STARTUP_SEED=true is forbidden in production — "
                    "dev seed routines must remain disabled"
                )

            if _env_flag("ENABLE_DEMO_CLINIC_SEED", default=False):
                raise RuntimeError(
                    "ENABLE_DEMO_CLINIC_SEED=true is forbidden in production — "
                    "demo datasets must remain disabled"
                )

            bypass_raw = (os.getenv("BYPASS_AVAILABILITY_VALIDATION") or "false").strip().lower()
            if bypass_raw in {"1", "true", "yes", "on"}:
                raise RuntimeError(
                    "BYPASS_AVAILABILITY_VALIDATION=true is forbidden in production — "
                    "doctor availability checks must remain enforced"
                )

        if self.is_clinic_node:
            # Clinic Node forbids cloud demo/test seeds; local bootstrap uses dedicated flags later.
            for flag in (
                "ENABLE_PILOT_SEED",
                "ENABLE_STARTUP_TEST_USER",
                "ENABLE_STARTUP_SEED",
                "ENABLE_DEMO_CLINIC_SEED",
            ):
                if _env_flag(flag, default=False):
                    raise RuntimeError(
                        f"{flag}=true is forbidden on clinic-node — "
                        "use the Clinic Node installer bootstrap instead"
                    )

        if self.is_deployed:
            self.validate_production_secrets()
            self.resolve_trusted_proxy_hosts()
