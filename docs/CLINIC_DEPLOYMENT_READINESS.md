# Clinic-day readiness report

**Date:** 2026-06-18  
**Backend:** https://web-production-ad6a36.up.railway.app  
**Frontend:** https://plateforme-sante-guinee.vercel.app  

**Latest audit:** **57 PASS · 0 FAIL · 0 BLOCKER**  
**Email verification:** **PASS** (Resend — signup + forgot-password delivered to inbox)  
**Security tests:** 33 PASS (local)

---

## Executive verdict

**Ready for clinic deployment.** Transactional email is live via Resend. All automated production checks pass.

---

## Railway email configuration (production)

| Variable | Value |
|----------|--------|
| `RESEND_API_KEY` | Set on Railway (not in repo) |
| `SENDER_EMAIL` | `onboarding@resend.dev` |
| `FRONTEND_URL` | `https://plateforme-sante-guinee.vercel.app` |

Verify: `GET /health/email` → `"configured": true, "provider": "resend"`

Re-run email tests:

```bash
RESEND_API_KEY=re_... python scripts/deploy/verify_email_production.py --inbox your@gmail.com
```

---

## Remaining blockers

**None** for single-clinic pilot.

---

## Known non-blocking items

| Item | Notes |
|------|--------|
| Resend sender `onboarding@resend.dev` | Testing sender; verify custom domain before multi-clinic scale |
| New clinic creation | Requires `platform_owner` |
| JWT in localStorage | Architectural risk; not clinic-day blocker |

---

## Demo accounts

| Role | Email | Password |
|------|--------|----------|
| Clinic admin | `clinic.admin.a@sante-gn.test` | `ClinicAdminA1!` |
| Reception A | `reception.demo@sante-gn.test` | `ReceptionDemo1!` |
| Doctor | `doctor.demo@sante-gn.test` | `DoctorDemo1!` |

---

## Recommended workflow for clinic day

1. **Morning:** clinic admin confirms staff accounts; staff change passwords on first login.
2. **Patient flow:** Reception → Nutrition → PEV → Doctor → Lab/Pharmacy as needed.
3. **Forgot password:** users can use forgot-password; emails deliver via Resend.
4. **End of day:** `python scripts/deploy/full_production_audit.py` (expect 57 PASS).
