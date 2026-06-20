# Koloma UI Production Validation

- **Run:** 20260620-1211-c3f085
- **Frontend:** https://frontend-seven-rust-94.vercel.app
- **Screenshots:** `docs\ui_e2e_screenshots\koloma-prod-20260620-1211-c3f085`
- **Overall:** **FAIL**

| Role | Route | Status | Screenshot |
|------|-------|--------|------------|
| clinic_admin | `/clinical/admin` | PASS | clinic_admin.png |
| receptionist | `/clinical/reception` | PASS | receptionist.png |
| doctor | `/clinical/doctor` | PASS | doctor.png |
| lab | `/clinical/lab` | FAIL | Page.reload: net::ERR_ABORTED; maybe frame was detached?
Call log:
  - waiting for navigation until "domcontentloaded"
 |
| pharmacy | `/clinical/pharmacy` | PASS | pharmacy.png |
| cashier | `/clinical/billing` | PASS | cashier.png |
| pev_agent | `/clinical/pev` | PASS | pev_agent.png |
| nurse | `/clinical/nursing-care` | PASS | nurse.png |
| nutritionist | `/clinical/nutrition` | PASS | nutritionist.png |