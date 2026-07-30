# Santé Guinée — Git reconciliation & production recovery notes

Generated during recovery on branch `cursor/git-reconciliation-deploy-ab76`.

## Railway failure evidence (GitHub Actions)

- Failed run: `30506994598` (Deploy Railway + Vercel on `main` @ `a3dd731`)
- Observed: `RAILWAY_TOKEN` / `RAILWAY_SERVICE_ID` empty → CLI deploy skipped
- Health wait: HTTP **502** `"Application failed to respond"` for **600s**
- Prior run `30506642414` on `e3108b4` reported `[OK] Backend ready after 1 attempt(s)` in ~2s — **too fast for a real redeploy**; treated as a **stale healthy process**, not proof that `e3108b4` booted cleanly

## Root cause (code + timeline)

1. `e3108b4` / `5536772` added Alembic `20260730_0023_single_platform_owner` creating a **unique partial index** on `users(role) WHERE role = 'platform_owner'` **without demoting duplicates**, plus **fail-closed** startup on migration/schema errors.
2. Production entrypoint runs `alembic upgrade head`. If more than one `platform_owner` exists (historical `/platform/setup` races), index creation fails → startup raises → Railway serves **502**.
3. `a3dd731` only fixed empty local `sante.db` Alembic bootstrap; it did **not** fix duplicate-owner index creation.

## Fixes on this reconciliation branch

- Demote duplicate `platform_owner` rows before unique index (migration `20260730_0023` + `ensure_single_platform_owner_index`)
- Rechain Security Wave 0 identity migration as `20260730_0024`
- Merge Offline V1 Clinic Node package + Security Waves 0–7 + Red Team into one branch atop current `main`
- Test fixture session_version restore after password-change tests (shared in-memory SQLite)
- Production env checklist updated in `deploy/railway-vercel.env.template` (no secret values)

## Manual Railway / Vercel actions required

Agent cannot set Railway/Vercel secrets (no `RAILWAY_TOKEN` / `VERCEL_TOKEN` in Actions).

Before/after merge to `main`, confirm Railway variables (values never logged here):

| Variable | Required |
|---|---|
| `DATABASE_URL` | Yes (`sslmode=require`) |
| `SECRET_KEY` / `JWT_SECRET` | Yes (≥32 strong) |
| `REMINDER_RESPOND_TOKEN` | Yes (≥32) |
| `ATTACHMENT_ENCRYPTION_KEY` | Yes (Fernet) after security merge |
| `JITSI_SECRET` / `JITSI_APP_SECRET` | Yes (cloud) |
| `FRONTEND_URL` / `CORS_ORIGINS` | Canonical Vercel URL |
| `ENVIRONMENT=production` | Yes |
| Emergency bypass attestation | **Must NOT** be set in production |

Canonical frontend: `https://plateforme-sante-guinee.vercel.app`  
Backend: `https://web-production-ad6a36.up.railway.app`  
Do **not** deploy Clinic Node (`deploy/clinic-node/`) as a cloud service.
