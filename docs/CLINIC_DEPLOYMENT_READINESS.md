# Clinic deployment readiness — final audit report

**Date:** 2026-06-18  
**Backend:** https://web-production-ad6a36.up.railway.app  
**Frontend:** https://frontend-seven-rust-94.vercel.app  

**Automated audit:** `python scripts/deploy/full_production_audit.py`  
**Latest result:** **56 PASS · 0 FAIL · 0 WARN · 1 BLOCKER**  
**Security regression:** **33 unit tests PASS** (auth, isolation, workflow, nutrition/PEV, password reset)

Full machine-readable output: `docs/PRODUCTION_AUDIT_REPORT.md` and `docs/PRODUCTION_AUDIT_REPORT.json`

---

## Executive verdict

The platform is **ready for a single-clinic pilot tomorrow** using pre-provisioned demo accounts and in-app password changes. **Transactional email (password reset + verification) is the only deployment blocker** for self-service account recovery. All other audited clinical workflows pass in production.

---

## 1. Working features (verified in production)

### Infrastructure
- `GET /health` → 200 (`debug: false`)
- `GET /health/ready` → database OK
- Frontend SPA routes: `/`, `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/verify-email`
- Clinical dashboards: `/clinical/reception`, `/nutrition`, `/immunization`, `/doctor`, `/lab`, `/pharmacy`, `/midwife`

### Authentication & accounts
- Register (patient/doctor) with token + immediate login
- Login / logout / change password
- Forgot password endpoint (200) + invalid reset token rejected (400)
- Email verification API + `/verify-email` frontend route (delivery pending SMTP)
- Weak password and duplicate email rejection
- Rate limiting: login 30/min, register 5/min, forgot-password 10/hour (production defaults)

### Roles & dashboards
- Login verified: `clinic_admin`, `reception` (clinic A & B), `doctor`
- Reception queue + workflow queue
- Doctor queue + workflow queue
- Clinic admin operations summary + staff list
- Nutrition patient history + PEV schedule
- Lab/pharmacy orders correctly denied for reception (403)

### Security (production + unit tests)
- RBAC: reception denied doctor queue and admin backup (403)
- Multi-clinic isolation: clinic B cannot see clinic A patients
- Password reset: hashed tokens, expiry, single-use
- Public registration role guard (no admin escalation)
- Privileged role ORM guard

### Production smoke journey (automated)
- Staff created and logged in: receptionist, nutritionist, midwife, doctor, lab_technician, pharmacist
- Patient intake + child workflow: Reception → Nutrition → PEV → Doctor
- Nutrition assessment (201), PEV record (201), midwife queues (200)
- Laboratory queue (200), pharmacy queue (200)
- Full workflow artifact: patient_id 23, workflow_id 4, stages verified

---

## 2. Blocking issue for clinic deployment tomorrow

### SMTP / Resend not configured on Railway

**Impact:** Password reset and email verification links are generated server-side but **not delivered to inboxes**. Users cannot self-recover via forgot-password until this is fixed.

**Required Railway variables** (backend service → Variables):

| Variable | Example |
|----------|---------|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | sender account |
| `SMTP_PASSWORD` | app password |
| `SENDER_EMAIL` | verified sender |
| `FRONTEND_URL` | `https://frontend-seven-rust-94.vercel.app` |

**Alternative:** `RESEND_API_KEY` + verified `SENDER_EMAIL`.

**Verify after setting:**
```bash
curl https://web-production-ad6a36.up.railway.app/health/email
# → "configured": true
```

**Inbox E2E test (manual, after SMTP):**
1. POST `/auth/forgot-password` with a real inbox email
2. Register a new account — check inbox for `/verify-email?token=...`
3. Re-run: `python scripts/deploy/full_production_audit.py`

Full guide: [RAILWAY_SMTP.md](./RAILWAY_SMTP.md)

**Workaround for clinic day:**
- Use demo accounts below
- Change password from profile for existing users
- Clinic admin resets staff passwords via admin panel

---

## 3. Remaining non-blocking items

| Item | Severity | Notes |
|------|----------|--------|
| SMTP not configured | **Blocker** | See §2 — requires Railway credentials (not in repo) |
| New clinic creation | By design | `POST /clinical/clinics` requires `platform_owner`; use `scripts/deploy/provision_platform_owner.py` for multi-clinic onboarding |
| Inbox E2E email test | Pending | Blocked on SMTP configuration |
| `REQUIRE_EMAIL_VERIFICATION` | Optional | Off by default; enable only after SMTP is stable |
| JWT in localStorage | Medium | Documented architectural risk; mitigated by CSP/XSS hygiene; not a clinic-day blocker |
| Rate limit in-memory | Medium | Single Railway worker OK for pilot; Redis needed for multi-instance scale |

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

1. **Configure SMTP/Resend** on Railway and complete inbox E2E test.
2. **Provision platform owner** for new clinic creation (`POST /clinical/clinics`).
3. **Run audit after SMTP:** `python scripts/deploy/full_production_audit.py` → expect 57 PASS, 0 BLOCKER.
4. **Optional:** Set `REQUIRE_EMAIL_VERIFICATION=true` after SMTP is stable.
5. **Train staff** on password rule: 8+ chars, 1 uppercase, 1 digit.
6. **Document clinic-specific admin** for staff provisioning and password resets.

---

## 6. Security audit summary

| Area | Status |
|------|--------|
| Public registration role guard | PASS |
| Privileged role ORM guard | PASS |
| Login rate limit (30/min prod) | Configured |
| Forgot-password rate limit (10/hour) | Configured |
| Password reset token hashing + expiry | PASS |
| Multi-clinic isolation | PASS (production + unit tests) |
| Password policy (8+, upper, digit) | Enforced |
| RBAC on clinical endpoints | PASS (production audit) |

Historical critical/high items from earlier code reviews (admin registration, payment bypass, public uploads) were remediated in prior commits. No new critical/high issues found in this audit pass.

---

## 7. Commits in this audit cycle

| Commit | Description |
|--------|-------------|
| `cd0cca4` | SMTP delivery, email verification, audit tooling |
| `78d83dd` | Railway Alembic startup + email schema ensure |
| `585b7c9` | Low-bandwidth optimizations |
| `b38e560` | Production audit report + clinic deployment readiness |

Uncommitted local improvements: extended audit script (lab/pharmacy/midwife queues + clinical frontend routes) — see `scripts/deploy/full_production_audit.py`.
