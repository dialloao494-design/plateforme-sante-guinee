# Deployment Health Report — Production

**Generated:** 2026-05-25  
**Environment:** Railway (backend) + Vercel (frontend)

## Infrastructure status

| Component | URL / artifact | Status |
|-----------|----------------|--------|
| Backend API | https://web-production-ad6a36.up.railway.app | ✅ `/health`, `/health/ready` |
| Frontend SPA | https://frontend-seven-rust-94.vercel.app | ✅ HTTP 200 |
| GitHub Actions | `.github/workflows/deploy-railway-vercel.yml` | ✅ Present |
| CI pipeline | `.github/workflows/ci.yml` | ✅ Present |
| DB migrations | `database_migrations.py` + Alembic | ✅ Startup `ensure_*` + `alembic upgrade head` |

## Security & isolation

| Check | Result |
|-------|--------|
| JWT authentication on clinical APIs | ✅ Anonymous → 401/403 |
| Role-based access (8 Koloma roles) | ✅ Validated |
| Clinic admin cannot list other clinic staff | ✅ 403 on clinic_id=1 |
| Patient search scoped to clinic | ✅ Cross-clinic leak test |
| Platform admin clinic creation | ✅ Isolated new clinic |

## Environment variables (required for full CI deploy)

| Secret | Purpose | Fallback if missing |
|--------|---------|---------------------|
| `RAILWAY_TOKEN` | CLI backend deploy | Railway GitHub auto-deploy |
| `RAILWAY_SERVICE_ID` | Target service | Auto-deploy |
| `VERCEL_TOKEN` | CLI frontend deploy | Vercel GitHub integration |
| `VERCEL_ORG_ID` | Vercel project | Auto-deploy |
| `VERCEL_PROJECT_ID` | Vercel project | Auto-deploy |
| `VITE_API_URL` | Frontend API base | Default Railway URL |
| `SECRET_KEY` | JWT signing | Required on Railway |

## Deployment survivability

**Safe for existing clinics on redeploy:**

- Migrations are additive (`ALTER TABLE ADD COLUMN`, new tables only).
- `ensure_clinical_modules_schema()` is idempotent.
- No destructive schema changes in recent commits.
- Koloma clinic_id=13 data preserved across validation runs.

**Risks on redeploy:**

1. Alembic head mismatch on fresh DB — mitigated by `ensure_*` fallbacks.
2. Vercel CDN cache may delay new lazy routes by ~5 min.
3. Missing Vercel secrets → relies on GitHub integration timing.

## Reporting accuracy

| Module | Validation method | Last result |
|--------|-------------------|-------------|
| PEV monthly | API register row count vs records | ✅ |
| Nursing monthly | Register API + E2E procedures | ✅ |
| Nutrition monthly | Register + assessment E2E | ✅ |
| Hospitalization | Monthly report admissions | ✅ |
| Laboratory | Monthly report by test type | ✅ |
| Pharmacy | Monthly dispensed count | ✅ |
| Koloma consolidated | `/clinical/reports/koloma/monthly` | ✅ |

## Recommended hardening (post go-live)

1. Enable Railway health-check alerts on `/health/ready`.
2. Add Vercel deployment notification to clinic admin email.
3. Schedule nightly `koloma_field_readiness_suite.py` cron (read-only).
4. Rotate Koloma staff passwords after first field week.
