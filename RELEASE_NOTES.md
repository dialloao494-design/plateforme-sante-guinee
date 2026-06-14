# Release Notes — v1.0.0-pilot

**Release date:** 2026-06-14  
**Tag:** `v1.0.0-pilot`  
**Repository:** https://github.com/dialloao494-design/plateforme-sante-guinee

---

## Overview

First **pilot-production** release of the Plateforme Santé Guinée clinic information system (CIS). This build is QA-validated and approved for pilot clinic deployment on VPS (Docker, PostgreSQL, HTTPS).

---

## Stripe removal

- Removed Stripe Checkout, webhooks, and all Stripe-related services, models, tests, and documentation.
- Online card payment UI removed from the frontend.
- Clinic payments are collected **in person at reception** via cash or Orange Money (`POST /clinical/billing/charges/{id}/pay`).
- Legacy admin manual settlement retained for portal appointments (`POST /rendezvous/{id}/confirm-payment`).
- Environment templates updated — no `STRIPE_*` keys required.

---

## Reception + cashier merge

- Single **Reception workspace** at `/clinical/reception` combines patient intake, appointment booking, check-in, and **encaissement** (cash collection).
- Cashier role retained for RBAC compatibility; operational workflow unified under reception dashboard.
- Pending charges, daily revenue, and payment recording accessible from one screen.

---

## Role isolation

Strict API and frontend route guards per clinical station:

| Role | Access |
|------|--------|
| Reception | Intake, appointments, billing pay/read |
| Doctor | Consultation queue, prescriptions, lab orders, follow-ups |
| Lab | Lab queue and result validation only |
| Pharmacy | Pharmacy queue and dispensing only |
| Admin | Operations summary, audit logs, staff, backup status |
| Patient | Portal: appointments, medical history |

Cross-role API access returns **403** (verified in QA). Doctor cannot read lab/pharmacy queues; lab/pharmacy cannot access each other's queues.

---

## Medical history

- Permanent patient medical record with allergies, chronic conditions, vitals, and timeline.
- Patient portal at `/my-records` (Dossier médical).
- Doctor can record vitals and view patient history during consultation.
- Admin/clinical staff can query full history via API.
- Soft-delete on clinical records; patient archive blocked when clinical history exists.
- Seed: 50 simulated patients with 2–5 visit longitudinal history (`python -m services.medical_history_seed`).

---

## Follow-up appointments

- Doctor schedules follow-ups: 7d, 15d, 1m, 3m, 6m, or custom date.
- Reception dashboard shows due today, overdue, and upcoming follow-ups.
- Follow-up records linked to consultations and visible in patient timeline.

---

## QA validation results

Automated E2E run (`scripts/qa_production_e2e.py`) — evidence in `evidence/qa_production_report.json`:

| Metric | Result |
|--------|--------|
| **PASS** | 39 |
| **WARNING** | 0 |
| **FAIL** | 0 |

Unit tests: **126 passed**, 1 skipped.

Data volume at validation:

| Entity | Count |
|--------|-------|
| Patients | 70 |
| Appointments | 202 |
| Consultations | 184 |
| Lab orders | 124 |
| Prescriptions | 181 |
| Follow-ups | 125 |
| Audit logs | 275 |

Full workflow validated: Patient → Reception → Doctor → Laboratory → Pharmacy → Follow-up → Completed.

---

## Production readiness

### Documentation

| Document | Path |
|----------|------|
| Quick start | `README.md` |
| Deployment guide | `docs/DEPLOYMENT.md` |
| Database migrations | `docs/MIGRATIONS.md` |
| Backup & restore | `docs/BACKUP_RESTORE.md` |
| Full deployment package (checklists) | `docs/PRODUCTION_DEPLOYMENT_PACKAGE.md` |
| Environment template | `.env.example`, `.env.production.example` |

### Security

- JWT secrets required (32+ chars in production).
- Login rate limit: 30/min (production), 120/min (development).
- `ENABLE_PILOT_SEED=false` required for public production.
- Clinical audit logging enabled.
- Attachments not served from public paths.

### Deploy

```bash
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git
git checkout v1.0.0-pilot
cp .env.production.example .env.production
cp deploy/env/.env.backend.example deploy/env/.env.backend
sudo bash deploy/vps/init-ssl.sh
sudo bash deploy/vps/deploy-production.sh
docker compose exec backend alembic upgrade head
python scripts/qa_production_e2e.py   # expect FAIL=0
```

---

## Pilot accounts (development / pilot only)

Enabled when `ENABLE_PILOT_SEED=true`. **Disable in public production.**

| Role | Email | Password |
|------|-------|----------|
| Manager | `admin@pilot.local` | `AdminPilot1!` |
| Reception | `reception@pilot.local` | `ReceptionPilot1!` |
| Doctor | `dr.pilot@pilot.local` | `DoctorPilot1!` |
| Lab | `lab@pilot.local` | `LabPilot1!` |
| Pharmacy | `pharmacy@pilot.local` | `PharmacyPilot1!` |
| Patient | `test.patient@example.com` | `Patient123!` |

Simulated history patients: `sim.patient.001@pilot.local` / `SimPatient1!`

---

## Upgrade notes

- Run `alembic upgrade head` before starting the application.
- Alembic revisions through `20260620_0012_reminders` (hospitalization, billing, discharge, radiology, reminders).
- No Stripe migration required — feature fully removed.

---

## v2.0 — Full clinic workflow (2026-06)

### Phase 1 — Hospitalization
- Room/bed management, admissions from consultation, bed assignment, occupancy dashboard.

### Phase 2 — Unified billing
- Clinical visits, unified invoices, payment records, invoice PDF receipts.

### Phase 3 — Patient discharge
- Discharge checklist (billing + pharmacy validation), discharge summary PDF, EMR archive.

### Phase 4 — Radiology
- Imaging orders from consultation, radiology worklist, report entry/validation, EMR attachment, billing integration.

### Phase 5 — WhatsApp reminders
- 48h/24h reminder scheduling on appointment creation, patient confirm/cancel/reschedule, staff notification center.

See `docs/API_MODULES.md` and `docs/PRODUCTION_VALIDATION_CHECKLIST.md` for deployment validation.

---

## Known limitations (pilot)

- Teleconsultation requires Jitsi configuration (optional).
- Orange Money treasury integration is stub-ready; live rails require env flags.
- QA screenshot evidence (`evidence/*.png`) is local-only; JSON reports are in repository.

---

**Prepared by:** Platform DevOps  
**Review status:** Ready for external engineering review
