# Production Validation Checklist — v2.0 Full Clinic Workflow

## Pre-deployment

- [ ] `ENABLE_PILOT_SEED=false` in production `.env`
- [ ] `ENABLE_REMINDER_CRON=true` (or external cron calling `POST /clinical/reminders/process-due`)
- [ ] Alembic upgraded through `20260620_0012_reminders`
- [ ] WhatsApp Cloud API credentials configured (or dry-run accepted for pilot)
- [ ] PostgreSQL backup job verified (`docs/BACKUP_RESTORE.md`)

## Module smoke tests

### Phase 1 — Hospitalization
- [ ] Admin creates room + bed via `/clinical/hospitalization/rooms`
- [ ] Doctor creates admission from consultation
- [ ] Reception assigns bed; occupancy dashboard updates

### Phase 2 — Unified billing
- [ ] Generate unified invoice for patient with consult/lab/rx charges
- [ ] Pay invoice (cash / Orange Money)
- [ ] Download invoice PDF

### Phase 3 — Discharge
- [ ] Checklist shows zero pending charges after payment
- [ ] Execute discharge; EMR archive flag set
- [ ] Download discharge PDF

### Phase 4 — Radiology
- [ ] Doctor orders X-Ray from consultation
- [ ] Lab/radiology tech enters report
- [ ] Doctor validates report; charge appears on invoice

### Phase 5 — WhatsApp reminders
- [ ] Reminders scheduled on appointment creation (48h / 24h)
- [ ] `process-due` sends messages (dry-run log if no token)
- [ ] Patient confirm/cancel appears in notification center

## Automated QA

```bash
pip install -r requirements.txt
pytest tests/ -q
python scripts/qa_production_e2e.py
```

Target: **0 FAIL**, all extension tests pass.

## Frontend routes

| Route | Role |
|-------|------|
| `/clinical/hospitalization` | admin, receptionist, doctor |
| `/clinical/billing` | receptionist, cashier, admin |
| `/clinical/discharge` | receptionist, doctor, admin |
| `/clinical/radiology` | doctor, lab_technician, admin |
| `/clinical/notifications` | receptionist, doctor, admin |

## Sign-off

| Role | Name | Date | OK |
|------|------|------|-----|
| Clinical lead | | | |
| IT / DevOps | | | |
| Reception pilot | | | |
