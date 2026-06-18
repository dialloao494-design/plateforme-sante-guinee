# Production Audit Report

- **Backend:** https://web-production-ad6a36.up.railway.app
- **Frontend:** https://frontend-seven-rust-94.vercel.app
- **Started:** 2026-06-18T02:22:31.681960Z

## Summary

| Status | Count |
|--------|-------|
| PASS | 44 |
| WARN | 1 |
| BLOCKER | 1 |

## Blocking issues (clinic deployment)

- **Email:** SMTP/Resend not configured on Railway — {"status":"not_configured","configured":false,"provider":"none","sender_set":false,"frontend_url_set":true}

## All findings

- [PASS] **Infrastructure** — GET /health -> 200 ({"status":"ok","version":"1.0.0","debug":false,"database":"***"})
- [PASS] **Infrastructure** — GET /health/ready -> 200 ({"status":"ready","database":"ok"})
- [BLOCKER] **Email** — SMTP/Resend not configured on Railway ({"status":"not_configured","configured":false,"provider":"none","sender_set":false,"frontend_url_set":true})
- [PASS] **Infrastructure** — GET /auth/email-status -> 200 ({"configured":false,"provider":"none","sender_set":false,"frontend_url_set":true})
- [PASS] **Infrastructure** — Frontend home (200)
- [PASS] **Frontend routes** — / (200)
- [PASS] **Frontend routes** — /login (200)
- [PASS] **Frontend routes** — /signup (200)
- [PASS] **Frontend routes** — /forgot-password (200)
- [PASS] **Frontend routes** — /reset-password (200)
- [PASS] **Frontend routes** — /verify-email (200)
- [PASS] **Auth** — Doctor register + token
- [PASS] **Auth** — Login after register
- [PASS] **Auth** — Duplicate email rejected (409)
- [PASS] **Auth** — Weak password rejected (422)
- [PASS] **Auth** — Forgot password endpoint (200)
- [PASS] **Auth** — Invalid reset token rejected (400)
- [PASS] **Auth** — Change password ({"message":"Mot de passe mis à jour"})
- [PASS] **Auth** — Login with new password
- [PASS] **Roles** — Login clinic_admin (clinic.admin.a@sante-gn.test)
- [PASS] **Roles** — Login reception_a (reception.demo@sante-gn.test)
- [PASS] **Roles** — Login reception_b (reception.beta@sante-gn.test)
- [PASS] **Roles** — Login doctor (doctor.demo@sante-gn.test)
- [PASS] **Dashboards** — reception_a GET /clinical/reception/queue (200)
- [PASS] **Dashboards** — reception_a GET /clinical/workflow/queue/reception (200)
- [PASS] **Dashboards** — doctor GET /clinical/doctor/queue (200)
- [PASS] **Dashboards** — doctor GET /clinical/workflow/queue/doctor (200)
- [PASS] **Dashboards** — clinic_admin GET /clinical/operations/summary (200)
- [PASS] **Dashboards** — clinic_admin GET /clinical/staff (200)
- [PASS] **Dashboards** — reception_a GET /clinical/nutrition/patients/1/history (200)
- [PASS] **Dashboards** — reception_a GET /clinical/immunization/schedule (200)
- [PASS] **Dashboards** — reception_a GET /clinical/lab/orders (403)
- [PASS] **Dashboards** — reception_a GET /clinical/pharmacy/orders (403)
- [PASS] **Security RBAC** — reception_a denied /clinical/doctor/queue (403)
- [PASS] **Security RBAC** — reception_a denied /clinical/admin/backup-status (403)
- [PASS] **Isolation** — Clinic B cannot see clinic A patient (patient_id=18 visible_in_b=False)
- [PASS] **Smoke journey** — Using existing clinic (id=1)
- [PASS] **Smoke journey** — Staff receptionist login (audit.recv.71d8a626@sante-gn.test)
- [PASS] **Smoke journey** — Staff nutritionist login (audit.nutri.71d8a626@sante-gn.test)
- [PASS] **Smoke journey** — Staff midwife login (audit.midwife.71d8a626@sante-gn.test)
- [PASS] **Smoke journey** — Staff doctor login (audit.doc.71d8a626@sante-gn.test)
- [PASS] **Smoke journey** — Staff lab_technician login (audit.lab.71d8a626@sante-gn.test)
- [PASS] **Smoke journey** — Staff pharmacist login (audit.pharma.71d8a626@sante-gn.test)
- [PASS] **Smoke journey** — Nutrition assessment (201)
- [WARN] **Smoke journey** — PEV record ({"detail":[{"type":"missing","loc":["body","vaccine_name"],"msg":"Field required","input":{"patient_)
- [PASS] **Smoke journey** — Full child workflow completed ({"suffix": "71d8a626", "clinic_id": 1, "patient_id": 19, "workflow_id": 2, "after_reception": "nutrition", "after_nutrition": "pev", "after_pev": "doctor", "after_doctor": "doctor"})

## Smoke journey artifact

```json
{
  "suffix": "71d8a626",
  "clinic_id": 1,
  "patient_id": 19,
  "workflow_id": 2,
  "after_reception": "nutrition",
  "after_nutrition": "pev",
  "after_pev": "doctor",
  "after_doctor": "doctor"
}
```
