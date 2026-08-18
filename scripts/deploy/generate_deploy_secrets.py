#!/usr/bin/env python3
"""Generate secrets and Railway/Vercel env var blocks for staging deployment."""

from __future__ import annotations

import secrets
import textwrap


def _token(n: int = 32) -> str:
    return secrets.token_urlsafe(n)


def main() -> None:
    jwt = _token(48)
    jitsi = _token(24)
    reminder = _token(48)

    railway_vars = textwrap.dedent(
        f"""
        # --- Railway backend service variables ---
        ENVIRONMENT=staging
        DEBUG=false
        ENABLE_STAGING_API_DOCS=true
        ENABLE_STAGING_E2E_SEED=true
        ENABLE_PILOT_SEED=false
        ENABLE_STARTUP_TEST_USER=false
        ENABLE_STARTUP_SEED=false
        ALLOWED_HOSTS=*.up.railway.app,backend,localhost,127.0.0.1
        TRUSTED_PROXY_HOSTS=127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,backend
        SECRET_KEY={jwt}
        JWT_SECRET={jwt}
        JITSI_SECRET={jitsi}
        REMINDER_RESPOND_TOKEN={reminder}
        ALLOW_STUB_PAYMENT=true
        BYPASS_AVAILABILITY_VALIDATION=false
        LOG_FORMAT=json
        LOG_LEVEL=INFO
        # Link PostgreSQL plugin variable in Railway dashboard:
        # DATABASE_URL=${{Postgres.DATABASE_URL}}
        """
    ).strip()

    vercel_vars = textwrap.dedent(
        """
        # --- Vercel frontend project variables ---
        VITE_API_URL=https://YOUR-RAILWAY-BACKEND.up.railway.app
        VITE_TELECONSULT_PROVIDER=jitsi
        """
    ).strip()

    print("=" * 72)
    print("RAILWAY BACKEND ENV (paste in Railway -> Service -> Variables)")
    print("=" * 72)
    print(railway_vars)
    print()
    print("=" * 72)
    print("VERCEL FRONTEND ENV (paste in Vercel -> Project -> Environment Variables)")
    print("=" * 72)
    print(vercel_vars)
    print()
    print("Replace YOUR-RAILWAY-BACKEND with the public Railway hostname after first deploy.")
    print("Then set FRONTEND_URL / CORS_ORIGINS on Railway to your Vercel URL.")


if __name__ == "__main__":
    main()
