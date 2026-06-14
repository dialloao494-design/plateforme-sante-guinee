# Production Deployment Package — Plateforme Santé Guinée

**Status:** QA approved (39 PASS / 0 WARNING / 0 FAIL)  
**Target:** Pilot clinic deployment on VPS (Ubuntu 22.04, Docker, PostgreSQL, HTTPS)  
**Last updated:** 2026-06-14

---

## 1. Repository structure audit

### Core application

| Path | Role | Production relevance |
|------|------|-------------------|
| `main.py` | FastAPI entrypoint | Required |
| `routers/` | REST API (clinical, auth, patients, …) | Required |
| `services/` | Business logic, seeds, billing | Required |
| `models/` | SQLAlchemy ORM | Required |
| `schemas/` | Pydantic validation | Required |
| `core/` | RBAC, settings, rate limits | Required |
| `alembic/` | Database migrations | **Run before go-live** |
| `database_migrations.py` | Idempotent startup schema guards | Auto on boot |
| `requirements.txt` | Python dependencies | Required |
| `Dockerfile` | Backend container | Required |

### Frontend

| Path | Role |
|------|------|
| `frontend-sante/frontend/` | React + Vite SPA |
| `frontend-sante/frontend/Dockerfile` | Production static build |
| `frontend-sante/frontend/.env.example` | `VITE_API_URL` template |

### Infrastructure & deploy

| Path | Role |
|------|------|
| `docker-compose.yml` | Base stack (db, backend, frontend, nginx) |
| `docker-compose.prod.yml` | Production overlay (HTTPS, certbot, limits) |
| `deploy/nginx/` | Reverse proxy configs |
| `deploy/vps/` | VPS scripts (SSL, deploy, backup) |
| `deploy/env/` | Backend/frontend env templates |
| `certbot/` | SSL certificates (gitignored, created on server) |

### Operations scripts

| Path | Purpose |
|------|---------|
| `scripts/qa_production_e2e.py` | End-to-end QA (API + permissions) |
| `scripts/qa_db_counts.py` | Volume verification |
| `scripts/verify_medical_history_seed.py` | Longitudinal seed check |
| `scripts/db/backup_verify.sh` | Validate backup integrity |
| `scripts/db/restore_drill.sh` | Non-destructive restore test |
| `scripts/git/pre_push_check.ps1` | Block secret commits |
| `generate_secrets.py` | JWT / key generation |

### Documentation (canonical)

| Document | Status |
|----------|--------|
| [README.md](../README.md) | ✅ Verified — quick start, pilot accounts, QA |
| [docs/DEPLOYMENT.md](./DEPLOYMENT.md) | ✅ Verified — env, Docker, VPS |
| [docs/MIGRATIONS.md](./MIGRATIONS.md) | ✅ Verified — Alembic + production steps |
| [docs/BACKUP_RESTORE.md](./BACKUP_RESTORE.md) | ✅ Verified — pg_dump, restore, retention |

### Environment templates

| File | Committed | Notes |
|------|-----------|-------|
| `.env.example` | Yes | Local development |
| `.env.production.example` | Yes | VPS compose root |
| `.env.staging.example` | Yes | Staging VPS |
| `deploy/env/.env.backend.example` | Yes | API secrets template |
| `deploy/env/.env.frontend.example` | Yes | Build-time frontend vars |
| `.env`, `.env.production`, `deploy/env/.env.backend` | **No** (gitignored) | Real secrets on server only |

### Legacy / reference (not required for pilot)

| Path | Note |
|------|------|
| `HANDOVER/` | Historical handover docs |
| `deploy/DEPLOYMENT.md`, `deploy/PRODUCTION_DEPLOYMENT.md` | Superseded by `docs/DEPLOYMENT.md` |
| `deploy/jitsi/docker-jitsi-meet/` | Embedded Jitsi submodule — use only if self-hosting video |
| Root `DEPLOYMENT_*.md`, `*_AUDIT*.md` | Archive / audit history |

### QA evidence

| Path | Content |
|------|---------|
| `evidence/qa_production_report.json` | Latest E2E report (39 PASS, 0 FAIL) |

### Pre-publication gaps to address

- [ ] Confirm `deploy/env/.env.backend` is **not** tracked (`git ls-files deploy/env/.env.backend` → empty)
- [ ] Confirm `backups/`, `certbot/`, `sante.db` are gitignored
- [ ] Remove or archive obsolete Stripe references in legacy deploy docs (optional)
- [ ] Set `ENABLE_PILOT_SEED=false` in production env files after initial admin bootstrap

---

## 2. Documentation verification summary

| Document | Complete | Accurate | Action |
|----------|----------|----------|--------|
| README | ✅ | ✅ | Links to `docs/*` |
| DEPLOYMENT | ✅ | ✅ | Covers Docker + VPS + QA |
| MIGRATIONS | ✅ | ✅ | Lists all Alembic revisions through `0007` |
| BACKUP_RESTORE | ✅ | ✅ | pg_dump, restore, retention policy |

**Health endpoints for monitoring:**

- Liveness: `GET /health` → `{"status":"ok",...}`
- Readiness: `GET /health/ready` → DB connectivity (503 if DB down)

---

## 3. GitHub publication checklist

### Repository hygiene

- [ ] Run `.\scripts\git\pre_push_check.ps1` — no secret env files staged
- [ ] Verify `.gitignore` covers: `.env*`, `backups/`, `certbot/`, `*.db`, `deploy/env/.env.backend`
- [ ] Remove any committed credentials: `git log -p -- '*.env'`
- [ ] Default branch protected (`main`) with PR reviews (team policy)

### README & docs

- [ ] README quick-start works on clean clone
- [ ] `docs/DEPLOYMENT.md`, `MIGRATIONS.md`, `BACKUP_RESTORE.md` linked from README
- [ ] This package (`docs/PRODUCTION_DEPLOYMENT_PACKAGE.md`) linked from README
- [ ] Pilot account table present; production warning on `ENABLE_PILOT_SEED`

### Templates only in Git

- [ ] `.env.example`, `.env.production.example`, `.env.staging.example` present
- [ ] `deploy/env/.env.backend.example`, `.env.frontend.example` present
- [ ] No real `SECRET_KEY`, `POSTGRES_PASSWORD`, or JWT in any committed file

### CI / quality (recommended)

- [ ] `pytest tests/ -q` passes on default branch
- [ ] `python scripts/qa_production_e2e.py` documented as pre-release gate
- [ ] Optional: GitHub Actions workflow for test on push (not required for pilot)

### Release tagging

- [ ] Tag release: `git tag -a v1.0.0-pilot -m "Pilot production release"`
- [ ] Push tag: `git push origin v1.0.0-pilot`
- [ ] Record commit SHA deployed to VPS in runbook

---

## 4. VPS deployment checklist

### Server provisioning

- [ ] Ubuntu 22.04 LTS VPS (min 2 vCPU, 4 GB RAM, 40 GB SSD)
- [ ] Static public IPv4 + DNS A record (`DOMAIN` → VPS IP)
- [ ] SSH key auth only; disable password login
- [ ] UFW: allow 22, 80, 443; deny all other inbound
- [ ] Non-root deploy user with `docker` group membership

### Software

- [ ] Docker Engine + Compose plugin (`deploy/vps/install-docker.sh`)
- [ ] Git installed
- [ ] Optional: fail2ban for SSH

### Clone & configure

```bash
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git /opt/plateforme-sante
cd /opt/plateforme-sante
git checkout v1.0.0-pilot   # or target tag/branch

cp .env.production.example .env.production
cp deploy/env/.env.backend.example deploy/env/.env.backend
cp deploy/env/.env.frontend.example deploy/env/.env.frontend
python3 generate_secrets.py   # copy SECRET_KEY into .env.backend
```

- [ ] `DOMAIN` set in `.env.production`
- [ ] `POSTGRES_PASSWORD` strong (16+ chars, not default)
- [ ] `SECRET_KEY` / `JWT_SECRET` strong (32+ chars)
- [ ] `ENVIRONMENT=production` in `deploy/env/.env.backend`
- [ ] `ENABLE_PILOT_SEED=false` (after first bootstrap)
- [ ] `BYPASS_AVAILABILITY_VALIDATION=false`
- [ ] `VITE_API_URL=https://<DOMAIN>/api`
- [ ] `CORS_ORIGINS=https://<DOMAIN>`
- [ ] `RATE_LIMIT_LOGIN=30/minute` (adjust if needed)

### SSL & deploy

- [ ] `sudo bash deploy/vps/init-ssl.sh` (Let's Encrypt)
- [ ] `sudo bash deploy/vps/deploy-production.sh`
- [ ] All containers healthy: `docker compose -f docker-compose.yml -f docker-compose.prod.yml ps`

### Post-deploy validation

- [ ] `curl -fsS https://<DOMAIN>/api/health`
- [ ] `curl -fsS https://<DOMAIN>/api/health/ready`
- [ ] Frontend loads over HTTPS
- [ ] Login works for each pilot role (once seeded)
- [ ] Full clinical workflow smoke test (reception → doctor → lab → pharmacy)

### Migrations on VPS

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic current
```

---

## 5. PostgreSQL backup strategy

### Objectives

- **RPO** (max data loss): 24 hours (daily backup) — tighten to 1 h with hourly dumps if required
- **RTO** (max downtime): 4 hours (restore + validation)
- **Retention:** 30 daily + 12 monthly off-site copies

### Automated daily backup

Cron on VPS (02:00 local):

```cron
0 2 * * * cd /opt/plateforme-sante && ENV_FILE=.env.production COMPOSE_EXTRA="-f docker-compose.prod.yml" bash deploy/vps/backup-db.sh >> /var/log/sante-backup.log 2>&1
```

Script: `deploy/vps/backup-db.sh` → `backups/sante_YYYYMMDD_HHMMSS.sql.gz`

- [ ] Cron installed and tested manually once
- [ ] `scripts/db/backup_verify.sh` run after first backup
- [ ] Local retention: 14 days (script auto-deletes older files)

### Off-site replication

- [ ] Sync `backups/` to encrypted object storage (S3-compatible, Backblaze B2, etc.)
- [ ] Monthly archive kept 12 months
- [ ] Backup encryption at rest (bucket SSE or gpg before upload)
- [ ] Access restricted to ops role only

### Pre-migration / pre-deploy snapshot

```bash
docker compose ... exec -T db pg_dump -U sante sante | gzip > backups/pre_deploy_$(date +%Y%m%d).sql.gz
```

### Restore procedure

See [BACKUP_RESTORE.md](./BACKUP_RESTORE.md). Summary:

1. Stop traffic (nginx maintenance page or `docker compose down`)
2. Restore dump into PostgreSQL
3. `docker compose up -d`
4. Verify `/health/ready` + QA script
5. Confirm audit log continuity

### Monthly restore drill

- [ ] Run `bash scripts/db/restore_drill.sh backups/<latest>.sql.gz` on staging
- [ ] Document drill date and result in ops log

---

## 6. Production monitoring checklist

### Health probes

| Probe | URL | Expected | Frequency |
|-------|-----|----------|-----------|
| Liveness | `GET /api/health` | 200, `"status":"ok"` | 1 min |
| Readiness | `GET /api/health/ready` | 200, `"database":"ok"` | 1 min |
| Frontend | `GET /` | 200 | 5 min |

### Infrastructure

- [ ] Docker container restart policy: `unless-stopped`
- [ ] Disk usage alert > 80% on `/` and Docker volumes
- [ ] Memory alert if backend OOM (512M limit in prod compose)
- [ ] PostgreSQL connection pool / slow query log (optional)

### Application logs

- [ ] `LOG_FORMAT=json` in production for structured parsing
- [ ] Log rotation: `./logs` volume or Docker logging driver
- [ ] Optional: `SENTRY_DSN` for error tracking

### Uptime monitoring

- [ ] External ping (UptimeRobot, Better Stack, or similar) on `/api/health`
- [ ] Alert channel: SMS/email to on-call (clinic IT contact)

### Clinical ops metrics (manual / weekly review)

- [ ] `GET /clinical/audit-logs?limit=50` — denied access attempts
- [ ] Pending billing charges not growing abnormally
- [ ] Failed login rate (429 spikes) in nginx/access logs

### QA regression (weekly during pilot)

```bash
python scripts/qa_production_e2e.py   # target: FAIL=0
python scripts/qa_db_counts.py
```

---

## 7. Security checklist

### Secrets & configuration

- [ ] `SECRET_KEY` ≥ 32 random characters; not in Git
- [ ] `POSTGRES_PASSWORD` strong; not default `sante_dev_password`
- [ ] `ENABLE_PILOT_SEED=false` in public production
- [ ] `DEBUG=false`, `ENVIRONMENT=production`
- [ ] API docs disabled in production (`DISABLE_API_DOCS` or prod default)
- [ ] JWT expiry appropriate (`ACCESS_TOKEN_EXPIRE_MINUTES=60`)

### Network

- [ ] HTTPS only (TLS 1.2+); HTTP → HTTPS redirect
- [ ] `ALLOWED_HOSTS` / `DOMAIN` set correctly
- [ ] CORS limited to production frontend origin(s)
- [ ] Rate limiting active: login 30/min, register 5/min

### RBAC (verified in QA)

- [ ] Reception cannot access doctor/lab/pharmacy/admin APIs (403)
- [ ] Doctor cannot access lab/pharmacy queues (403)
- [ ] Lab/pharmacy cross-access denied (403)
- [ ] Patient cannot access clinical operations (403)
- [ ] Admin backup-status admin-only

### Data protection

- [ ] Clinical attachments not served from public `/uploads/*` (blocked in `main.py`)
- [ ] Database backups encrypted off-site
- [ ] VPS SSH key-only; no shared root password
- [ ] Pilot passwords rotated before public announcement

### Compliance ops

- [ ] Clinical audit logs enabled (`clinical_audit_logs` table growing)
- [ ] Incident contact list documented (see disaster recovery)
- [ ] Patient data export/deletion process documented for clinic DPO

---

## 8. Disaster recovery checklist

### Scenarios & playbooks

| Scenario | Detection | Response |
|----------|-----------|----------|
| VPS unreachable | External uptime alert | Failover DNS to standby / restore on new VPS |
| Database corruption | `/health/ready` 503 | Restore latest backup; run QA |
| Accidental data delete | User report + audit logs | Point-in-time restore from backup |
| SSL expiry | Certbot renewal failure alert | Manual `certbot renew`; check cron |
| DDoS / brute force | 429/502 spike | Rate limits; UFW; CDN/WAF if available |

### DR prerequisites

- [ ] Off-site backup copies verified (< 24 h old)
- [ ] Restore procedure tested on staging within last 30 days
- [ ] Infrastructure-as-code: clone repo + env templates sufficient to rebuild
- [ ] DNS TTL lowered (300 s) before go-live for faster failover

### Recovery steps (full VPS loss)

1. Provision new Ubuntu 22.04 VPS
2. Restore DNS A record
3. Clone repo at known release tag
4. Restore `deploy/env/.env.backend` from secure vault (1Password, Bitwarden, etc.)
5. `init-ssl.sh` + `deploy-production.sh`
6. Restore PostgreSQL from latest off-site backup
7. `alembic current` == head
8. Run QA E2E; smoke test all roles
9. Communicate recovery to clinic staff

### RTO / RPO targets (pilot)

| Metric | Target |
|--------|--------|
| RPO | ≤ 24 h |
| RTO | ≤ 4 h |
| Communication SLA | 1 h to clinic manager after incident confirmed |

---

## 9. Pilot clinic onboarding checklist

### Pre-onboarding (1 week before)

- [ ] VPS deployed and QA passed
- [ ] Domain + HTTPS live
- [ ] Clinic manager account created (not shared pilot password)
- [ ] Staff roster received: names, roles, emails
- [ ] Training schedule set (2 h per role)

### Account provisioning

- [ ] Create staff via admin dashboard or `POST /clinical/staff`
- [ ] Assign each user to `clinic_id=1`
- [ ] Disable generic pilot passwords after individual accounts issued
- [ ] Doctor profiles linked to clinic

### Data setup

- [ ] Run `alembic upgrade head` on production DB
- [ ] Optional: import existing patient list (reception intake CSV → manual entry for pilot)
- [ ] Do **not** run `medical_history_seed` on production (simulated data only)

### Training per role

| Role | URL path | Key tasks |
|------|----------|-----------|
| Reception | `/clinical/reception` | Intake, appointments, check-in, encaissement |
| Doctor | `/clinical/doctor` | Consultation, lab orders, prescriptions, follow-ups |
| Lab | `/clinical/lab` | Sample collection, results, validation |
| Pharmacy | `/clinical/pharmacy` | Prepare, dispense |
| Manager | `/clinical` | Operations summary, audit logs, staff |
| Patient | `/my-records` | Medical history, appointments |

### Acceptance criteria

- [ ] One real patient completes full workflow end-to-end
- [ ] Cash payment recorded in billing
- [ ] Medical history visible on patient portal
- [ ] Audit log entries for each step
- [ ] Clinic manager signs pilot acceptance form

---

## 10. Go-live checklist

### T-7 days

- [ ] Staging environment validated (`deploy/vps/validate-staging.sh`)
- [ ] Security checklist (section 7) complete
- [ ] Backup cron + off-site sync tested
- [ ] All staff accounts provisioned

### T-1 day

- [ ] Production deploy from release tag
- [ ] `alembic upgrade head`
- [ ] `ENABLE_PILOT_SEED=false` confirmed
- [ ] QA E2E on production URL: **FAIL=0**
- [ ] SSL certificate valid > 30 days
- [ ] Monitoring alerts configured

### Go-live day (T-0)

- [ ] Maintenance window communicated to clinic (if needed)
- [ ] Final pre-deploy backup taken
- [ ] Deploy: `bash deploy/vps/deploy-production.sh`
- [ ] Smoke test: login all roles + one patient workflow
- [ ] Reception begins live patient intake
- [ ] On-call engineer available for 8 h

### T+1 day

- [ ] Review audit logs for denied access or errors
- [ ] Confirm backup ran overnight
- [ ] Collect staff feedback
- [ ] Document any incidents in ops log

### T+7 days (pilot review)

- [ ] QA E2E re-run on production
- [ ] DB counts within expected growth
- [ ] Performance acceptable (page load < 3 s on 4G)
- [ ] Go/no-go decision for expanded rollout

---

## Quick reference commands

```bash
# Deploy
sudo bash deploy/vps/deploy-production.sh

# Migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head

# Backup
ENV_FILE=.env.production COMPOSE_EXTRA="-f docker-compose.prod.yml" bash deploy/vps/backup-db.sh

# Health
curl -fsS https://<DOMAIN>/api/health
curl -fsS https://<DOMAIN>/api/health/ready

# QA
python scripts/qa_production_e2e.py
```

---

**Package owner:** DevOps / platform team  
**Clinic contact:** _[fill before go-live]_  
**On-call:** _[fill before go-live]_
