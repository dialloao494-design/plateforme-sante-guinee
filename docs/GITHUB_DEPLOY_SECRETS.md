# GitHub Actions — Deploy Railway + Vercel secrets

The workflow `.github/workflows/deploy-railway-vercel.yml` requires these **repository secrets**  
(GitHub → **Settings → Secrets and variables → Actions → New repository secret**).

## Railway (backend job)

| Secret name | Required | How to obtain |
|-------------|----------|---------------|
| `RAILWAY_TOKEN` | **Yes** | Railway → **Project** → **Settings** → **Tokens** → **Create token**. Use a **project token**, not an account API token from railway.com/account/tokens. |
| `RAILWAY_SERVICE_ID` | **Yes** | Railway → open the **backend service** → **Settings**. Copy the service UUID (also visible in the browser URL: `.../service/<UUID>`). |
| `RAILWAY_BACKEND_URL` | **Yes** (verify job) | Public backend URL, e.g. `https://web-production-ad6a36.up.railway.app` |

Optional (not used by current workflow): `RAILWAY_PROJECT_ID` — only needed if you customize linking.

## Vercel (frontend job)

| Secret name | Required | How to obtain |
|-------------|----------|---------------|
| `VERCEL_TOKEN` | **Yes** | Vercel → Account → **Tokens** → Create token |
| `VERCEL_ORG_ID` | **Yes** | Vercel project → Settings → General → **Team ID** / run `vercel project ls` |
| `VERCEL_PROJECT_ID` | **Yes** | Vercel project → Settings → General → **Project ID** |
| `VITE_API_URL` | **Yes** | Same as `RAILWAY_BACKEND_URL` (no trailing slash) |
| `VERCEL_FRONTEND_URL` | **Yes** (verify job) | Production frontend URL, e.g. `https://frontend-seven-rust-94.vercel.app` |

## Common failure: `Deploy backend to Railway` exits immediately

1. **`RAILWAY_TOKEN` is an account token** → create a **project token** instead.  
2. **`RAILWAY_SERVICE_ID` is wrong** → must be the service UUID, not the project ID.  
3. **Secret missing** → workflow now prints an explicit `::error` annotation naming the secret.

Reference: [Railway — Using GitHub Actions](https://blog.railway.com/p/github-actions)
