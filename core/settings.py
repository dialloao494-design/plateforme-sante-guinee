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
        # Local Clinic Node appliance (offline-first mini-PC). Isolated from Railway/Vercel.
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
        """Validate required secrets for staging/production/clinic-node deployments."""
        if not self.is_deployed:
            return

        jwt_secret = _first_env("JWT_SECRET", "SECRET_KEY")
        db_password = _first_env("DB_PASSWORD", "POSTGRES_PASSWORD") or _password_from_database_url()
        jitsi_secret = _resolve_jitsi_secret()

        failures: list[str] = []

        if is_insecure_secret(jwt_secret, min_length=32):
            failures.append("JWT_SECRET/SECRET_KEY must be a strong random value (32+ chars)")

        if is_insecure_secret(db_password, min_length=12, extra_weak_tokens=("sante_dev", "postgres")):
            failures.append("DB_PASSWORD/POSTGRES_PASSWORD must be a strong database password")

        # Teleconsult/Jitsi is optional on Clinic Node (LAN offline).
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

        # PHI attachments — required on production and clinic-node (Wave 2/4).
        if self.is_production or self.is_clinic_node:
            enc_key = (os.getenv("ATTACHMENT_ENCRYPTION_KEY") or "").strip()
            require_enc = _env_flag(
                "REQUIRE_ATTACHMENT_ENCRYPTION",
                default=True,
            )
            if not enc_key and require_enc:
                failures.append(
                    "ATTACHMENT_ENCRYPTION_KEY must be set "
                    f"(Fernet key for PHI at rest on {'clinic-node' if self.is_clinic_node else 'production'})"
                )
            elif enc_key:
                try:
                    from cryptography.fernet import Fernet

                    Fernet(enc_key.encode("utf-8"))
                except Exception:
                    failures.append("ATTACHMENT_ENCRYPTION_KEY must be a valid Fernet key")

        if self.is_clinic_node:
            try:
                from core.clinic_node_security import assert_clinic_node_secret_separation

                assert_clinic_node_secret_separation(
                    jwt_secret=jwt_secret,
                    license_secret=os.getenv("CLINIC_NODE_LICENSE_SECRET") or "",
                    update_secret=os.getenv("CLINIC_NODE_UPDATE_SECRET") or "",
                    attachment_key=os.getenv("ATTACHMENT_ENCRYPTION_KEY") or "",
                )
            except RuntimeError as exc:
                failures.append(str(exc))

            # Host-network is lab-only for pilots unless explicitly acknowledged.
            network = (os.getenv("CLINIC_NODE_NETWORK") or "bridge").strip().lower()
            if network == "host" and not _env_flag("CLINIC_NODE_ALLOW_HOST_NETWORK", default=False):
                failures.append(
                    "CLINIC_NODE_NETWORK=host is lab-only — set CLINIC_NODE_ALLOW_HOST_NETWORK=true "
                    "to acknowledge LAN exposure risk, or use bridge networking"
                )

        if failures:
            raise RuntimeError("Insecure deployment secrets: " + "; ".join(failures))

    def enforce_production_boot(self) -> None:
        """Run all boot guards: production/clinic-node ops flags + deployed secret validation."""
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
