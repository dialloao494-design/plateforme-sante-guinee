# Security Wave 5 — Sync / Backup / DR / Update Hardening Report

**Status:** COMPLETE  
**Branch:** `cursor/security-wave5-sync-dr-ab76`  
**Scope:** Cloud synchronization integrity, delta sync, replay protection, backup encryption, restore validation, disaster recovery, integrity verification, update security, rollback.  
**Constraint honored:** Offline Clinic Node sync/license product APIs remain frozen (security libraries + ops scripts only).

## Deliverables

| Area | Implementation |
|------|----------------|
| Cloud / delta sync | `core/sync_security.py` — HMAC envelopes, content SHA-256, batch integrity |
| Replay protection | `ReplayGuard` (nonce + event_id TTL) + timestamp skew |
| Sync token gate | `require_sync_token` |
| Backup encryption | Fernet + `\x00SGBKENC\x01` magic; `BACKUP_ENCRYPTION_KEY` |
| Integrity verification | SHA-256 sidecars for plain and encrypted artifacts |
| Restore validation | `pre_restore_validation` (decrypt + gzip/SQL gate) |
| Disaster recovery | Checklist + `docs/DISASTER_RECOVERY_SECURITY.md` |
| Recovery orchestration | `services/recovery_security_service.py` (S1–S4) |
| Update security | Signed manifests; JWT fallback refused in clinic-node/production |
| Rollback | Image tag record/read + `apply_update.sh` health-gate path |
| Ops scripts | `scripts/security/*` |
| Smoke validator | `scripts/deploy/validate_security_wave5.py` |

## Recovery scenario validation

| ID | Scenario | Result |
|----|----------|--------|
| S1 | Plaintext gzip/SQL precheck | PASS |
| S2 | SHA-256 sidecar match | PASS |
| S3 | Encrypted restore gate | PASS |
| S4 | DR checklist (≥8 steps) | PASS |
| S5 | Sync envelope replay rejected | PASS |
| S6 | Bad update signature refused | PASS |
| S7 | Rollback image tag roundtrip | PASS |

Evidence: `evidence/security/WAVE5_RECOVERY_SCENARIOS.txt`

## Test evidence

| Artifact | Result |
|----------|--------|
| `WAVE5_SMOKE.txt` | `WAVE5 SMOKE OK` |
| `WAVE5_PYTEST_WAVE5.txt` | **21 passed** |
| `WAVE5_PYTEST_FULL.txt` | **223 passed**, 3 failed (pre-existing: `test_end_to_end_clinic`, `test_reminders` ×2 — unrelated to Wave 5) |
| `WAVE5_STATIC.txt` | Inventory + symbol export OK |

## Operator notes

1. Set unique `BACKUP_ENCRYPTION_KEY` and `CLINIC_NODE_UPDATE_SECRET` per node.  
2. Encrypt backups before off-box copy: `python3 scripts/security/encrypt_backup.py dump.sql.gz`.  
3. Always run `restore_validate.py --require-encryption --scenarios` before live restore.  
4. Sign updates with `sign_update_package.py`; apply via `apply_update.sh`.  
5. After live restore, rotate JWT/sync/update/attachment/backup keys (DR-06).

## Residual risks

- Sync HMAC remains symmetric (architecture recommends mTLS / asymmetric later).  
- Update signing remains HMAC (architecture recommends Ed25519 later).  
- `ReplayGuard` is process-local; multi-instance ingest needs shared store when product sync is unfrozen.  
- Age/GPG encrypt scripts ship with Clinic Node package when present; Wave 5 Fernet path is the portable CI/default control.
