# Koloma Production Validation

- **Run:** 20260620-1201-e50092
- **Backend:** https://web-production-ad6a36.up.railway.app
- **Frontend:** https://frontend-seven-rust-94.vercel.app
- **Overall:** **PASS**

## Accounts tested

| Role | Email |
|------|-------|
| clinic_admin | `centre.koloma.admin@sante-gn.test` |
| receptionist | `monemoumariejeanne94@gmail.com` |
| doctor | `saatollno69@gmail.com` |
| lab | `salifoudian719@gmail.com` |
| pharmacy | `thioutobarry90@gmail.com` |
| nutritionist | `dialloaissatoutoupe013@gmail.com` |
| pev_agent | `niepousalomonloua@gmail.com` |
| nurse | `infirmsadjo01@gmail.com` |

## Results

| Category | Check | Status | Detail |
|----------|-------|--------|--------|
| Accounts | Login clinic_admin | PASS | centre.koloma.admin@sante-gn.test clinic_id=13 role=clinic_admin |
| RBAC | clinic_admin GET /clinical/staff | PASS | expected=200 got=200 |
| Accounts | Login receptionist | PASS | monemoumariejeanne94@gmail.com clinic_id=13 role=receptionist |
| RBAC | receptionist GET /clinical/reception/queue | PASS | expected=200 got=200 |
| RBAC | receptionist GET /clinical/lab/orders | PASS | expected=403 got=403 |
| Accounts | Login doctor | PASS | saatollno69@gmail.com clinic_id=13 role=doctor |
| RBAC | doctor GET /clinical/doctor/queue | PASS | expected=200 got=200 |
| RBAC | doctor GET /clinical/pharmacy/orders | PASS | expected=403 got=403 |
| Accounts | Login lab | PASS | salifoudian719@gmail.com clinic_id=13 role=lab_technician |
| RBAC | lab GET /clinical/lab/orders | PASS | expected=200 got=200 |
| RBAC | lab GET /clinical/reception/queue | PASS | expected=403 got=403 |
| Accounts | Login pharmacy | PASS | thioutobarry90@gmail.com clinic_id=13 role=pharmacist |
| RBAC | pharmacy GET /clinical/pharmacy/orders | PASS | expected=200 got=200 |
| RBAC | pharmacy GET /clinical/lab/orders | PASS | expected=403 got=403 |
| Accounts | Login nutritionist | PASS | dialloaissatoutoupe013@gmail.com clinic_id=13 role=nutritionist |
| RBAC | nutritionist GET /clinical/nutrition/dashboard | PASS | expected=200 got=200 |
| RBAC | nutritionist GET /clinical/lab/orders | PASS | expected=403 got=403 |
| Accounts | Login pev_agent | PASS | niepousalomonloua@gmail.com clinic_id=13 role=pev_agent |
| RBAC | pev_agent GET /clinical/immunization/dashboard | PASS | expected=200 got=200 |
| RBAC | pev_agent GET /clinical/pharmacy/orders | PASS | expected=403 got=403 |
| Accounts | Login nurse | PASS | infirmsadjo01@gmail.com clinic_id=13 role=nurse |
| RBAC | nurse GET /clinical/nursing-care/dashboard | PASS | expected=200 got=200 |
| RBAC | nurse GET /clinical/doctor/queue | PASS | expected=403 got=403 |
| Admin | Staff list Koloma only | PASS | 15 staff at clinic 13 |
| Admin | Blocked from other clinic staff | PASS | status=403 (clinic admin must not list clinic 1) |
| Accounts | Cashier exists | PASS | koloma.cashier.f34070@sante-gn.test |
| Frontend | Route /clinical/pev | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/hospitalization | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/nursing-care | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/nutrition | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/patient-history | PASS | http=200 bundle=lazy/spa |
| Frontend | Route /clinical/admin | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/reception | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/doctor | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/lab | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/pharmacy | PASS | http=200 bundle=yes |
| Frontend | Route /clinical/billing | PASS | http=200 bundle=yes |
| PEV | Field options API | PASS | status=200 |
| PEV | Injection sites configured | PASS | 7 |
| PEV | Monthly register API | PASS | rows=8 |
| PEV | Monthly report register_rows | PASS | total=8 |
| Pharmacy | Update stock | PASS | KOL-e50092 status=201 |
| Setup | Doctor ID for appointments | PASS | 35 |
| Patient A | Pharmacy order queued | PASS | 137 |
| Patient A | Cashier payment | PASS | 2 charge(s) paid |
| Patient B | Lab validated | PASS | order=57 |
| Patient B | End-to-end lab→pharmacy→cashier | PASS | paid=3 |
| Patient C | PEV vaccination | PASS | patient_id=229 |
| Patient C | Nutrition follow-up | PASS |  |
| Patient C | Nursing procedures x4 | PASS | injection, perfusion, dressing, suture |
| History | Central journey + timeline patient 227 | PASS | journey=200 timeline=200 events=3 |
| History | Central journey + timeline patient 228 | PASS | journey=200 timeline=200 events=5 |
| History | Central journey + timeline patient 229 | PASS | journey=200 timeline=200 events=6 |
| Phase2 | nurse /clinical/nursing-care/register | PASS | status=200 rows=34 |
| Phase2 | nutritionist /clinical/nutrition/register | PASS | status=200 rows=9 |
| Phase2 | receptionist /clinical/hospitalization/reports/monthly | PASS | status=200 |
| Phase2 | lab /clinical/lab/dashboard | PASS | status=200 |
| Phase2 | lab /clinical/lab/reports/monthly | PASS | status=200 |
| Phase2 | lab /clinical/lab/catalog | PASS | status=200 |
| Phase2 | pharmacy /clinical/pharmacy/dashboard | PASS | status=200 |
| Phase2 | pharmacy /clinical/pharmacy/reports/monthly | PASS | status=200 |
| Phase2 | clinic_admin /clinical/reports/koloma/monthly | PASS | status=200 modules=['year', 'month', 'clinic_id', 'pev', 'nursing', 'hospitaliza |
| Phase2 | doctor patient timeline | PASS | patient=229 status=200 |
| Phase2 | receptionist patient timeline | PASS | patient=229 status=200 |
| Phase2 | nurse patient timeline | PASS | patient=229 status=200 |