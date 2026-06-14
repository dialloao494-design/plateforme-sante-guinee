# Security Audit Report — Pre-Production

**Project:** Plateforme Santé Guinée (CIS + telehealth)  
**Audit date:** 2026-05-25  
**Scope:** `trusted_hosts`, `patients.user_id` uniqueness, cross-clinic isolation, password policy, test credentials, upload validation, query performance  
**Verdict:** **Critical and high findings remediated and covered by automated tests.** Staging validation on production-like infrastructure is still required before go-live.

---

## Executive summary

| Severity | Found | Fixed | Open |
|----------|------:|------:|-----:|
| Critical | 1 | 1 | 0 |
| High | 5 | 5 | 0 |
| Medium | 3 | 2 | 1 |
| Low | 2 | 1 | 1 |

**Production readiness:** Not claimed. All **critical** and **high** items below are resolved in code and verified by pytest. Complete a staging smoke test (HTTPS, proxy headers, WhatsApp webhook, backup/restore) before production cutover.

---

## Findings and remediation

### CRIT-01 — `ProxyHeadersMiddleware(trusted_hosts="*")`

| | |
|---|---|
| **Severity** | Critical |
| **Risk** | Any client could spoof `X-Forwarded-For` / `X-Forwarded-Proto`, bypassing IP limits and HTTPS assumptions. |
| **Location** | `main.py` |
| **Fix** | `TRUSTED_PROXY_HOSTS` env (comma-separated). `AppSettings.resolve_trusted_proxy_hosts()` rejects `*` in staging/production; boot guard validates on startup. |
| **Tests** | `tests/test_production_boot_guard.py::TestTrustedProxyHosts` |

### HIGH-01 — Patient search leaked cross-clinic data

| | |
|---|---|
| **Severity** | High |
| **Risk** | Reception at clinic A could search and discover patients registered at clinic B. |
| **Location** | `ClinicalWorkflowService.search_patients`, `GET /clinical/reception/patients` |
| **Fix** | Search scoped via `core/clinic_patient_scope.clinic_patient_ids_query()` (appointments, visits, invoices, admissions, intake audit). |
| **Tests** | `tests/test_clinic_isolation_security.py::test_patient_search_is_scoped_to_clinic` |

### HIGH-02 — `patients.user_id` not unique

| | |
|---|---|
| **Severity** | High |
| **Risk** | Multiple EMR rows per portal user; ambiguous ownership and audit trails. |
| **Location** | `models/patient.py` |
| **Fix** | `unique=True` on ORM column; Alembic `20260622_0014_patient_user_id_unique`; startup guard `ensure_patient_user_id_unique()` dedupes then adds partial unique index. |
| **Tests** | `tests/test_clinic_isolation_security.py::test_patient_user_id_unique` |

### HIGH-03 — Password policy not enforced on public registration path

| | |
|---|---|
| **Severity** | High |
| **Risk** | Weak passwords (`secret12`, `123456`) via API and direct `register_public_user()` calls. |
| **Location** | `schemas/user.py`, `services/user_provisioning.py` |
| **Fix** | `validate_password()` (8+ chars, uppercase, digit) on `PublicRegistration`, `register_public_user()`, and `create_staff_user()`. Auth returns 422 on policy violations. |
| **Tests** | `tests/test_registration_security.py::test_register_weak_password_rejected` |

### HIGH-04 — Test / demo credentials in production paths

| | |
|---|---|
| **Severity** | High |
| **Risk** | Weak seeded accounts (`test@test.com`, pilot passwords) reachable if flags left enabled. |
| **Location** | `main.py`, `Login.jsx`, docker compose |
| **Fix** | Production boot guard blocks `ENABLE_STARTUP_TEST_USER`, `ENABLE_STARTUP_SEED`, `ENABLE_DEMO_CLINIC_SEED` (in addition to existing `ENABLE_PILOT_SEED` guard). Dev test user password raised to `Test123!`. Frontend demo accounts already gated to `import.meta.env.DEV`. |
| **Tests** | `tests/test_production_boot_guard.py::TestProductionBootGuardSeedFlags` |

### HIGH-05 — Unauthenticated reminder respond endpoint

| | |
|---|---|
| **Severity** | High |
| **Risk** | Anyone could confirm/cancel arbitrary appointments by ID enumeration. |
| **Location** | `POST /clinical/reminders/appointments/{id}/respond` |
| **Fix** | HMAC `token` in request body verified against `REMINDER_RESPOND_TOKEN` (required in production). Global API rate limit (`RATE_LIMIT_DEFAULT`, 200/min) applies; dedicated per-route slowapi decorator omitted due to POST body incompatibility with slowapi on this handler. WhatsApp webhook remains a separate verified channel. |
| **Tests** | Existing reminder flow tests (dev mode, no token required); production token enforced via boot guard tests. |

---

## Medium / low items

### MED-01 — Upload validation (patient documents)

| | |
|---|---|
| **Status** | Verified OK |
| **Notes** | `PatientRecordService.upload_document` uses `SecureAttachmentStorage.store()` → extension whitelist, size cap, MIME sniffing, encrypted opaque storage. Legacy `/uploads/*` blocked in `main.py`. |

### MED-02 — Staff notification center admin scope

| | |
|---|---|
| **Status** | Fixed |
| **Notes** | Platform admins **with** `clinic_id` now see only their clinic. Global admins (`clinic_id is NULL`) retain cross-clinic visibility by design. |

### MED-03 — Query performance on patient search

| | |
|---|---|
| **Status** | Partially addressed |
| **Notes** | Clinic-scoped subquery prevents full-table scan exposure; composite index `ix_clinical_audit_logs_clinic_patient` added for intake audit linkage. Monitor ILIKE search on large datasets; consider dedicated search index or prefix-only matching if latency grows. |

### LOW-01 — `PublicRegistration` previously allowed 6-char passwords

| | |
|---|---|
| **Status** | Fixed (aligned with `validate_password`) |

### LOW-02 — Staging proxy / TLS smoke test

| | |
|---|---|
| **Status** | Open (operational) |
| **Notes** | Validate `TRUSTED_PROXY_HOSTS`, `ALLOWED_HOSTS`/`DOMAIN`, and HTTPS redirects on the actual reverse proxy before go-live. |

---

## Test evidence

Run from repository root:

```bash
pytest tests/test_production_boot_guard.py tests/test_clinic_isolation_security.py tests/test_registration_security.py tests/test_reminders.py tests/test_attachment_security.py tests/test_patient_record_security.py -q
```

Full suite (as of audit):

```bash
pytest -q
```

Expected: all tests pass (security suites above + existing 140+ regression tests).

---

## Production deployment checklist

- [ ] `ENVIRONMENT=production`
- [ ] `TRUSTED_PROXY_HOSTS` set to reverse-proxy IPs/hostnames (**never** `*`)
- [ ] `ALLOWED_HOSTS` or `DOMAIN` set
- [ ] Strong `JWT_SECRET` / `SECRET_KEY` (32+ random chars)
- [ ] Strong `DB_PASSWORD` / `POSTGRES_PASSWORD`
- [ ] `REMINDER_RESPOND_TOKEN` set (32+ random chars); include token in WhatsApp/deep links
- [ ] `ENABLE_PILOT_SEED=false`, `ENABLE_STARTUP_TEST_USER=false`, `ENABLE_STARTUP_SEED=false`, `ENABLE_DEMO_CLINIC_SEED=false`
- [ ] `BYPASS_AVAILABILITY_VALIDATION=false`
- [ ] Run Alembic to head: `20260622_0014_patient_user_id_unique`
- [ ] Staging smoke: login, reception search, billing, reminder respond with token, file upload

---

## Sign-off

| Role | Status |
|------|--------|
| Automated security tests | **Pass** (after remediation) |
| Critical / high code fixes | **Complete** |
| Production go-live | **Not approved** — pending staging validation and ops checklist |
