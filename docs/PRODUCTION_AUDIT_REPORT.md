# Production Audit Report

- **Backend:** https://web-production-ad6a36.up.railway.app
- **Frontend:** https://frontend-seven-rust-94.vercel.app
- **Started:** 2026-06-18T14:34:25.836957Z

## Summary

| Status | Count |
|--------|-------|
| PASS | 56 |
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
- [PASS] **Frontend routes** — /clinical/reception (200)
- [PASS] **Frontend routes** — /clinical/nutrition (200)
- [PASS] **Frontend routes** — /clinical/immunization (200)
- [PASS] **Frontend routes** — /clinical/doctor (200)
- [PASS] **Frontend routes** — /clinical/lab (200)
- [PASS] **Frontend routes** — /clinical/pharmacy (200)
- [PASS] **Frontend routes** — /clinical/midwife (200)
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
- [PASS] **Isolation** — Clinic B cannot see clinic A patient (patient_id=25 visible_in_b=False)
- [PASS] **Smoke journey** — Using existing clinic (id=1)
- [PASS] **Smoke journey** — Staff receptionist login (audit.recv.b91f51df@sante-gn.test)
- [PASS] **Smoke journey** — Staff nutritionist login (audit.nutri.b91f51df@sante-gn.test)
- [PASS] **Smoke journey** — Staff midwife login (audit.midwife.b91f51df@sante-gn.test)
- [PASS] **Smoke journey** — Staff doctor login (audit.doc.b91f51df@sante-gn.test)
- [PASS] **Smoke journey** — Staff lab_technician login (audit.lab.b91f51df@sante-gn.test)
- [PASS] **Smoke journey** — Staff pharmacist login (audit.pharma.b91f51df@sante-gn.test)
- [PASS] **Smoke journey** — Nutrition assessment (201)
- [PASS] **Smoke journey** — Midwife /clinical/workflow/queue/pev (200)
- [PASS] **Smoke journey** — Midwife /clinical/workflow/queue/midwife (200)
- [PASS] **Smoke journey** — PEV record ({"id":5,"clinic_id":1,"patient_id":26,"vaccine_code":"BCG","vaccine_name":"BCG","dose_label":"Naissa)
- [PASS] **Smoke journey** — Laboratory queue (200)
- [PASS] **Smoke journey** — Pharmacy queue (200)
- [PASS] **Smoke journey** — Full child workflow completed ({"suffix": "b91f51df", "clinic_id": 1, "patient_id": 26, "workflow_id": 5, "after_reception": "nutrition", "after_nutrition": "pev", "after_pev": "doctor", "after_doctor": "doctor"})

## Smoke journey artifact

```json
{
  "suffix": "b91f51df",
  "clinic_id": 1,
  "patient_id": 26,
  "workflow_id": 5,
  "after_reception": "nutrition",
  "after_nutrition": "pev",
  "after_pev": "doctor",
  "after_doctor": "doctor"
}
```
