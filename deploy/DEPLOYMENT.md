# Production deployment — Plateforme Santé Guinée

## Architecture

```text
Internet
   │
   ▼
┌─────────────────────────────────────┐
│  Nginx (TLS, gzip, security headers) │
│  :443 / :80                          │
└──────────┬──────────────┬────────────┘
           │              │
    /api/* │              │ /*
           ▼              ▼
   ┌──────────────┐  ┌─────────────┐
   │ FastAPI      │  │ React (Vite) │
   │ backend:8000 │  │ frontend:80  │
   └──────┬───────┘  └─────────────┘
          │
          ▼
   ┌──────────────┐
   │ PostgreSQL 16│
   │ db:5432      │
   └──────────────┘
```

| Service | Role |
|---------|------|
| **nginx** | Reverse proxy, HTTPS, WebSocket-ready `/api/ws/`, static caching |
| **backend** | REST API, JWT auth, uploads volume, rate limiting |
| **frontend** | SPA build served by nginx in container |
| **db** | Persistent PostgreSQL (`pgdata` volume) |

---

## Deployment phases (recommended order)

1. **Local Docker** — section 1 below  
2. **Staging VPS** — `deploy/vps/deploy-staging.sh` + `.env.staging` (see [STAGING_VALIDATION.md](./STAGING_VALIDATION.md))  
3. **Validate** — `deploy/vps/validate-staging.sh`, mobile/4G checklist  
4. **Production** — [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) + `deploy/vps/deploy-production.sh`  

Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md) · Readiness: [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)

---

## Repository layout

| Path | Purpose |
|------|---------|
| `Dockerfile` | Backend API image |
| `frontend-sante/frontend/Dockerfile` | Frontend build + nginx |
| `docker-compose.yml` | Base stack (HTTP staging) |
| `docker-compose.prod.yml` | Production overlay (HTTPS, certbot) |
| `.env.production.example` | Root compose variables |
| `deploy/env/.env.backend.example` | API secrets |
| `deploy/env/.env.frontend.example` | Vite build args |
| `deploy/nginx/` | Nginx configs |
| `deploy/vps/` | Ubuntu install & deploy scripts |

---

## 1. Local Docker test (HTTP)

```bash
cp .env.production.example .env.production
cp deploy/env/.env.backend.example deploy/env/.env.backend
# Edit passwords and SECRET_KEY

# Staging URLs (localhost)
# In .env.production:
#   VITE_API_URL=http://localhost/api
#   POSTGRES_PASSWORD=...

docker compose --env-file .env.production up -d --build
```

Open: http://localhost  
API: http://localhost/api/health  

Pilot accounts (if `ENABLE_PILOT_SEED=true`):

- Doctor: `dr.amu@example.com` / `Doctor123!`
- Patient: `test.patient@example.com` / `Patient123!`

---

## 2. VPS prerequisites (Ubuntu 22.04)

```bash
sudo apt update && sudo apt upgrade -y
sudo bash deploy/vps/install-docker.sh
```

Point DNS **A record** `sante.example.com` → VPS public IP.

---

## 3. Production configuration

On the server:

```bash
git clone <your-repo> /opt/plateforme-sante
cd /opt/plateforme-sante

cp .env.production.example .env.production
cp deploy/env/.env.backend.example deploy/env/.env.backend
```

Edit **`.env.production`**:

- `DOMAIN=your.real.domain`
- `POSTGRES_PASSWORD=` strong random
- `VITE_API_URL=https://your.real.domain/api`
- `CERTBOT_EMAIL=admin@your.domain`

Edit **`deploy/env/.env.backend`**:

- `SECRET_KEY=` (`python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `CORS_ORIGINS=https://your.real.domain`
- `FRONTEND_URL=https://your.real.domain`
- Stripe live keys
- `TELECONSULT_PROVIDER=jitsi` (or `daily` / `twilio`)
- SMTP settings

After first deploy, set `ENABLE_PILOT_SEED=false` in `.env.production` if you do not want demo users recreated.

---

## 4. SSL (Let's Encrypt)

```bash
chmod +x deploy/vps/*.sh
sudo bash deploy/vps/init-ssl.sh
```

Or manual certbot then:

```bash
export DOMAIN=sante.example.com
envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template > deploy/nginx/conf.d/app.conf
```

---

## 5. Deploy / update

```bash
sudo bash deploy/vps/deploy.sh
```

Containers use `restart: unless-stopped`.

---

## 6. Backups

```bash
# Manual
sudo bash deploy/vps/backup-db.sh

# Cron (daily 03:00)
0 3 * * * /opt/plateforme-sante/deploy/vps/backup-db.sh >> /var/log/sante-backup.log 2>&1
```

Backups: `backups/sante_YYYYMMDD_HHMMSS.sql.gz` (14-day retention).

---

## 7. Security checklist

- [ ] `DEBUG=false`, `ENVIRONMENT=production`
- [ ] Strong `SECRET_KEY` and `POSTGRES_PASSWORD`
- [ ] CORS limited to your domain (no `ENABLE_LAN_DEV`)
- [ ] HTTPS only in production
- [ ] `ALLOWED_HOSTS=your.domain,localhost` on backend
- [ ] Rate limits: `RATE_LIMIT_LOGIN=10/minute`
- [ ] Firewall: allow 80, 443; block 5432 and 8000 from public
- [ ] Disable `ENABLE_DEMO_CLINIC_SEED`, `ENABLE_STARTUP_TEST_USER`

---

## 8. Teleconsultation

| Provider | Env |
|----------|-----|
| Stub (demo) | `TELECONSULT_PROVIDER=stub` |
| Jitsi | `TELECONSULT_PROVIDER=jitsi`, `JITSI_DOMAIN=meet.jit.si` |
| Daily | `DAILY_API_KEY=...` |
| Twilio | `TWILIO_API_KEY`, `TWILIO_API_SECRET`, `TWILIO_ACCOUNT_SID` |

API:

- `GET /teleconsultation/appointments/{id}/access` — time-boxed join token / room URL
- `POST /teleconsultation/appointments/{id}/end` — close session, mark completed

---

## 9. Useful commands

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec db psql -U sante -d sante
curl -fsS https://YOUR_DOMAIN/api/health/ready
```

---

## Next phase

After this infrastructure is live: **AI healthcare assistant** layer (RAG, clinical hints, triage) as a separate service or router module without changing this compose topology.
