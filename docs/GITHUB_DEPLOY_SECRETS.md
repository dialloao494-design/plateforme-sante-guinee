# GitHub Actions — Deploy Railway + Vercel secrets

The workflow `.github/workflows/deploy-railway-vercel.yml` requires these **repository secrets**  
(GitHub → **Settings → Secrets and variables → Actions → New repository secret**).

## Required for a green pipeline

| Secret name | How to obtain |
|-------------|---------------|
| `RAILWAY_BACKEND_URL` | Public backend URL, e.g. `https://web-production-ad6a36.up.railway.app` (no trailing slash) |
| `VERCEL_TOKEN` | Vercel → Account → **Tokens** → Create token |
| `VERCEL_ORG_ID` | Vercel project → Settings → General → **Team ID** (or `vercel project ls`) |
| `VERCEL_PROJECT_ID` | Vercel project → Settings → General → **Project ID** |
| `VITE_API_URL` | Same value as `RAILWAY_BACKEND_URL` |
| `VERCEL_FRONTEND_URL` | Production frontend URL, e.g. `https://frontend-seven-rust-94.vercel.app` |

## Optional — Railway CLI deploy from Actions

If these are **not** set, the backend job waits for Railway’s GitHub auto-deploy and still passes when `/health/ready` is OK.

| Secret name | How to obtain |
|-------------|---------------|
| `RAILWAY_TOKEN` | Railway → **Project** → **Settings** → **Tokens** → **Create token**. Use a **project token**, not an account API token from railway.com/account/tokens. |
| `RAILWAY_SERVICE_ID` | Railway → open the **backend service** → **Settings**. Copy the service UUID (browser URL: `.../service/<UUID>`). |

When both optional secrets are set, the workflow runs `railway up --service=...` and `railway run ... staging_e2e_seed.py`.

## Quick copy-paste values (Koloma production)

```
RAILWAY_BACKEND_URL=https://web-production-ad6a36.up.railway.app
VITE_API_URL=https://web-production-ad6a36.up.railway.app
VERCEL_FRONTEND_URL=https://frontend-seven-rust-94.vercel.app
```

You still need `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` from your Vercel dashboard.

## Common failures

1. **`RAILWAY_TOKEN` is an account token** → create a **project token** instead.
2. **`RAILWAY_SERVICE_ID` is wrong** → must be the service UUID, not the project ID.
3. **Missing `RAILWAY_BACKEND_URL`** → backend job fails immediately with an explicit error.
4. **Missing Vercel secrets** → frontend job fails; verify and smoke-test jobs are skipped.

Reference: [Railway — Using GitHub Actions](https://blog.railway.com/p/github-actions)
