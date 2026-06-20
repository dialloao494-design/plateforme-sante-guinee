# Multi-Clinic Readiness Report

**Date:** 2026-05-25  
**Status:** Ready for controlled onboarding

## Current capability

| Step | API / UI | Time estimate | Status |
|------|----------|---------------|--------|
| Create clinic | `POST /clinical/clinics` (platform_admin) | 1 min | ✅ Tested |
| Create clinic admin | `POST /clinical/staff` | 2 min | ✅ Tested |
| Create receptionist + roles | `POST /clinical/staff` | 5 min | ✅ Tested |
| Patient registration | Reception dashboard | Immediate | ✅ |
| Role dashboards | Auto via nav config | Immediate | ✅ |
| Clinic data isolation | Tenant middleware | Automatic | ✅ Verified |

## Provisioning script

`scripts/deploy/koloma_clinic_onboarding.py` — full Koloma staff provisioning template.

Field readiness suite (`koloma_field_readiness_suite.py`) Phase 4 validates:
- New clinic creation on production
- Clinic admin + receptionist creation
- Patient registration in new clinic
- Cross-clinic isolation (Koloma cannot see new clinic patients)

## Clinic creation wizard (UI)

**Current:** Platform admin uses `/platform/clinics` + staff creation in admin UI.  
**Gap:** No single guided wizard — operational workaround is onboarding script.

## Recommended onboarding checklist (new clinic)

1. Platform admin creates clinic (`name`, `city`, `phone`).
2. Create `clinic_admin` account with temporary password.
3. Clinic admin creates staff by role (receptionist first, then clinical roles).
4. Receptionist registers first test patient.
5. Run `koloma_field_readiness_suite.py` scoped checks or manual smoke test.
6. Distribute credentials securely (not via chat).

## Isolation guarantees

- Patients scoped by `clinic_id` on all clinical APIs.
- Staff RBAC enforced per role.
- Clinic admin cannot access other clinic staff lists (403).
- Search results filtered to actor's clinic.

## Scale limits (current architecture)

- Single PostgreSQL database, row-level clinic isolation.
- Suitable for **10–50 clinics** without architectural change.
- Beyond 50: consider read replicas and report materialized views.

## Readiness verdict

**READY** for onboarding additional clinics via platform admin + onboarding script.  
**NOT READY** for self-service clinic signup without platform admin involvement.
