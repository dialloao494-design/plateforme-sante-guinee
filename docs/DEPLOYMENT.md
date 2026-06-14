# Deployment Guide — Plateforme Santé Guinée

Pilot-ready clinic information system (CIS): reception, doctor, laboratory, pharmacy, patient portal.

**Full checklists:** [PRODUCTION_DEPLOYMENT_PACKAGE.md](./PRODUCTION_DEPLOYMENT_PACKAGE.md)

## Prerequisites

- Python 3.11+ (backend) or Docker on Ubuntu 22.04+
- Node.js 18+ (frontend build)
- PostgreSQL 15+ (production)
- Domain + DNS for HTTPS (production)

## Environment template

```bash
cp .env.example .env
cp .env.production.example .env.production   # VPS only
cp deploy/env/.env.backend.example deploy/env/.env.backend
python generate_secrets.py                   # JWT / rotation keys
```

Required variables:

| Variable | Development | Production |
|----------|-------------|------------|
| `ENVIRONMENT` | `development` | `production` |
| `SECRET_KEY` / `JWT_SECRET` | random 32+ chars | strong random 32+ chars |
| `DATABASE_URL` | `sqlite:///./sante.db` | PostgreSQL URL |
| `ENABLE_PILOT_SEED` | `true` (pilot only) | **`false`** |
| `FRONTEND_URL` | `http://127.0.0.1:5173` | HTTPS app URL |
| `RATE_LIMIT_LOGIN` | `120/minute` (default) | `30/minute` (default) |

Clinic payments are collected **in person at reception** (`/clinical/billing/charges/{id}/pay`). No online card gateway is required.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend-sante\frontend
npm install
npm run dev
```

## Database migrations

See [MIGRATIONS.md](./MIGRATIONS.md).

After first deploy:

```bash
alembic upgrade head
python -m services.medical_history_seed   # optional pilot longitudinal data
```

## Docker (local / VPS)

```bash
cp .env.production.example .env.production
docker compose --env-file .env.production up -d --build
```

Health check: `GET /health`

## Production VPS (Ubuntu 22.04)

```bash
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git /opt/plateforme-sante
cd /opt/plateforme-sante
cp .env.production.example .env.production
# Edit: DOMAIN, POSTGRES_PASSWORD, SECRET_KEY, CORS, ENABLE_PILOT_SEED=false

sudo bash deploy/vps/init-ssl.sh
sudo bash deploy/vps/deploy-production.sh
```

Validate:

```bash
python scripts/qa_production_e2e.py
pytest tests/ -q
```

## Backup & restore

See [BACKUP_RESTORE.md](./BACKUP_RESTORE.md).

## Pilot accounts

When `ENABLE_PILOT_SEED=true`:

| Role | Email | Password |
|------|-------|----------|
| Manager | `admin@pilot.local` | `AdminPilot1!` |
| Reception | `reception@pilot.local` | `ReceptionPilot1!` |
| Doctor | `dr.pilot@pilot.local` | `DoctorPilot1!` |
| Lab | `lab@pilot.local` | `LabPilot1!` |
| Pharmacy | `pharmacy@pilot.local` | `PharmacyPilot1!` |
| Patient | `test.patient@example.com` | `Patient123!` |

Simulated history patients (after seed): `sim.patient.001@pilot.local` / `SimPatient1!`

## QA before go-live

```bash
python scripts/qa_production_e2e.py
python scripts/qa_db_counts.py
python scripts/verify_medical_history_seed.py
```

Report written to `evidence/qa_production_report.json`.
