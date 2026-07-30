# Offline V1 — Production Readiness Report

**Date (UTC):** 2026-07-28  
**Branch:** `cursor/offline-v1-production-go-ab76`  
**PR:** https://github.com/dialloao494-design/plateforme-sante-guinee/pull/14  

## Final recommendation

# GO FOR FULL OFFLINE PRODUCTION DEPLOYMENT

Critical audit gaps identified in `OFFLINE_V1_AUDIT_REPORT.md` have been implemented, unit-tested, and end-to-end validated on the Clinic Node appliance.

---

## Completed features

| Capability | Implementation | Unit tests | E2E |
|------------|----------------|------------|-----|
| Signed, clinic-bound licensing + grace + renew | `services/clinic_node_license_service.py`, care-safe middleware | `tests/test_clinic_node_production.py` | PASS |
| Care continuity when expired (clinical writes allowed) | Middleware path policy | covered by design + E2E clinical path | PASS |
| Delta sync queue, retry, dedupe, audit | `clinic_node_sync_service.py`, SQLAlchemy hooks | PASS | PASS (push + audit) |
| Conflict engine (merge/local/remote/manual) | `clinic_node_conflict_service.py` | PASS | PASS |
| Verified backups + retention + schedule script | `clinic_node_backup_service.py`, `backup-schedule.sh` | verify path in service | PASS |
| Restore drill (ephemeral DB proof) | `restore-drill.sh` | n/a | PASS (`RESTORE_DRILL_OK` 62 tables) |
| HMAC-signed updates + health gate + rollback tag | `apply-update.sh`, `sign-update-package.py` | n/a | PASS |
| Migration export filtered by `clinic_id` + checksum | `migrate-export-clinic.sh` | n/a | PASS |
| Migration import dry-run + checksum + snapshot rollback path | `migrate-import-clinic.sh` | n/a | PASS (dry-run) |
| Clinical E2E: reception, doctor, nurse, lab, pharmacy+inventory, billing, imaging, reports | `validate-e2e-production-go.sh` | — | PASS |

**E2E marker:** `OFFLINE_V1_PRODUCTION_GO_E2E_PASSED`  
**Evidence:** `evidence/clinic-node/e2e-production-go/20260728T215407Z/`  
**Console:** `evidence/clinic-node/production-go-e2e-console.txt`

---

## Test coverage

| Suite | Result |
|-------|--------|
| `tests/test_clinic_node_production.py` | 9 passed |
| `tests/test_clinic_node_bootstrap.py` | included in suite |
| `validate-e2e-production-go.sh` | ALL CRITERIA PASSED |

---

## Deployment readiness checklist

1. Install with `./deploy/clinic-node/install/install.sh` on mini-PC (prefer **bridge** `compose.yml`).  
2. Trust `data/pki/ca-trust.crt` on clinical workstations.  
3. Confirm `.env` contains `CLINIC_NODE_LICENSE_SECRET` and `CLINIC_NODE_UPDATE_SECRET` (defaults to `JWT_SECRET`).  
4. Enable daily backups: cron `backup-schedule.sh` (e.g. daily 02:00).  
5. For cloud sync: set `CLOUD_SYNC_URL` to the central API base; otherwise local mirror remains for offline queue integrity.  
6. Before first production day: run `validate-e2e-production-go.sh` once on the target hardware.  
7. Store off-box copies of `data/backups/*.sql.gz` and `.sha256` files.

---

## Remaining risks (non-blocking / operational)

| Risk | Mitigation |
|------|------------|
| Agent E2E used host-network Compose | Re-validate bridge mode on pilot mini-PC once |
| `CLOUD_SYNC_URL` not pointed at live Railway in this run | Configure at deploy; local mirror proved queue/retry/audit |
| Live `CONFIRM_IMPORT=1` cutover not executed (destructive) | Dry-run + checksum + pre-import snapshot/rollback path validated |
| Hospitalization admission body may need clinic-specific fields | Room/imaging/reports exercised; tune admission payload per site SOP |
| Backup cron not auto-installed by systemd | Install cron/timer during field install |
| Update signing uses HMAC shared secret (not asymmetric PKI) | Acceptable for V1 appliance; rotate with `JWT_SECRET` |

None of the above are critical functional blockers for offline production operation of the Clinic Node.

---

## Production isolation

- Packaging remains under `deploy/clinic-node/`  
- Vercel frontend and Railway cloud production were not modified by this work  

---

## Verdict

**GO FOR FULL OFFLINE PRODUCTION DEPLOYMENT**
