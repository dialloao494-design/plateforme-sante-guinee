# Railway HTTP 502 — exact remaining blocker

**Status:** Production backend `https://web-production-ad6a36.up.railway.app` returns **502 Application failed to respond**.  
**Code on GitHub `main`:** recovered (Offline V1 + Security + boot fixes). Local Docker **build succeeds**.  
**What this agent cannot do:** authenticate to Railway or read Railway build/runtime logs.

---

## Classification of the remaining blocker

| Candidate | Verdict | Evidence |
|---|---|---|
| Missing Railway permission / token | **CONFIRMED blocker** | Actions log: `RAILWAY_TOKEN:` empty; `railway whoami` → Unauthorized; `gh secret list` → 403 |
| Missing GitHub secret `RAILWAY_TOKEN` + `RAILWAY_SERVICE_ID` | **CONFIRMED** | Deploy job skips `railway up` and only waits for auto-deploy |
| Missing Railway env var (app-side) | Possible secondary — **cannot verify without logs/token** | Boot guards fixed in code (TLS mesh, attachment key derivation, pyotp) |
| Docker build failure | Unlikely for current tree | `sudo docker build` succeeds on this commit |
| Entrypoint / gosu failure | Mitigated | Entrypoint restored to last-good non-gosu path |
| Migration failure | Mitigated in code | Duplicate `platform_owner` demoted before unique index |
| Dependency issue (`pyotp`) | Mitigated | `pyotp==2.9.0` in `requirements.txt`; CI import path fixed |
| Runtime config | Possible secondary — needs Railway logs | |
| GitHub auto-deploy not applying new commits | **Likely** | Many `main` pushes; health stayed 502 for hours despite fixes |

**Single remaining action only you can perform:** give this agent (or GitHub Actions) Railway project access **or** redeploy from the Railway dashboard and paste the deploy/runtime log snippet if it still fails.

Without that, every further code push can only *hope* Railway’s GitHub integration picks it up — we cannot prove or force it.

---

## Exact intervention required (choose ONE path)

### Path 1 — Fastest: Dashboard Redeploy (no token sharing)

1. Open [Railway](https://railway.app) → project **`sunny-illumination`** (hosts `web-production-ad6a36`).
2. Open the **backend / web** service (public URL `web-production-ad6a36.up.railway.app`).
3. Confirm **Settings → Source** is connected to GitHub repo `dialloao494-design/plateforme-sante-guinee`, branch **`main`**.
4. Open **Deployments** → **Deploy** / **Redeploy** the latest `main` commit (tip should include recovery commits; current tip is whatever `git rev-parse origin/main` shows).
5. Watch **Build Logs** then **Deploy Logs**.
6. When the service is Running, verify:
   ```bash
   curl -sS https://web-production-ad6a36.up.railway.app/health
   curl -sS https://web-production-ad6a36.up.railway.app/health/ready
   ```
   Expect HTTP **200**.
7. If still failing: copy the **last 80 lines** of Deploy/Runtime logs (redact secrets) into the Cursor agent chat. I will fix the next code error immediately.

### Path 2 — Unblock the agent + Actions (recommended for ongoing recovery)

#### A. Create a Railway **project** token

1. Railway → project **`sunny-illumination`** → **Settings** → **Tokens** → **Create Token**.  
2. Name: `cursor-recovery` (or similar).  
3. Copy the token once (do not paste it into git/issues).

#### B. Copy the backend service UUID

1. Railway → open the **web/backend** service → **Settings**.  
2. Copy the service UUID from the URL: `.../service/<UUID>`  
3. That value is `RAILWAY_SERVICE_ID`.

#### C. Deliver credentials (either is enough; both is best)

**Option C1 — Cursor Cloud Agent environment / secrets**

Set:

- `RAILWAY_TOKEN` = (project token from A)  
- `RAILWAY_SERVICE_ID` = (UUID from B)

Then re-run / continue this agent. I will:

1. `railway up --service=$RAILWAY_SERVICE_ID`
2. Read deploy logs
3. Fix any remaining boot error
4. Confirm `/health` and `/health/ready` = 200
5. Run production smoke tests

**Option C2 — GitHub Actions repository secrets**

GitHub → `dialloao494-design/plateforme-sante-guinee` → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|---|---|
| `RAILWAY_TOKEN` | project token from A |
| `RAILWAY_SERVICE_ID` | service UUID from B |
| `RAILWAY_BACKEND_URL` | `https://web-production-ad6a36.up.railway.app` |

Then: **Actions → Deploy Railway + Vercel → Run workflow** (branch `main`).

---

## Variables to verify in Railway (names only — do not paste values into chat/git)

On the **backend service → Variables**:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Railway Postgres reference is fine (`*.railway.internal` OK) |
| `ENVIRONMENT` | Yes | `production` |
| `SECRET_KEY` / `JWT_SECRET` | Yes | ≥32 strong chars |
| `REMINDER_RESPOND_TOKEN` | Yes | ≥32 chars |
| `JITSI_SECRET` or `JITSI_APP_SECRET` | Yes | cloud teleconsult |
| `ATTACHMENT_ENCRYPTION_KEY` | Recommended | Fernet key; if missing, app derives from JWT (still encrypted) |
| `FRONTEND_URL` | Yes | `https://plateforme-sante-guinee.vercel.app` |
| `CORS_ORIGINS` | Recommended | same canonical frontend URL |
| `ENABLE_PILOT_SEED` | Must be false/absent | |
| `ENABLE_STARTUP_TEST_USER` | Must be false/absent | |
| `EMERGENCY_SECURITY_BYPASS_ATTESTATION` | Must be absent | |

Do **not** deploy Clinic Node (`deploy/clinic-node/`) as this Railway service.

---

## What I can still do without your intervention

- Keep fixing application/Docker/migration code on `main`
- Keep local tests green
- Keep waiting/probing `/health`
- Prepare smoke scripts for the moment health returns

## What I cannot do without your intervention

- Force a Railway deploy
- Read Railway build/runtime logs
- Confirm whether GitHub auto-deploy is even connected
- Set Railway variables
- Mark production backend healthy

---

## Success criteria (unchanged)

- `GET /health` → 200  
- `GET /health/ready` → 200  
- Railway deployment healthy  
- Frontend talks to backend  
- Production smoke tests pass

## Code fixes applied while blocked on Railway access

These are already on `main` and do **not** require your intervention:

1. Demote duplicate `platform_owner` before unique index
2. Add `pyotp` dependency
3. Railway private-mesh TLS exemption
4. Derive `ATTACHMENT_ENCRYPTION_KEY` from strong JWT when unset
5. Prefer `DATABASE_URL` password over weak leftover `POSTGRES_PASSWORD`
6. Auto-default `TRUSTED_PROXY_HOSTS` on Railway when unset (never `*`)
7. Railway-compatible Dockerfile (`USER appuser`, no fragile apt mirrors)

After you Redeploy (Path 1) or provide `RAILWAY_TOKEN` (Path 2), these fixes can take effect.
