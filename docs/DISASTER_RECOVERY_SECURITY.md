# Disaster Recovery Security — Santé Guinée (Security Wave 5)

This runbook hardens backup encryption, restore validation, sync integrity,
update signing, and rollback. It does **not** unfreeze Offline Clinic Node
sync/license product APIs.

## Threats addressed

| Threat | Control |
|--------|---------|
| Forged sync / delta events | HMAC-SHA256 signed envelopes + content SHA-256 |
| Replay of sync events | Nonce + event_id TTL (`ReplayGuard`) + timestamp skew |
| Stolen plaintext backups | Fernet encryption (`BACKUP_ENCRYPTION_KEY`) + SHA-256 sidecars |
| Corrupt / wrong restore | `pre_restore_validation` before any drill or live restore |
| Malicious update package | Signed manifest required; JWT fallback refused in clinic-node/production |
| Failed update | Pre-update encrypted backup + health gate + rollback image tag |

## Cloud / delta sync

Use `core.sync_security`:

1. `build_signed_envelope(...)` on the producer (outbox).
2. Gate ingest with `require_sync_token(X-Sync-Token, expected)`.
3. `verify_signed_envelope(...)` then `ReplayGuard.consume_envelope(...)`.
4. Optionally bind batches with `delta_batch_integrity(...)`.

Env:

- `SYNC_MAX_SKEW_SECONDS` (default 300)
- `SYNC_NONCE_TTL_SECONDS` (default 600)
- Sync shared secret / `X-Sync-Token` (operator-configured; never commit)

## Backup encryption & integrity

```bash
export BACKUP_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
python scripts/security/encrypt_backup.py /path/to/dump.sql.gz
python scripts/security/decrypt_backup.py /path/to/dump.sql.gz.enc -o /tmp/restored.sql.gz
python scripts/security/restore_validate.py /path/to/dump.sql.gz.enc --require-encryption --scenarios
```

Artifacts:

- `<dump>.sql.gz` — plaintext logical dump
- `<dump>.sql.gz.sha256` — integrity sidecar
- `<dump>.sql.gz.enc` (+ `.sha256`) — encrypted package (`\\x00SGBKENC\\x01` + Fernet)

## Restore validation (mandatory)

Never pipe a dump into Postgres until:

1. Sidecar SHA-256 matches (when present).
2. Encrypted package decrypts with the current backup key.
3. Gzip CRC + SQL-ish header pass (`verify_gzip_sql_backup`).
4. Ephemeral restore drill succeeds (ops script / monthly cadence).

Live restore requires dual control / break-glass + ticket (DR-05).

## Disaster recovery checklist

Machine-readable: `core.backup_security.disaster_recovery_checklist()`.

1. DR-01 Identify latest verified encrypted backup  
2. DR-02 Isolate restore target network  
3. DR-03 Take pre-restore snapshot of current DB volume  
4. DR-04 Run ephemeral restore-drill  
5. DR-05 Live restore with dual-control approval  
6. DR-06 Rotate JWT, sync, update, attachment, and backup keys  
7. DR-07 Verify `/health/ready` and sample clinical reads  
8. DR-08 Document RPO/RTO and close incident  

## Update security & rollback

```bash
export CLINIC_NODE_UPDATE_SECRET="…unique per node…"
# Create package dir with manifest.json (+ optional images/)
python scripts/security/sign_update_package.py ./update-pkg --version 1.2.3
./scripts/security/apply_update.sh ./update-pkg
```

Controls:

- `CLINIC_NODE_UPDATE_SECRET` required; JWT fallback blocked unless lab + `ALLOW_UPDATE_JWT_FALLBACK`
- Optional per-file digests in `manifest["files"]`
- Pre-update encrypted backup when `backup_required`
- Previous backend image id written for automatic rollback on health failure

## Recovery scenario matrix (must pass)

| ID | Scenario | Pass criteria |
|----|----------|---------------|
| S1 | Plaintext precheck | gzip/SQL OK |
| S2 | SHA-256 match | sidecar matches bytes |
| S3 | Encrypted restore gate | decrypt + gzip/SQL OK |
| S4 | DR checklist | eight required steps present |
| S5 | Sync replay | second identical envelope rejected |
| S6 | Bad update signature | `SIGNATURE_INVALID` / refuse apply |
| S7 | Rollback tag | previous image id recorded and readable |

Evidence: `evidence/security/WAVE5_*` and `python scripts/deploy/validate_security_wave5.py`.
