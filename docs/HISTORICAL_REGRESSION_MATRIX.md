# Historical clinic bug regression matrix

Every production/clinic defect already encountered must remain covered by an automated gate.
Status: **LOCKED** = CI gate present; **PARTIAL** = unit only / incomplete E2E; **GAP** = missing (must be zero for GO).

| ID | Historical finding | Automated gate | Status |
|---|---|---|---|
| H01 | Duplicate registration 409 opaque Axios error | `registrationConflict.test.mjs`, e2e `reception-registration`, `test_reception_his_duplicate_registration.py` | LOCKED |
| H02 | Registration missing dossier number (online) | `test_reception_patient_number_generation.py`, `registrationSuccess.test.mjs` | LOCKED |
| H03 | Registration offline treated as failure / online-only bypass | `offline-pure.test.mjs`, `reconcilePatient.test.mjs`, e2e `reception-offline-registration` | LOCKED |
| H04 | Offline temp patient id breaks dependent mutations | `remapPatientRefs.test.mjs` (PR #40) | LOCKED (after #40) |
| H05 | Urgences specialty flip on “Créer la facture” | `test_reception_emergency_specialty_invoice.py`, `buildInvoiceItemPayload.test.mjs` | LOCKED |
| H06 | Emergency tariff without department context | `test_reception_emergency_specialty_invoice.py` | LOCKED |
| H07 | Receptionist 100% exemption | `test_billing_integrity_hardening.py`, `test_pr31_adversarial_audit.py` | LOCKED |
| H08 | Invoice idempotency (`X-Client-Request-Id`) | `test_billing_integrity_hardening.py`, `test_reception_register_idempotency.py` | LOCKED |
| H09 | Safari ITP / missing JSON bearer tokens | `test_auth_spa_cross_origin_tokens.py` | LOCKED |
| H10 | Cookie SameSite cross-origin | `test_pr31_adversarial_audit.py` | LOCKED |
| H11 | Outbox owner scoping / logout PHI purge | `test_pr31_adversarial_audit.py`, offline outbox tests | LOCKED |
| H12 | Unicode PDF / Helvetica | `test_simple_pdf_unicode.py` | LOCKED |
| H13 | Cross-clinic patient search / tenant isolation | `test_clinic_isolation_security.py`, `test_patient_record_security.py` | LOCKED |
| H14 | Nurse foreign consultation overwrite | `test_redteam_round2_clinical_idor.py` | LOCKED |
| H15 | Lab/pharmacy default doctor cross-tenant | `test_redteam_final_assessment.py` | LOCKED |
| H16 | session_version column missing | `test_session_version_migration.py` | LOCKED |
| H17 | must_change_password / login lockout | `test_security_wave6_pentest.py`, `test_auth_spa_cross_origin_tokens.py` | LOCKED |
| H18 | Payment access / settlement | `test_payment_access_enforcement.py`, `test_payment_settlement_security.py` | LOCKED |
| H19 | Visit workflow auth | `test_visit_workflow_auth.py` | LOCKED |
| H20 | Nutrition / immunization auth | `test_nutrition_immunization_auth.py` | LOCKED |
| H21 | Hospitalization auth path | `test_hospitalization.py` | LOCKED |
| H22 | Doctor appointment RBAC | `test_doctor_appointment_rbac.py` | LOCKED |
| H23 | Attachment security | `test_attachment_security.py` | LOCKED |
| H24 | WhatsApp webhook unsigned reject | `test_redteam_final_assessment.py` | LOCKED |
| H25 | Service request billing integrity | `test_reception_service_request_billing.py` | LOCKED |
| H26 | Invoice serial allocation | `test_invoice_serial_allocation.py` | LOCKED |
| H27 | Unified billing | `test_unified_billing.py` | LOCKED |
| H28 | Print auth errors actionable | e2e login + downloadPdf paths (PR #35) | PARTIAL |
| H29 | Dual `/appointments` vs `/rendezvous` | `test_appointments_rendezvous_parity.py` — `/appointments` canonical; `/rendezvous` legacy alias with shared `effective_role` RBAC | LOCKED |
| H30 | Mobile Money webhook signatures | `test_mobile_money_webhook_security.py` — HMAC fail-closed in production/`*_LIVE` | LOCKED |
| H31 | WebSocket token-in-query | `test_ws_auth_security.py` — cookie / first-message auth; query token rejected | LOCKED |
| H32 | HttpOnly-only auth (same-origin) | `test_auth_same_origin_cookies.py` + Vite prod default `VITE_API_URL=/api` + Vercel `/api` rewrite; JWT not persisted when same-origin | LOCKED |

## CI job

`clinic-regression-gates` in `.github/workflows/ci.yml` runs the Python subset below.
Frontend unit/offline gates run in `frontend-build`.
Playwright role/offline matrices run in `e2e-tests`.
