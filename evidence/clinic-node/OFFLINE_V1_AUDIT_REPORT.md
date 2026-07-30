# Offline V1 Audit Report — Clinic Node

**Product:** Santé Guinée — Offline Clinic Node (local appliance)  
**Scope:** Phases 0–5 as implemented on branch `cursor/clinic-node-phase0-ab76`  
**Audit date (UTC):** 2026-07-28  
**Evidence root:** `evidence/clinic-node/`  
**PR:** https://github.com/dialloao494-design/plateforme-sante-guinee/pull/13  

### Executive verdict

| Question | Answer |
|----------|--------|
| Can a pilot clinic run **standalone offline** clinical workflows on LAN? | **CONDITIONAL GO** |
| Is Offline V1 ready as a **full production** offline platform (sync, license, DR, cutover)? | **NO-GO** |
| Recommended pilot posture | Supervised LAN pilot, limited module set, manual ops runbook |

**Final recommendation:** **CONDITIONAL GO** for a single supervised pilot clinic that accepts the limitations and missing items listed below. Do **not** treat cloud sync, cryptographic licensing, automated DR, or migration cutover as production-ready.

---

## Scope clarification

This audit covers the **Clinic Node appliance** (`deploy/clinic-node/`): local PostgreSQL + FastAPI + SPA + HTTPS proxy on LAN.

It does **not** claim completion of `docs/OFFLINE_STRATEGY_ROADMAP.md` (PWA / IndexedDB / Service Worker offline). That roadmap remains **NOT READY** and is a different architecture.

Cloud production (`plateforme-sante-guinee.vercel.app` / Railway) was **not modified** by Clinic Node packaging.

---

## Rating legend

| Field | Meaning |
|-------|---------|
| **Implemented** | Code/config present and wired |
| **Tested** | Automated unit/integration or scripted smoke |
| **E2E validated** | Phase acceptance script + evidence artifact |
| **Production readiness** | Ready / Conditional / Not ready for pilot clinic use of *that feature* |
| **Remaining risks** | What can still fail in the field |

---

## Phase 0 — Appliance foundation

| Feature | Implemented | Tested | E2E validated | Remaining risks | Production readiness | Known limitations |
|---------|-------------|--------|---------------|-----------------|----------------------|-------------------|
| Compose stack (bridge `compose.yml`) | Yes | Settings/file tests | Partial (assets exist; agent used host) | Bridge/veth broken in some nested VMs | **Conditional** | Prefer bridge on real mini-PC; not proven in CI agent |
| Compose stack (host `compose.host.yml`) | Yes | File existence | **Yes** — `PHASE0_E2E_ACCEPTANCE.md` | Binds host ports (`5432`, `8000`, etc.) | **Conditional** | Fallback mode for constrained Docker hosts |
| One-command installer `install/install.sh` | Yes | Scripted in Phase 0 E2E | **Yes** | Requires Docker + openssl | **Ready** | Auto-selects bridge vs host |
| Secrets / `.env` bootstrap | Yes | Phase 0 install | **Yes** | Admin credentials file on disk | **Ready** | `data/ADMIN_CREDENTIALS.txt` (gitignored, mode 600) |
| Data dirs (postgres, uploads, logs, pki, backups) | Yes | Install creates | **Yes** | Bind-mount permissions | **Ready** | Under `deploy/clinic-node/data/` |
| Local PKI + HTTPS proxy | Yes | TLS cert info in evidence | **Yes** | Manual CA trust per workstation | **Conditional** | Self-signed; `trust-ca-help.sh` only |
| HTTP→HTTPS redirect | Yes | Indirect | Partial | Port remap in host mode | **Ready** | |
| systemd unit | Yes | Exists | **No** (reboot sim uses compose) | Hardcoded WorkingDirectory path | **Conditional** | Optional; must edit path on site |
| Restart policies / reboot-safe | Yes | `validate-reboot-safe.sh` | **Yes** (compose stop/start) | Not a hardware power-cycle + systemd E2E | **Conditional** | Probe row survival proven |
| `/health` + `/health/ready` | Yes | Indirect | **Yes** | — | **Ready** | |
| `ENVIRONMENT=clinic-node` isolation | Yes | `tests/test_clinic_node_settings.py` | **Yes** | Deploy discipline if shared images | **Ready** | Seeds/demo flags forced off |
| Isolation from Vercel/Railway packaging | Yes | Frontend URL tests | Documented | Merge mistakes | **Ready** | Packaging lives only under `deploy/clinic-node/` |
| Technician README | Yes | n/a | n/a | Still Phase-0-centric | **Conditional** | Missing Phase 1–5 ops runbook sections |

**Phase 0 evidence:** `evidence/clinic-node/PHASE0_E2E_ACCEPTANCE.md` · run `e2e-phase0/20260728T133741Z/`  
**Unit tests:** `tests/test_clinic_node_settings.py`

---

## Phase 1 — Local authentication & bootstrap

| Feature | Implemented | Tested | E2E validated | Remaining risks | Production readiness | Known limitations |
|---------|-------------|--------|---------------|-----------------|----------------------|-------------------|
| Bootstrap clinic + `clinic_admin` | Yes | `tests/test_clinic_node_bootstrap.py` | **Yes** | Misconfigured admin email/password env | **Ready** | Idempotent; does not reset existing password |
| `must_change_password` on bootstrap | Yes | Unit + migration helper | Partial | Phase 1 E2E disables flag for admin automation | **Conditional** | Staff reset path validated; admin first-login UI not browser-E2E’d |
| Platform setup wizard disabled | Yes | API behavior | **Yes** (`setup_required:false`) | Frontend route still exists | **Ready** | API returns deny on clinic-node |
| Staff create + role login | Yes | Via clinical API | **Yes** | Shared RBAC complexity | **Ready** | |
| Permission enforcement (setup denied) | Partial | Soft E2E assert | Partial | Soft pass possible in validator | **Conditional** | Not a full RBAC matrix |
| Admin staff password reset → must change | Yes | E2E script | **Yes** | — | **Ready** | Forces `must_change_password` |
| Frontend must-change gate | Yes | No UI test | **No** browser E2E | Users could miss UX if API ignored | **Conditional** | `Login.jsx` / `ProtectedRoute.jsx` |
| Forgot-password clinic-node messaging | Yes | No UI test | **No** | Staff may expect email reset | **Conditional** | Directs to admin reset on LAN |
| Pilot/demo seed disabled | Yes | Settings + compose | Env-level | — | **Ready** | |
| Optional multi-role bootstrap staff | Yes | Untested as default | **No** (default off) | Temp passwords if enabled carelessly | **Conditional** | Phase 2 creates staff via API instead |

**Phase 1 evidence:** `evidence/clinic-node/PHASE1_E2E_ACCEPTANCE.md` · `e2e-phase1/20260728T174249Z/`  
**Unit tests:** `tests/test_clinic_node_bootstrap.py`

---

## Phase 2 — LAN clinical modules (multi-role)

| Feature | Implemented | Tested | E2E validated | Remaining risks | Production readiness | Known limitations |
|---------|-------------|--------|---------------|-----------------|----------------------|-------------------|
| Multi-role local logins (reception, doctor, lab, pharmacy, cashier, nurse) | Yes | API smoke only | **Yes** | Not load/concurrency stress | **Conditional** | Sequential tokens ≠ true concurrent write load |
| Reception: create patient (HIS) | Yes | No clinic-node unit | **Yes** | Duplicate identity rules | **Ready** | API-only evidence |
| Reception: create admission | Yes | No | **Yes** | Outpatient-focused | **Ready** | |
| Doctor: open consultation | Yes | No | **Yes** | Chart fields often empty in smoke | **Conditional** | Depth of documentation not exercised |
| Lab: order + result + validate | Yes | No | **Yes** | Single CBC path | **Ready** | |
| Pharmacy: dispense | Yes | No | **Partial** | Validator targeted `orders[0]` from prior run | **Conditional** | Evidence dispensed `patient_id=1` while workflow patient was `2` |
| Cashier: payment | Yes | No | **Partial** | Same soft targeting issue | **Conditional** | Paid charge was prior patient `1` |
| Nurse: clinical workflow | Partial | No | **Partial** (`/auth/me` only) | Staff may expect nursing modules | **Not ready** | Login-only; no pointage/care E2E |
| HTTPS SPA reachable during multi-user use | Yes | Header curl | **Yes** | Not interactive browser session | **Conditional** | No Playwright multi-tab E2E |

**Phase 2 evidence:** `evidence/clinic-node/PHASE2_E2E_ACCEPTANCE.md` · `e2e-phase2/20260728T174521Z/`

### Explicitly NOT E2E-validated in Phase 2
- Hospitalization / inpatient
- Imaging / radiology
- Teleconsult (frontend build stubs provider)
- Pharmacy inventory / stock levels / oversell protection
- Nursing care / assessments / pointage
- PEV / immunization
- Nutrition
- Full invoice ledger beyond one cash payment
- Interactive SPA role dashboards
- True concurrent write contention
- Browser CA trust on real LAN workstations

---

## Phase 3 — License, sync deltas, conflicts, backups

| Feature | Implemented | Tested | E2E validated | Remaining risks | Production readiness | Known limitations |
|---------|-------------|--------|---------------|-----------------|----------------------|-------------------|
| Local license (“jeton”) issue + state | Partial | **No** unit tests | **Yes** (API smoke) | Anyone can keep using after expiry | **Not ready** | Self-issued JSON; **no crypto**; `EXPIRED` does **not** block clinical APIs |
| Sync outbox enqueue/list/ack | Partial | **No** | **Yes** (manual API) | False confidence that sync exists | **Not ready** | **Not hooked** into clinical writes; no cloud push worker; `last_sync_success_at` always null |
| Conflict record store/list | Partial | **No** | **Yes** (store/list) | Conflicts never auto-detected | **Not ready** | No resolve API; no UI; no merge policy engine |
| Local `pg_dump` backup (on demand) | Yes | **No** unit | **Yes** (~20 KB gzip) | Operator forgets to run | **Conditional** | Works with postgresql-client-16; falls back to marker if dump fails |
| Scheduled / automatic backups | **No** | — | **No** | Data loss on disk failure between manual dumps | **Not ready** | No cron/systemd timer in Clinic Node |
| Backup retention policy | **No** | — | **No** | Disk fill | **Not ready** | Unlimited accumulation under `data/backups/` |
| Backup **restore** drill for Clinic Node | **No** | — | **No** | Unrecoverable after hardware loss | **Not ready** | Generic VPS restore docs exist; not wired/E2E’d for appliance |

**Phase 3 evidence:** `evidence/clinic-node/PHASE3_E2E_ACCEPTANCE.md` · combined run `e2e-phase3-5/20260728T175050Z/`  
**Code:** `models/clinic_node_ops.py`, `services/clinic_node_ops_service.py`, `routers/clinic_node_ops.py`

---

## Phase 4 — Updates, Owner dashboard, monitoring

| Feature | Implemented | Tested | E2E validated | Remaining risks | Production readiness | Known limitations |
|---------|-------------|--------|---------------|-----------------|----------------------|-------------------|
| `/clinic-node/health-ops` heartbeat | Yes | **No** unit | **Yes** | No periodic telemetry upload | **Conditional** | On-request only; `schema_version` hard-coded `"head"` |
| Owner dashboard (ops, no PHI) | Partial | E2E PHI scan | **Yes** | Mistaken for multi-clinic cloud product | **Conditional** | Local single-node JSON only; **no SPA UI**; cloud aggregation not built |
| PHI exclusion on ops endpoints | Yes | E2E key scan | **Yes** | Outbox API can accept arbitrary payloads | **Conditional** | List API omits payload today |
| Update agent `apply-update.sh` | Partial | Script smoke | **Yes** (`UPDATE_APPLY_OK`) | Bad package can rebuild broken stack | **Not ready** | Header says “signed”; **no signature verify**; optional tar load only |
| Pre-update backup | Yes | In update script | **Yes** | Restore after failed update not automated | **Conditional** | Backup taken; **no rollback** path |
| Update rollback | **No** | — | **No** | Failed update may strand clinic | **Not ready** | |

**Phase 4 evidence:** `evidence/clinic-node/PHASE4_E2E_ACCEPTANCE.md`

---

## Phase 5 — Migration tooling & pilot readiness

| Feature | Implemented | Tested | E2E validated | Remaining risks | Production readiness | Known limitations |
|---------|-------------|--------|---------------|-----------------|----------------------|-------------------|
| `migrate-export-clinic.sh` | Partial | **No** | **Partial** | Cross-tenant data leak from multi-clinic cloud | **Not ready** | `CLINIC_ID` required but **not applied** as SQL filter; dumps whole tables |
| Export artifact generation (schema dump) | Yes | Scripted | **Yes** (`local-clinic-export.sql`) | Schema-only ≠ full clinic data cutover | **Conditional** | E2E used `pg_dump --schema-only`, not full export script path |
| `migrate-import-clinic.sh` | Partial | Presence only | **No** (destructive import not run) | Import can corrupt/clash with existing schema | **Not ready** | Stops backend + `psql`; no wipe/reset strategy; no app maintenance mode |
| Cloud → Node cutover freeze | Partial | — | **No** | Writes during cutover | **Not ready** | Container stop only |
| Pilot readiness checklist (local scaffolding) | Partial | Combined E2E | Smoke **Yes** | Overstating “complete” vs ops gaps | **Conditional** | Suitable for **standalone LAN** pilot only |

**Phase 5 evidence:** `evidence/clinic-node/PHASE5_E2E_ACCEPTANCE.md`, `PHASE3_5_E2E_ACCEPTANCE.md`

---

## Cross-cutting quality

| Area | Status |
|------|--------|
| Production isolation (Vercel/Railway untouched) | **Pass** |
| Phase 0–1 unit tests | **Pass** (`test_clinic_node_settings`, `test_clinic_node_bootstrap`) |
| Phase 2–5 unit/integration tests for ops | **Missing** |
| Browser / Playwright E2E on Clinic Node | **Missing** |
| Alembic RBAC check vs `nurse`/`pev_agent` | **Warn** — widen/fallback path; not clean |
| JWT secrets in evidence | Redacted in committed artifacts |
| Host-network validation vs mini-PC bridge | Agent evidence is host-mode; bridge must be revalidated on target hardware |

---

## Explicit MISSING items (must not assume present)

1. Cryptographic license issuance / verification  
2. License enforcement blocking clinical use when `EXPIRED` / missing  
3. Automatic outbox enqueue from clinical create/update/delete  
4. Cloud sync worker / remote push / real delta sync to Railway  
5. Conflict detection engine + resolve API + resolution UI  
6. Scheduled backups (cron / systemd timer)  
7. Backup retention / pruning  
8. Clinic Node restore script + restore E2E drill  
9. Signed update packages + signature verification  
10. Update rollback / blue-green version pin  
11. Multi-clinic cloud Owner aggregation + Owner UI  
12. Periodic heartbeat/telemetry agent (phone-home without PHI)  
13. Real `clinic_id` row filtering in migrate-export  
14. Executed import/cutover E2E against a live cloud dump  
15. Application maintenance / freeze mode (beyond stopping container)  
16. Unit/integration tests for Phase 3–5 ops code  
17. Frontend for license / outbox / conflicts / backup / owner-ops  
18. Nurse clinical workflow E2E (beyond login)  
19. Hospitalization, imaging, teleconsult, pharmacy stock, PEV, nutrition E2E on node  
20. Interactive SPA multi-role browser E2E + workstation CA trust procedure proven on site  
21. Phase 1–5 technician runbook sections in `deploy/clinic-node/README.md`  
22. PWA / Service Worker / IndexedDB offline (separate roadmap — not this V1)

---

## Go / No-Go decision matrix

### CONDITIONAL GO — deploy Offline V1 to pilot clinic **if all of the following are true**

1. Pilot is **standalone LAN**: no requirement for same-day cloud sync.  
2. Scope limited to **outpatient** path: reception → consultation → lab → pharmacy → cashier.  
3. Nurse / hospitalization / imaging / teleconsult are **out of scope** or paper-assisted.  
4. A trained technician is on-site or on-call for install, CA trust, and **manual daily backups**.  
5. Hardware is a dedicated mini-PC + UPS; Docker bridge networking is validated on **that** machine (not only host-network CI).  
6. Stakeholders accept that license, sync outbox, conflicts, update signing, and migration helpers are **scaffolding**, not production controls.  
7. Paper or secondary backup process exists for the first pilot weeks.  
8. Cloud production remains the separate online system; no automated cutover is attempted without a dedicated migration rehearsal.

### NO-GO — do **not** deploy if the pilot requires any of

1. Reliable cloud ↔ node sync or conflict reconciliation  
2. Cryptographic / enforceable licensing  
3. Proven disaster recovery (restore drill) and scheduled backups  
4. Unattended or signed software updates with rollback  
5. One-shot Cloud→Node patient data migration without rehearsal  
6. Full module parity (nurse care, inpatient, imaging, teleconsult, stock control) on day one  
7. Treating Phase 3–5 E2E smoke as proof of production ops maturity

---

## Final recommendation

**CONDITIONAL GO** for a **supervised Offline V1 LAN pilot**.

**Rationale:** Phases 0–2 deliver a working local appliance and a core clinical API path with recorded E2E acceptance. Phases 3–5 add useful **ops scaffolding** (manual backup, heartbeat, update rebuild helper, migration script shells) that passed smoke tests, but they are **not** production-grade sync, licensing, DR, or cutover.

**Pilot launch gate (must complete before first patient day):**

| # | Gate | Owner |
|---|------|-------|
| 1 | Fresh install on pilot mini-PC using **bridge** compose (or documented host exception) | Field tech |
| 2 | Trust local CA on every clinical workstation browser | Field tech |
| 3 | Create real staff accounts; force password change; verify role dashboards in UI | Clinic admin |
| 4 | Run a **same-patient** reception→doctor→lab→pharmacy→cashier dry run in the UI | Clinic lead |
| 5 | Configure and document **daily manual backup** + off-box copy (USB/NAS) | Field tech |
| 6 | Perform one **restore drill** on a spare volume / staging DB | Field tech |
| 7 | Written incident plan: who to call if stack down; UPS check | Clinic lead |
| 8 | Explicit sign-off that cloud sync / migration / license enforcement are deferred | Product owner |

**After pilot start — do not claim “Offline V1 complete” until missing items 1–8 (ops/DR) and nurse/module gaps are closed or formally deferred in writing.**

---

## Evidence index

| Phase | Acceptance doc | Marker / run |
|-------|----------------|--------------|
| 0 | `PHASE0_E2E_ACCEPTANCE.md` | `e2e-phase0/20260728T133741Z/` |
| 1 | `PHASE1_E2E_ACCEPTANCE.md` | `e2e-phase1/20260728T174249Z/` |
| 2 | `PHASE2_E2E_ACCEPTANCE.md` | `e2e-phase2/20260728T174521Z/` |
| 3 | `PHASE3_E2E_ACCEPTANCE.md` | part of `e2e-phase3-5/20260728T175050Z/` |
| 4 | `PHASE4_E2E_ACCEPTANCE.md` | same |
| 5 | `PHASE5_E2E_ACCEPTANCE.md` | same |
| 3–5 combined | `PHASE3_5_E2E_ACCEPTANCE.md` | `PHASE3_5_E2E_ACCEPTANCE_PASSED` |

**Validators:**  
`deploy/clinic-node/scripts/validate-e2e-phase{0,1,2}.sh`  
`deploy/clinic-node/scripts/validate-e2e-phase3-5.sh`
