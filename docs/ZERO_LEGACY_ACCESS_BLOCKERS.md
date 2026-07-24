# What blocks completing zero-legacy frontend migration

**Audited:** 2026-07-24  
**Canonical frontend:** `https://plateforme-sante-guinee.vercel.app`  
**Legacy frontend (must leave production):** `https://frontend-seven-rust-94.vercel.app`

## Bottom line

I **do not** currently have enough access to finish the last Railway env cleanup or to archive/delete the old Vercel project from this cloud agent.

Runtime is already safe (CORS + email links use the canonical URL via remap), but Railway’s **stored** `FRONTEND_URL` is still the legacy host, and the old Vercel project is still online.

## Access probe results

| Surface | Status in this agent | Proof |
|---------|----------------------|-------|
| GitHub `gh` (git / PR / Actions runs) | Available (limited integration token) | `gh auth status` OK |
| GitHub Actions **secrets** read/write | **Blocked — HTTP 403** | `gh secret list` → `Resource not accessible by integration` |
| Railway token in agent env | **Missing** | `env \| grep RAILWAY` empty; `railway` CLI not installed/authenticated |
| Railway token in GitHub Actions | **Missing / empty** | Deploy run log shows `RAILWAY_TOKEN:` blank; CLI deploy step **skipped** |
| Vercel token in agent env | **Missing** | `env \| grep VERCEL` empty; `vercel` CLI not installed/authenticated |
| Vercel token in GitHub Actions | **Missing / empty** | Deploy workflow skips Vercel CLI with “secrets not configured” |

## Exact items needed from you

Provide any **one** of these paths (A is enough for Railway env; B also covers Vercel archive):

### Path A — Railway only (cleans stored `FRONTEND_URL`)

1. **Railway project token** (not an account API token):  
   Railway → project `sunny-illumination` (or whatever hosts `web-production-ad6a36`) → **Settings → Tokens → Create token**
2. **Railway service ID** of the backend web service (UUID in service Settings URL)
3. Deliver as either:
   - Cloud agent secrets / env: `RAILWAY_TOKEN`, `RAILWAY_SERVICE_ID`  
   - **or** GitHub Actions secrets with the same names (repo Settings → Secrets → Actions)

Once present, the deploy workflow now includes a step that sets:

- `FRONTEND_URL=https://plateforme-sante-guinee.vercel.app`
- `FRONTEND_PRODUCTION_URL` / `PUBLIC_FRONTEND_URL` to the same canonical value

### Path B — Railway + Vercel archive/delete

Everything in Path A, plus:

1. **VERCEL_TOKEN** (Vercel → Account → Tokens)
2. **VERCEL_ORG_ID** (team / org id)
3. **Project ID of `frontend-seven-rust-94`** (to archive or delete)
4. Optional: `VERCEL_PROJECT_ID` of `plateforme-sante-guinee` for verification

### Path C — You do 2 clicks in dashboards (fastest if tokens are hard)

**Railway Variables** on backend service:

```
FRONTEND_URL=https://plateforme-sante-guinee.vercel.app
```

Remove any `FRONTEND_PRODUCTION_URL` / `PUBLIC_FRONTEND_URL` still set to seven-rust.

**Vercel:** open project `frontend-seven-rust-94` → Settings → **Delete** or pause/archive.

Then tell me and I will re-run `/health/email` proof that `frontend_url_raw` is canonical and remapped=false.

## What is already clean (no dependency)

| Check | Result |
|-------|--------|
| Effective email/reset frontend URL | Canonical |
| CORS allows only canonical (legacy Origin blocked) | Pass |
| Canonical SPA bundle contains seven-rust | **No** |
| GitHub Actions `DEFAULT_FRONTEND_URL` | Canonical |
| App production config pointing at seven-rust | **None** (only remap allowlist + tests/docs) |

Evidence JSON: `docs/ZERO_LEGACY_DEPENDENCY_AUDIT.json`

## Current production proof (still remapping)

`GET /health/email` currently returns:

- `frontend_url` = `https://plateforme-sante-guinee.vercel.app` ✅  
- `frontend_url_raw` = `https://frontend-seven-rust-94.vercel.app` ❌ (Railway stored value)  
- `frontend_url_remapped_from_legacy` = `true`

That single stored Railway variable is the only production env leftover. Everything else already ignores the old frontend for traffic and links.
