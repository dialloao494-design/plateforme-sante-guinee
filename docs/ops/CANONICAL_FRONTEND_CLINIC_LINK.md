# Canonical frontend — clinic link (mandatory)

## Official production URL

**https://plateforme-sante-guinee.vercel.app**

Give this link to every clinic staff member (Reception, Doctor, Lab, Pharmacy, Admin).  
Do **not** use bookmarks, QR codes, or emails that still point at `frontend-seven-rust-94.vercel.app`.

## Retired URL (do not use)

`https://frontend-seven-rust-94.vercel.app`

That host is a separate, stale Vercel project. Production CORS rejects it, which surfaces in the browser as:

> Impossible de joindre le serveur. Réessayez dans un instant.

(or a generic “Une erreur est survenue…” depending on the cached bundle).

## Why login fails on the old link

1. Staff open the legacy bookmark / QR / email link (`seven-rust-94`).
2. The SPA still calls `https://web-production-ad6a36.up.railway.app`.
3. Browser CORS preflight is rejected (`Disallowed CORS origin`, HTTP 400, no `Access-Control-Allow-Origin`).
4. Axios reports a network error → login UI fails.

Accounts and passwords are usually fine; the **domain** is wrong.

## Operator checklist (urgent)

### A. Clinic communications (immediate)

1. Send every clinic the canonical URL above.
2. Ask staff to clear site data for the old domain and open only the canonical URL.

### B. Disable the legacy Vercel project (required)

GitHub Actions currently has **no** `VERCEL_TOKEN` / `VERCEL_ORG_ID`, so CI cannot redeploy the old project automatically.

**Manual (Vercel dashboard) — preferred:**

1. Open the Vercel project named `frontend-seven-rust-94` (or similar).
2. Either:
   - **Settings → Domains**: remove production traffic / pause the project, **or**
   - Deploy the contents of repo folder `legacy-frontend-redirect/` to that project’s **Production** (permanent 308 redirect + deprecation page), **or**
   - Delete/archive the project after confirming no custom domain still points at it.
3. Verify: `curl -sSI https://frontend-seven-rust-94.vercel.app/` returns `308`/`307` to `https://plateforme-sante-guinee.vercel.app/...` **or** a page that only links to the canonical host.

**Optional after secrets are added:**

1. Set repo secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_LEGACY_PROJECT_ID`.
2. Run workflow **Deprecate legacy seven-rust frontend**.

### C. Railway `FRONTEND_URL` (required for clean email links)

GitHub Actions currently has **no** `RAILWAY_TOKEN`, so CI cannot rewrite env vars.

In Railway project `sunny-illumination` → service `web` → Variables:

```text
FRONTEND_URL=https://plateforme-sante-guinee.vercel.app
```

Remove any `FRONTEND_PRODUCTION_URL` / `PUBLIC_FRONTEND_URL` still set to seven-rust.

Confirm:

```bash
curl -s https://web-production-ad6a36.up.railway.app/auth/email-status
# expect: frontend_url_remapped_from_legacy: false
```

(Runtime already remaps legacy values for generated links; correcting the env removes the stale raw value.)

## Quick verification

```bash
# Must succeed (CORS allow-origin = canonical)
curl -i -X OPTIONS \
  -H 'Origin: https://plateforme-sante-guinee.vercel.app' \
  -H 'Access-Control-Request-Method: POST' \
  https://web-production-ad6a36.up.railway.app/auth/login-json

# Must fail closed (no allow-origin)
curl -i -X OPTIONS \
  -H 'Origin: https://frontend-seven-rust-94.vercel.app' \
  -H 'Access-Control-Request-Method: POST' \
  https://web-production-ad6a36.up.railway.app/auth/login-json
```
