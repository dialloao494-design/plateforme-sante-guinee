# Santé Guinée — Stabilization findings matrix

Living inventory of historical audit / clinic findings and current remediation status.
Updated as part of the clinic stabilization & offline-capability mission.

Status key:

- **VERIFIED FIXED** — code + tests + production topology aligned
- **PARTIALLY FIXED** — core path fixed; residual risk or incomplete coverage remains
- **STILL BROKEN** — not addressed or actively incorrect
- **REGRESSED** — previously fixed, broken again

## Auth / session

| Finding | Status | Notes |
|---|---|---|
| Safari ITP / JSON bearer tokens | VERIFIED FIXED | PR #35; prod smoke |
| Cookie SameSite cross-origin | VERIFIED FIXED | PR #31 |
| Refresh / jti denylist | VERIFIED FIXED | Wave0/security merge |
| must_change_password gate | VERIFIED FIXED | Wave6 |
| Login lockout | VERIFIED FIXED | Wave6 |
| Public register role=admin | VERIFIED FIXED | provisioning hooks |
| JWT still in sessionStorage (XSS residual) | PARTIALLY FIXED | Cookie+Bearer hybrid; HttpOnly-only migration open |
| WebSocket token in query | STILL BROKEN | Residual |
| MFA optional for privileged | PARTIALLY FIXED | Soft-gate residual |

## Reception / clinic bugs

| Finding | Status | Notes |
|---|---|---|
| Duplicate 409 opaque Axios error | VERIFIED FIXED | PR #33/#34 |
| Registration missing dossier number (online) | VERIFIED FIXED | flush+commit; keep form |
| Registration offline queued as failure / online-only bypass | VERIFIED FIXED (this branch) | Queued + reconcile dossier; **not** online-only |
| Urgences specialty flip on invoice | VERIFIED FIXED | PR #36 |
| Emergency tariff without department context | VERIFIED FIXED | PR #37 |
| Stale Autre specialty on dept change | VERIFIED FIXED | PR #37 |

## Billing / payments

| Finding | Status | Notes |
|---|---|---|
| Receptionist 100% exemption | VERIFIED FIXED | PR #31 |
| Invoice X-Client-Request-Id idempotency | VERIFIED FIXED | PR #31 |
| Catalog-authoritative prices | VERIFIED FIXED | billing integrity suite |
| DSR double-bill / cancelled | VERIFIED FIXED | billing integrity suite |
| Patient register idempotency | VERIFIED FIXED (this branch) | `test_reception_register_idempotency.py` |
| Mobile Money webhook signatures | STILL BROKEN | Residual until MM live |
| Appointment confirm without payment | PARTIALLY FIXED | Policy present; dual API debt |

## Tenant / authz

| Finding | Status | Notes |
|---|---|---|
| Cross-clinic patient search | VERIFIED FIXED | clinic scope |
| Nurse foreign consultation overwrite | VERIFIED FIXED | Red Team |
| Lab/pharmacy default doctor cross-tenant | VERIFIED FIXED | Red Team |
| Patient user_id relink by clinic admin | VERIFIED FIXED | Red Team |
| Open PR #26 patient ownership hardening | PARTIALLY FIXED | Branch exists; not on main |

## Offline / PHI

| Finding | Status | Notes |
|---|---|---|
| Outbox owner scoping | VERIFIED FIXED | PR #31 |
| Logout purge IndexedDB | VERIFIED FIXED | PR #31 |
| countPendingOutbox global (cross-user) | VERIFIED FIXED (this branch) | Owner-filtered |
| Conflict rows missing owner_key | VERIFIED FIXED (this branch) | Scoped |
| Offline registration + dossier reconcile | VERIFIED FIXED (this branch) | `reconcilePatient.js` |
| Dependent mutation rewrite (admission on temp id) | PARTIALLY FIXED | Register reconcile done; dependents backlog |
| Full multi-device concurrent offline E2E | PARTIALLY FIXED | Unit/integration; browser network-loss matrix in progress |
| Clinic Node appliance vs SPA dual stack | PARTIALLY FIXED | Documented; keep separate |

## Schema / ops

| Finding | Status | Notes |
|---|---|---|
| session_version column missing | VERIFIED FIXED | Alembic 0025 |
| Triple schema authority (create_all + runtime) | PARTIALLY FIXED | Alembic preferred; runtime helpers residual |
| patient_number nullable at DB | PARTIALLY FIXED | HIS path assigns; DB NOT NULL deferred (legacy rows) |
| Git history secrets | PARTIALLY FIXED | Rotation ops residual |
| Dual `/appointments` vs `/rendezvous` | STILL BROKEN | Architecture debt |

## Printing / PDF

| Finding | Status | Notes |
|---|---|---|
| Invoice receipt PDF urgences label | VERIFIED FIXED | Prod proof INV-2026-017-00137 |
| Unicode PDF Helvetica | VERIFIED FIXED | Hardening PR |
| Print auth errors actionable | VERIFIED FIXED | PR #35 |

---

## Permanent regression gates (CI)

| Gate | Location |
|---|---|
| Duplicate 409 UX | `registrationConflict.test.mjs`, e2e reception-registration |
| Patient number generation | `test_reception_patient_number_generation.py` |
| Emergency specialty / dept validation | `test_reception_emergency_specialty_invoice.py` |
| Register idempotency | `test_reception_register_idempotency.py` |
| Offline classify + optimistic patient | `offline-pure.test.mjs` |
| Dossier reconcile helpers | `reconcilePatient.test.mjs` |
| PR #31 adversarial | `test_pr31_adversarial_audit.py` |
| Billing integrity | `test_billing_integrity_hardening.py` |
| Safari auth tokens | `test_auth_spa_cross_origin_tokens.py` |
