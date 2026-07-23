# Frontend Migration Dependency Report

**Date:** 2026-07-23  
**Canonical production frontend:** `https://plateforme-sante-guinee.vercel.app`  
**Retired frontend:** `https://frontend-seven-rust-94.vercel.app`  
**Backend:** `https://web-production-ad6a36.up.railway.app`  
**Database:** PostgreSQL `railway` on `postgres.railway.internal` (clinic id **17** — AASMA)

## Verdict

The archived `frontend-seven-rust-94` project is **not required for production**.  
Runtime email links and CORS resolve to the canonical frontend even if Railway still stores the legacy URL (hard remap in `core/frontend_url.py`).

## Dependency matrix

| Surface | Legacy seven-rust? | Notes |
|--------|--------------------|-------|
| Vercel GitHub-connected project | No | Production SPA is `plateforme-sante-guinee` |
| Live SPA bundle | No | Bundle points at Railway backend only |
| CORS allowlist | No | Legacy Origin blocked; canonical allowed |
| Password-reset / verify-email links | No (effective) | Remapped when Railway `FRONTEND_URL` is legacy |
| GitHub Actions deploy defaults | No | `DEFAULT_FRONTEND_URL` = canonical |
| Docs / scripts (historical) | Mention only | Marked superseded; not used by runtime |
| Railway env `FRONTEND_URL` raw value | **Still legacy** | Dashboard/token access missing in this agent — hygiene only |

## Blocking access gaps

1. **No `RAILWAY_TOKEN`** in this environment → cannot edit Railway variables via CLI/API.  
   **Manual action:** In Railway project `sunny-illumination` / service `web`, set:
   - `FRONTEND_URL=https://plateforme-sante-guinee.vercel.app`
   - Remove any `FRONTEND_PRODUCTION_URL` / `PUBLIC_FRONTEND_URL` pointing at seven-rust.
2. **No `VERCEL_TOKEN`** → cannot delete/archive the seven-rust Vercel project from here.  
   Safe to archive/delete in Vercel UI after the Railway env hygiene above.

## Proof points

- `/health/email` → `frontend_url` = canonical; `frontend_url_remapped_from_legacy` = true when raw is seven-rust.
- OPTIONS CORS with Origin seven-rust → no `Access-Control-Allow-Origin` for that host.
- OPTIONS CORS with Origin canonical → allowed.
- Both frontends historically shared the same Railway Postgres (`/health/database`).

## Safe to archive?

**Yes** for application traffic. After Railway env cleanup, zero production dependency remains on seven-rust.
