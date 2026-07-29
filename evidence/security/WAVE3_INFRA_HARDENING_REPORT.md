# Santé Guinée — Security Wave 3 Report

**Wave:** 3 — Docker / PostgreSQL / Railway / Vercel / Nginx / FastAPI deploy / Secrets / Env / TLS / HTTPS / Certificates  
**Status:** COMPLETE  
**Date:** 2026-07-29  
**Branch:** `cursor/security-wave3-infra-ab76`

---

## 1. Implemented protections

| Area | Implementation |
|------|----------------|
| **Docker** | Non-root `appuser` via `gosu` in entrypoint; `no-new-privileges`; `cap_drop: ALL`; `read_only` + tmpfs; required `POSTGRES_PASSWORD` (no weak default); Postgres not published on host in base/prod |
| **PostgreSQL** | Weak password rejection at boot; Railway production requires `sslmode=require`; `DB_SSLMODE` connect arg support; compose-internal TLS optional |
| **Railway** | `railway.toml` healthcheck `/health/ready`; env template production checklist + SSL notes |
| **Vercel** | CSP, HSTS, X-Frame-Options DENY, COOP, Permissions-Policy in `vercel.json` |
| **Nginx** | TLS 1.2/1.3 only; HSTS; CSP; `/uploads/` → 403; HTTP→HTTPS redirect; session tickets off |
| **FastAPI** | `SecurityHeadersMiddleware` (nosniff, DENY frame, CSP, HSTS on HTTPS/`X-Forwarded-Proto`) |
| **Secrets / env** | Production requires `ATTACHMENT_ENCRYPTION_KEY` (Fernet); templates document `JWT_SECRET`, `DB_SSLMODE`, encryption key |
| **TLS / HTTPS** | Edge termination (nginx/Railway/Vercel); app honors forwarded proto for HSTS; certbot renew retained |

---

## 2. Validation evidence

| Suite | Result | Artifact |
|-------|--------|----------|
| Wave 3 infra + boot + deploy tests | **45 passed** | `evidence/security/WAVE3_PYTEST_INFRA.txt` |
| Full backend pytest | **224 passed** | `evidence/security/WAVE3_PYTEST_FULL.txt` |
| Static smoke | **WAVE3 SMOKE OK** | `scripts/deploy/validate_security_wave3.py` |

---

## 3. Ops notes

- Production Railway: ensure `DATABASE_URL` includes `?sslmode=require` (or set `DB_SSLMODE=require`).
- Set `ATTACHMENT_ENCRYPTION_KEY` (Fernet) before production boot; emergency rollback: `REQUIRE_ATTACHMENT_ENCRYPTION=false`.
- Pilot compose still publishes Postgres `5433` — **lab only**.
- After changing nginx template, re-run `deploy/vps/init-ssl.sh` / envsubst so live `app.conf` picks up CSP/HSTS.

---

## 4. Remaining risks (later)

| Risk | Notes |
|------|-------|
| Image digest pinning / Trivy CI | Deferred |
| Postgres app roles (migrator vs app_rw) | Deferred |
| Backup dump encryption | Separate wave |
| Clinic Node LUKS / PKI package | Offline V1 frozen; restore from offline branch when needed |

---

## 5. Verdict

**Security Wave 3 is COMPLETE.** All automated validations pass (224 pytest).
