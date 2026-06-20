# Field Readiness Validation — Centre de Santé Koloma

- **Run:** 20260620-1150-27eb61
- **Overall:** **FAIL** (77 pass / 3 fail)
- **Backend:** https://web-production-ad6a36.up.railway.app
- **Frontend:** https://frontend-seven-rust-94.vercel.app
- **Test patient:** 224
- **Screenshots:** `docs\ui_e2e_screenshots\koloma-prod-20260620-1152-b7b8c8`

## Results by phase

| Phase | Category | Check | Status | Detail |
|-------|----------|-------|--------|--------|
| 1 | Accounts | Login clinic_admin | PASS | centre.koloma.admin@sante-gn.test clinic=13 role=clinic_admin |
| 1 | Accounts | Login receptionist | PASS | monemoumariejeanne94@gmail.com clinic=13 role=receptionist |
| 1 | Accounts | Login doctor | PASS | saatollno69@gmail.com clinic=13 role=doctor |
| 1 | Accounts | Login pev_agent | PASS | niepousalomonloua@gmail.com clinic=13 role=pev_agent |
| 1 | Accounts | Login nutritionist | PASS | dialloaissatoutoupe013@gmail.com clinic=13 role=nutritionist |
| 1 | Accounts | Login nurse | PASS | infirmsadjo01@gmail.com clinic=13 role=nurse |
| 1 | Accounts | Login lab_technician | PASS | salifoudian719@gmail.com clinic=13 role=lab_technician |
| 1 | Accounts | Login pharmacist | PASS | thioutobarry90@gmail.com clinic=13 role=pharmacist |
| 1 | RBAC | receptionist /clinical/reception/queue | PASS | expected=200 got=200 |
| 1 | RBAC | receptionist /clinical/lab/orders | PASS | expected=403 got=403 |
| 1 | RBAC | doctor /clinical/doctor/queue | PASS | expected=200 got=200 |
| 1 | RBAC | doctor /clinical/pharmacy/orders | PASS | expected=403 got=403 |
| 1 | RBAC | lab_technician /clinical/lab/orders | PASS | expected=200 got=200 |
| 1 | RBAC | lab_technician /clinical/reception/queue | PASS | expected=403 got=403 |
| 1 | RBAC | pharmacist /clinical/pharmacy/orders | PASS | expected=200 got=200 |
| 1 | RBAC | pharmacist /clinical/lab/orders | PASS | expected=403 got=403 |
| 1 | RBAC | pev_agent /clinical/immunization/dashboard | PASS | expected=200 got=200 |
| 1 | RBAC | nutritionist /clinical/nutrition/dashboard | PASS | expected=200 got=200 |
| 1 | RBAC | nurse /clinical/nursing-care/dashboard | PASS | expected=200 got=200 |
| 1 | RBAC | clinic_admin /clinical/staff?clinic_id=13 | PASS | expected=200 got=200 |
| 1 | E2E | Reception — register patient | PASS | patient_id=224 |
| 1 | E2E | Reception — check-in | PASS | appointment=182 |
| 1 | E2E | Doctor — start consultation | PASS | consultation_id=141 |
| 1 | E2E | Laboratory — order + validate | PASS | order=56 |
| 1 | E2E | Doctor — prescription | PASS |  |
| 1 | E2E | Pharmacy — dispense | PASS | 136 |
| 1 | E2E | Billing — cashier payment | PASS | paid=3 |
| 1 | E2E | PEV — vaccination | PASS |  |
| 1 | E2E | Nutrition — assessment | PASS |  |
| 1 | E2E | Nursing — procedures | PASS | injection + dressing |
| 1 | E2E | Hospitalization — admit + discharge | PASS | admission_id=16 |
| 1 | E2E | Discharge — execute | PASS | visit=156 force=False status=201 |
| 1 | Timeline | Central patient timeline | PASS | modules=['reception', 'doctor', 'pev', 'nutrition', 'nursing', 'hospit |
| 1 | Reports | Monthly reports | PASS | status=200 |
| 1 | Reports | Monthly reports | PASS | status=200 |
| 1 | Reports | Monthly reports | PASS | status=200 |
| 1 | Reports | Monthly reports | FAIL | status=500 |
| 1 | Reports | Monthly reports | PASS | status=200 |
| 1 | Reports | Monthly reports | PASS | status=200 |
| 1 | Reports | Monthly koloma | FAIL | status=500 |
| 1 | Dashboards | receptionist /clinical/reception/queue | PASS | status=200 |
| 1 | Dashboards | doctor /clinical/doctor/queue | PASS | status=200 |
| 1 | Dashboards | pev_agent /clinical/immunization/dashboard | PASS | status=200 |
| 1 | Dashboards | nutritionist /clinical/nutrition/dashboard | PASS | status=200 |
| 1 | Dashboards | nurse /clinical/nursing-care/dashboard | PASS | status=200 |
| 1 | Dashboards | lab_technician /clinical/lab/dashboard | PASS | status=200 |
| 1 | Dashboards | pharmacist /clinical/pharmacy/dashboard | PASS | status=200 |
| 1 | Dashboards | receptionist /clinical/hospitalization/dashboard | PASS | status=200 |
| 1 | DB | Patient journey API | PASS | keys=['patient_id', 'appointments', 'consultations', 'immunizations'] |
| 1 | DB | PEV history linked to patient | PASS | records=1 |
| 1 | DB | Nutrition history linked | PASS | records=1 |
| 1 | DB | Nursing procedures linked | PASS | count=2 |
| 1 | Routes | /clinical/admin | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/reception | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/doctor | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/pev | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/nutrition | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/nursing-care | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/lab | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/pharmacy | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/patient-history | PASS | http=200 bundle=spa |
| 1 | Routes | /clinical/reports | PASS | http=200 bundle=yes |
| 1 | Routes | /clinical/billing | PASS | http=200 bundle=yes |
| 2 | Infra | /health | PASS | {"status":"ok","version":"1.0.0","debug":false,"database":"***"} |
| 2 | Infra | /health/ready | PASS | {"status":"ready","database":"ok"} |
| 2 | Isolation | Admin blocked from clinic 1 staff | PASS | status=403 |
| 2 | Isolation | Staff list clinic-scoped | PASS | 15 staff |
| 2 | Auth | Timeline requires auth | PASS | authenticated OK |
| 2 | Auth | Timeline rejects anonymous | PASS | status=401 |
| 2 | Deploy | Railway backend reachable | PASS | https://web-production-ad6a36.up.railway.app |
| 2 | Deploy | Vercel frontend reachable | PASS | https://frontend-seven-rust-94.vercel.app |
| 2 | Deploy | GitHub Actions workflow present | PASS | deploy-railway-vercel.yml |
| 2 | Deploy | DB migrations module present | PASS | ensure_clinical_modules_schema |
| 4 | Multi-clinic | Create clinic | PASS | id=14 name=Clinique Pilote Field-27eb61 |
| 4 | Multi-clinic | Create clinic admin | PASS | admin.field.27eb61@sante-gn.test status=201 |
| 4 | Multi-clinic | Clinic admin login | FAIL | clinic_id=None |
| 4 | Multi-clinic | Create receptionist | PASS | recv.field.27eb61@sante-gn.test |
| 4 | Multi-clinic | Receptionist creates patient | PASS | patient=225 |
| 4 | Multi-clinic | Koloma cannot see new clinic patient | PASS | leaked=False |
| 1 | Screenshots | UI role dashboards captured | PASS | docs\ui_e2e_screenshots\koloma-prod-20260620-1152-b7b8c8 |