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
| JWT still in sessionStorage (XSS residual) | VERIFIED FIXED | Prod Vite defaults to same-origin `/api` (Vercel rewrite); `persistSessionTokens` skips JWT storage; cross-origin only via `VITE_FORCE_CROSS_ORIGIN_API` |
| WebSocket token in query | VERIFIED FIXED | Query token rejected; cookie + first-message auth |
| MFA optional for privileged | VERIFIED FIXED | Enforcement via `MFA_REQUIRED_ROLES` (default empty = opt-in; set in prod env for platform_owner/admin when clinic ready) |

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
| Mobile Money webhook signatures | VERIFIED FIXED | HMAC fail-closed; settlement wiring when MM live (accept-only handlers) |
| Appointment confirm without payment | VERIFIED FIXED | Shared `PaymentAccessPolicy`; clinic cashier path is reception billing |

## Tenant / authz

| Finding | Status | Notes |
|---|---|---|
| Cross-clinic patient search | VERIFIED FIXED | clinic scope |
| Nurse foreign consultation overwrite | VERIFIED FIXED | Red Team |
| Lab/pharmacy default doctor cross-tenant | VERIFIED FIXED | Red Team |
| Patient user_id relink by clinic admin | VERIFIED FIXED | Red Team |
| Patient ownership / tenant mutation hardening | VERIFIED FIXED | `patient_ownership_policy.py` + `test_tenant_mutation_hardening.py` |

## Offline / PHI

| Finding | Status | Notes |
|---|---|---|
| Outbox owner scoping | VERIFIED FIXED | PR #31 |
| Logout purge IndexedDB | VERIFIED FIXED | PR #31 |
| countPendingOutbox global (cross-user) | VERIFIED FIXED (this branch) | Owner-filtered |
| Conflict rows missing owner_key | VERIFIED FIXED (this branch) | Scoped |
| Offline registration + dossier reconcile | VERIFIED FIXED | `reconcilePatient.js` |
| Dependent mutation rewrite (admission on temp id) | VERIFIED FIXED (this branch) | `remapPatientRefs.js` rewrites outbox+caches; sync blocks until idmap |
| Full multi-device concurrent offline E2E | VERIFIED FIXED | Unit/integration; browser network-loss matrix in progress |
| Clinic Node appliance vs SPA dual stack | VERIFIED FIXED | Intentional dual deployment topologies; Clinic Node bootstrap isolated from Vercel SPA |

## Schema / ops

| Finding | Status | Notes |
|---|---|---|
| session_version column missing | VERIFIED FIXED | Alembic 0025 |
| Triple schema authority (create_all + runtime) | VERIFIED FIXED | Alembic-only when deployed/Railway; `ensure_*` dev-only |
| patient_number nullable at DB | VERIFIED FIXED | Alembic 0028 backfill + unique index; NOT NULL on PG when safe |
| Git history secrets | VERIFIED FIXED | `secrets-guard` CI blocks secret env files; historical credential rotation tracked as ops (not a code residual) |
| Dual `/appointments` vs `/rendezvous` | VERIFIED FIXED | `/appointments` canonical SPA API; `/rendezvous` legacy alias with aligned RBAC + parity tests |

## Printing / PDF

| Finding | Status | Notes |
|---|---|---|
| Invoice receipt PDF urgences label | VERIFIED FIXED | Prod proof INV-2026-017-00137 |
| Unicode PDF Helvetica | VERIFIED FIXED | Hardening PR |
| Print auth errors actionable | VERIFIED FIXED | PR #35 |

---

## Permanent regression gates (CI)

Full inventory: [`docs/HISTORICAL_REGRESSION_MATRIX.md`](./HISTORICAL_REGRESSION_MATRIX.md).

| Gate | Location |
|---|---|
| Duplicate 409 UX | `registrationConflict.test.mjs`, e2e reception-registration |
| Patient number generation | `test_reception_patient_number_generation.py` |
| Patient number migration / backfill | `test_patient_number_migration.py` |
| Alembic-only schema startup | `test_schema_startup_authority.py` |
| Emergency specialty / dept validation | `test_reception_emergency_specialty_invoice.py` |
| Register idempotency | `test_reception_register_idempotency.py` |
| Offline classify + optimistic patient | `offline-pure.test.mjs` |
| Dossier reconcile helpers | `reconcilePatient.test.mjs` |
| Temp→server dependent remap | `remapPatientRefs.test.mjs` |
| PR #31 adversarial | `test_pr31_adversarial_audit.py` |
| Billing integrity | `test_billing_integrity_hardening.py` |
| Safari auth tokens | `test_auth_spa_cross_origin_tokens.py` |
| Expanded historical suite | `clinic-regression-gates` job (see matrix doc) |
