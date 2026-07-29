# Santé Guinée — Security Wave 1 Report

**Wave:** 1 — FastAPI / REST API / IDOR / Injection / Rate limiting / Validation  
**Status:** COMPLETE  
**Date:** 2026-07-29  

---

## 1. Implemented protections

| Area | Implementation |
|------|----------------|
| **Authorize helper** | `core/authorize.py` — two-layer role/permission + clinic/patient tenancy |
| **IDOR** | `assign_doctor_to_clinic` requires `assert_clinic_access`; clinic admins cannot move peer-clinic doctors; `/patients` delete/update clinic-scoped; appointment access denies unassigned clinic admins |
| **Request validation** | `extra="forbid"` on clinical request schemas (`schemas/clinical.py`) |
| **SQLi defense-in-depth** | `reject_suspicious_sql_input` on reception patient search |
| **XSS / output encoding** | `core/output_encoding.py`; invoice PDF descriptions escaped; email HTML links escaped |
| **Rate limiting** | `SlowAPIMiddleware` enabled (default 200/min); auth routes retain dedicated limits |
| **Security headers** | `SecurityHeadersMiddleware` — nosniff, frame deny, referrer, permissions-policy, CSP, HSTS on HTTPS |
| **Error handling** | 403 responses use generic `"Permission denied"` (no role-list leakage) |
| **API permissions** | `assert_permission` on audit-logs, billing pending/pay, backup-status; RBAC matrix adds nurse/pev/patient + BILLING_READ for admins |

---

## 2. Validation evidence

| Suite | Result | Artifact |
|-------|--------|----------|
| Wave 1 API security tests | **9 passed** (plus isolation) | `evidence/security/WAVE1_PYTEST_API.txt` |
| Full backend pytest | **211 passed** | `evidence/security/WAVE1_PYTEST_FULL.txt` |
| Live smoke | `scripts/deploy/validate_security_wave1.py` | against staging/API |

---

## 3. Remaining risks (later waves)

| Risk | Notes |
|------|-------|
| Not every router uses `authorize()` yet | Clinical modular paths largely scoped; migrate remaining legacy routers gradually |
| Global rate limit only (no per-account) | Auth has per-IP; per-user limits later |
| Public doctor directory still open | Product decision |
| CSP is API-oriented | Frontend host needs its own CSP on Vercel |
| SlowAPI per-route on clinical modules | Avoided due to FastAPI/`from __future__` annotation conflict with limiter wrappers |

---

## 4. Verdict

**Security Wave 1 is COMPLETE.** All automated validations pass.
