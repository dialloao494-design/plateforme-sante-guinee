# Clinic deployment readiness — final audit summary

**Date:** 2026-06-18  
**Backend:** https://web-production-ad6a36.up.railway.app  
**Frontend:** https://frontend-seven-rust-94.vercel.app  

Automated audit: `python scripts/deploy/full_production_audit.py`  
Latest result: **44 PASS · 0 FAIL · 1 BLOCKER** (see `PRODUCTION_AUDIT_REPORT.md`)

---

## 1. Working features (verified in production)

### Authentication & accounts
- Register (patient/doctor) with token + immediate login
- Login / logout / change password
- Forgot password + reset password (token validation)
- Email verification API + `/verify-email` frontend route
- Weak password and duplicate email rejection
- Rate limiting on login, register, forgot-password

### Clinical CIS
- Reception queue, patient intake, workflow queues
- Child path: Reception → Nutrition → PEV → Doctor (automated smoke PASS)
- Staff creation (reception, nutrition, midwife, doctor, lab, pharmacist)
- Nutrition assessments
- PEV schedule API
- Doctor / reception dashboards
- Multi-clinic patient isolation (clinic B cannot see clinic A patients)

### Infrastructure
- `/health`, `/health/ready`, frontend SPA routes
- Alembic + startup schema ensure on Railway (post hotfix `78d83dd`)
- Low-bandwidth optimizations (cached GETs, lazy routes, asset caching)

### Security (sample)
- RBAC: reception denied doctor queue and admin backup
- Lab/pharmacy queues denied for reception role
- JWT role integrity (covered by unit tests)

---

## 2. Blocking issue for tomorrow's clinic

### SMTP / transactional email not configured on Railway

**Impact:** Password reset and verification emails are **not delivered to inboxes** — links are only logged server-side.

**Fix (required before real doctors use forgot-password):** Set on Railway backend service:

| Variable | Value |
|----------|--------|
| `SMTP_HOST` | e.g. `smtp.gmail.com` or your provider |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | sender account |
| `SMTP_PASSWORD` | app password |
| `SENDER_EMAIL` | verified sender address |
| `FRONTEND_URL` | `https://frontend-seven-rust-94.vercel.app` |

Alternative: `RESEND_API_KEY` + verified `SENDER_EMAIL`.

Verify: `GET /health/email` → `"configured": true`

Full guide: [RAILWAY_SMTP.md](./RAILWAY_SMTP.md)

**Workaround for clinic day:** Use demo accounts below; use change-password from profile for existing users; clinic admin resets staff passwords via admin panel.

---

## 3. Remaining non-blocking items

| Item | Severity | Notes |
|------|----------|--------|
| SMTP not configured | **Blocker** | See above |
| PEV record in audit script | Low | Fixed in audit script; API works when `vaccine_name` provided |
| New clinic creation | By design | Only `platform_owner` can `POST /clinical/clinics`; use platform owner for onboarding new clinics |
| Lab/pharmacy smoke in audit | Info | Not in default journey; APIs exist, RBAC verified |
| `REQUIRE_EMAIL_VERIFICATION` | Optional | Env flag to block login until verified; **off** by default so clinic accounts work immediately |

---

## 4. Production test accounts

| Role | Email | Password |
|------|--------|----------|
| Clinic admin | `clinic.admin.a@sante-gn.test` | `ClinicAdminA1!` |
| Reception (clinic A) | `reception.demo@sante-gn.test` | `ReceptionDemo1!` |
| Reception (clinic B) | `reception.beta@sante-gn.test` | `ReceptionBeta1!` |
| Doctor | `doctor.demo@sante-gn.test` | `DoctorDemo1!` |

---

## 5. Recommended before onboarding multiple clinics

1. **Configure SMTP/Resend** on Railway and run inbox test (forgot-password + signup verification).
2. **Provision platform owner** for new clinic creation (`POST /clinical/clinics`).
3. **Set `FRONTEND_URL`** on Railway to production Vercel URL (already set).
4. **Run audit after SMTP:** `python scripts/deploy/full_production_audit.py`
5. **Optional:** Enable `REQUIRE_EMAIL_VERIFICATION=true` after SMTP is stable.
6. **Train staff** on password rule: 8+ chars, 1 uppercase, 1 digit.

---

## 6. Commits deployed this audit cycle

- `cd0cca4` — SMTP delivery, email verification, audit tooling
- `78d83dd` — Railway Alembic startup + email schema ensure
- `585b7c9` — Low-bandwidth optimizations

---

## 7. Security audit summary

| Area | Status |
|------|--------|
| Public registration role guard | PASS (unit tests) |
| Privileged role ORM guard | PASS |
| Login rate limit (30/min prod) | Configured |
| Forgot-password rate limit (10/hour) | Configured |
| Password reset token hashing + expiry | PASS |
| Multi-clinic isolation | PASS (production + unit tests) |
| Password policy (8+, upper, digit) | Enforced |

No new critical/high code review issues were left unaddressed in this pass. Full regression: **33 unit tests PASS** locally (auth, isolation, workflow, nutrition/PEV).
