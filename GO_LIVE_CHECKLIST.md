# Go-Live Checklist

Complete every item in order. Do **not** skip security or database steps.

**Target verdict after completion:** Ready for clinic deployment on production VPS.

---

## Phase 0 — Pre-flight (T-7 days)

- [ ] **G0-1** Staging UAT completed using [CLINIC_ACCEPTANCE_CHECKLIST.md](./CLINIC_ACCEPTANCE_CHECKLIST.md) — all sections Pass
- [ ] **G0-2** Review [FINAL_PRODUCTION_READINESS_REPORT.md](./FINAL_PRODUCTION_READINESS_REPORT.md) — no open BLK items
- [ ] **G0-3** Review [SECURITY_AUDIT_REPORT.md](./SECURITY_AUDIT_REPORT.md)
- [ ] **G0-4** Change window communicated to clinic staff
- [ ] **G0-5** Rollback plan documented (restore latest backup)

---

## Phase 1 — Infrastructure (T-1 day)

- [ ] **G1-1** Ubuntu 22.04+ VPS provisioned (4 GB RAM minimum recommended)
- [ ] **G1-2** DNS A record points `DOMAIN` to VPS IP
- [ ] **G1-3** Firewall: 80/443 open; SSH restricted to ops IPs
- [ ] **G1-4** Docker + Docker Compose installed
- [ ] **G1-5** Repository cloned to `/opt/plateforme-sante` (or agreed path)

---

## Phase 2 — Secrets & environment (T-1 day)

Copy and edit production env:

```bash
cp .env.production.example .env.production
python generate_secrets.py   # or openssl rand -base64 48
```

| Variable | Required value | Verified |
|----------|----------------|:--------:|
| `ENVIRONMENT=production` | | ☐ |
| `DEBUG=false` | | ☐ |
| `DOMAIN` | Clinic HTTPS domain | ☐ |
| `ALLOWED_HOSTS` | Domain + `backend` | ☐ |
| `TRUSTED_PROXY_HOSTS` | Reverse proxy IPs/hostnames (**never** `*`) | ☐ |
| `JWT_SECRET` / `SECRET_KEY` | 32+ random chars | ☐ |
| `POSTGRES_PASSWORD` | 12+ strong password | ☐ |
| `REMINDER_RESPOND_TOKEN` | 32+ random chars | ☐ |
| `ENABLE_PILOT_SEED=false` | | ☐ |
| `ENABLE_STARTUP_TEST_USER=false` | | ☐ |
| `ENABLE_STARTUP_SEED=false` | | ☐ |
| `ENABLE_DEMO_CLINIC_SEED=false` | | ☐ |
| `BYPASS_AVAILABILITY_VALIDATION=false` | | ☐ |
| `VITE_API_URL` | `https://<domain>/api` | ☐ |
| `WHATSAPP_ACCESS_TOKEN` | Meta Cloud API token | ☐ |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta phone number ID | ☐ |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verify string | ☐ |
| `ENABLE_REMINDER_CRON=true` | Or external cron configured | ☐ |
| `LOG_FORMAT=json` | | ☐ |
| `SENTRY_DSN` | Optional but recommended | ☐ |

- [ ] **G2-1** `.env.production` never committed to git
- [ ] **G2-2** Boot guard passes locally: `ENVIRONMENT=production python -c "from core.settings import AppSettings; AppSettings().enforce_production_boot()"`

---

## Phase 3 — Database (T-0 deploy)

- [ ] **G3-1** Pre-deploy backup (empty DB): document baseline
- [ ] **G3-2** Start PostgreSQL container
- [ ] **G3-3** Run migrations:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production exec backend alembic upgrade head
```

- [ ] **G3-4** Confirm head: `alembic current` → `20260622_0014_patient_user_id_unique`
- [ ] **G3-5** Create initial admin via secure channel (not pilot seed):

  - Option A: `ENABLE_ADMIN_BOOTSTRAP=true` with strong `ADMIN_BOOTSTRAP_PASSWORD` (disable after first boot)
  - Option B: `POST /users/admins` from secured ops console

- [ ] **G3-6** Assign admin to clinic; create staff accounts with strong passwords

---

## Phase 4 — Deploy application (T-0)

- [ ] **G4-1** SSL certificate: `sudo bash deploy/vps/init-ssl.sh`
- [ ] **G4-2** Deploy: `sudo bash deploy/vps/deploy-production.sh`
- [ ] **G4-3** Health check: `curl -sf https://<domain>/health`
- [ ] **G4-4** Readiness: `curl -sf https://<domain>/health/ready`
- [ ] **G4-5** API docs disabled: `curl -o /dev/null -w "%{http_code}" https://<domain>/docs` → `404`
- [ ] **G4-6** Frontend loads over HTTPS without mixed-content errors

---

## Phase 5 — WhatsApp & reminders (T-0)

- [ ] **G5-1** Meta webhook URL: `https://<domain>/api/clinical/reminders/whatsapp/webhook`
- [ ] **G5-2** Webhook verify succeeds (Meta dashboard green check)
- [ ] **G5-3** Create test appointment → confirm 48h/24h reminders in DB
- [ ] **G5-4** Process due reminders: cron or `POST /clinical/reminders/process-due` (admin)
- [ ] **G5-5** Patient respond URL includes HMAC token when using web link (production token required)
- [ ] **G5-6** Staff notification center shows confirmation/cancel/reschedule events

---

## Phase 6 — Backup & monitoring (T-0)

- [ ] **G6-1** Configure daily cron:

```bash
0 2 * * * cd /opt/plateforme-sante && ENV_FILE=.env.production bash deploy/vps/backup-db.sh >> /var/log/sante-backup.log 2>&1
```

- [ ] **G6-2** Run first backup manually; verify `backups/sante_*.sql.gz` exists
- [ ] **G6-3** Run `bash scripts/db/backup_verify.sh`
- [ ] **G6-4** Schedule monthly restore drill on staging (`scripts/db/restore_drill.sh`)
- [ ] **G6-5** Uptime monitoring on `/health` (UptimeRobot, Pingdom, etc.)
- [ ] **G6-6** Optional: Sentry alerts for 5xx errors

---

## Phase 7 — Post-deploy smoke test (T+0, within 2 hours)

Run on production with real staff test accounts (not pilot/demo):

- [ ] **G7-1** Register patient → search → appointment → check-in
- [ ] **G7-2** Consultation → lab order → result → validate
- [ ] **G7-3** Pay charges → verify daily revenue > 0
- [ ] **G7-4** Discharge test patient (or cancel appointment)
- [ ] **G7-5** Automated QA: `python scripts/qa_production_e2e.py` (update credentials to production test staff)

Optional full regression:

```bash
pytest tests/ -q
```

(Run in CI or staging — not required on production server.)

---

## Phase 8 — Go-live approval

| Gate | Owner | Date | OK |
|------|-------|------|:--:|
| All Phase 0–7 items complete | Ops lead | | ☐ |
| Clinic director UAT sign-off | Clinic | | ☐ |
| Security review (no critical/high open) | Vendor | | ☐ |
| Backup verified | Ops lead | | ☐ |

---

## Rollback procedure (if critical failure)

1. Stop traffic (maintenance page or DNS rollback).
2. Restore latest backup per [docs/BACKUP_RESTORE.md](./docs/BACKUP_RESTORE.md).
3. Verify `/health/ready` and smoke test.
4. Post-incident review before re-attempt.

---

## Quick reference — blocking fixes from audit

| Blocker | Command / action |
|---------|------------------|
| Migrations | `alembic upgrade head` |
| Secrets | Fill `.env.production` per Phase 2 |
| Staging smoke | `python scripts/qa_production_e2e.py` |
| WhatsApp | Configure Meta webhook + tokens |
| Backup drill | `bash scripts/db/restore_drill.sh backups/<file>.sql.gz` |

**When all phases are checked:** Update [FINAL_PRODUCTION_READINESS_REPORT.md](./FINAL_PRODUCTION_READINESS_REPORT.md) verdict to **READY FOR CLINIC DEPLOYMENT**.
