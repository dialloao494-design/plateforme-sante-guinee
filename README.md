# Plateforme Santé Guinée

Digital health platform for Guinea — clinic workflows (reception, doctor, laboratory, pharmacy), patient portal, teleconsultation.

**Repository:** [github.com/dialloao494-design/plateforme-sante-guinee](https://github.com/dialloao494-design/plateforme-sante-guinee)

## Quick start (local)

```powershell
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git
cd plateforme-sante-guinee
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend-sante\frontend
npm install
npm run dev
```

- API: http://127.0.0.1:8000/docs  
- App: http://127.0.0.1:5173  

## Documentation

| Guide | Description |
|-------|-------------|
| [docs/PRODUCTION_DEPLOYMENT_PACKAGE.md](docs/PRODUCTION_DEPLOYMENT_PACKAGE.md) | **Pilot go-live — all checklists** |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Environment, Docker, VPS production |
| [docs/MIGRATIONS.md](docs/MIGRATIONS.md) | Alembic & schema upgrades |
| [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md) | PostgreSQL backup & recovery |
| [.env.example](.env.example) | Environment variable template |

## Clinical workflow

```
Patient → Reception (intake + encaissement) → Doctor → Laboratory → Pharmacy → Follow-up → Completed
```

Payments are collected **at reception** (cash / Orange Money). Each role has an isolated dashboard and API permissions.

## Pilot accounts

Enabled when `ENABLE_PILOT_SEED=true` (disable in public production).

| Role | Email | Password |
|------|-------|----------|
| Manager | `admin@pilot.local` | `AdminPilot1!` |
| Reception | `reception@pilot.local` | `ReceptionPilot1!` |
| Doctor | `dr.pilot@pilot.local` | `DoctorPilot1!` |
| Lab | `lab@pilot.local` | `LabPilot1!` |
| Pharmacy | `pharmacy@pilot.local` | `PharmacyPilot1!` |
| Patient | `test.patient@example.com` | `Patient123!` |

Simulated history patients (after seed): `sim.patient.001@pilot.local` / `SimPatient1!`

## QA validation

```bash
python -m services.medical_history_seed
python scripts/qa_production_e2e.py
pytest tests/ -q
```

Report: `evidence/qa_production_report.json`

## Stack

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL / SQLite, Alembic, JWT  
- **Frontend:** React, Vite  
- **Infra:** Docker Compose, Nginx, Let's Encrypt, Jitsi (teleconsultation)  

## Security

Never commit `.env`, database dumps, or SSL certificates. Generate secrets with `python generate_secrets.py`.

For handover documentation (legacy): [`HANDOVER/README_START_HERE.md`](HANDOVER/README_START_HERE.md)
