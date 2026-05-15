"""
Centralized environment settings for production, staging, and development.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_settings() -> "AppSettings":
    return AppSettings()


class AppSettings:
    def __init__(self) -> None:
        self.environment = (os.getenv("ENVIRONMENT") or "development").lower().strip()
        self.debug = _env_flag("DEBUG", default=False)
        self.is_production = self.environment == "production"
        self.is_staging = self.environment == "staging"
        self.is_deployed = self.is_production or self.is_staging
        self.domain = (os.getenv("DOMAIN") or "").strip()
        self.log_level = (os.getenv("LOG_LEVEL") or ("INFO" if self.is_deployed else "DEBUG")).upper()
        self.log_format = (os.getenv("LOG_FORMAT") or ("json" if self.is_deployed else "text")).lower()
        self.sentry_dsn = (os.getenv("SENTRY_DSN") or "").strip()
        self.disable_api_docs = _env_flag("DISABLE_API_DOCS", default=False)
        self.docs_enabled = not self.is_production and not self.disable_api_docs
        if self.is_staging and _env_flag("ENABLE_STAGING_API_DOCS", default=False):
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

        if not hosts or (len(hosts) <= 3 and not self.domain and not raw.replace("*", "").strip()):
            raise RuntimeError(
                "ALLOWED_HOSTS or DOMAIN must be set for staging/production "
                "(e.g. ALLOWED_HOSTS=staging.example.com,backend)"
            )
        return hosts

    def validate_production_secrets(self) -> None:
        if not self.is_deployed:
            return
        sk = os.getenv("SECRET_KEY", "")
        if not sk or sk.startswith("change-me") or len(sk) < 32:
            raise RuntimeError("SECRET_KEY must be a strong random value (32+ chars) in staging/production")
