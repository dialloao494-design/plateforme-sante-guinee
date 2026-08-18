# Backup & Restore — PostgreSQL

## Automated backup (VPS)

Daily cron via deployment scripts:

```bash
bash deploy/vps/backup-db.sh
bash scripts/db/backup_verify.sh
```

Backups are written to `backups/sante_YYYYMMDD_HHMMSS.sql.gz` (gitignored),
gzip-tested, accompanied by a SHA-256 sidecar, and recorded under
`evidence/backup/`. The scheduled path fails if the artifact is too small,
unreadable, not a PostgreSQL SQL dump, or older than the configured RPO target.

## Manual backup

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  pg_dump -U sante sante | gzip > backups/sante_manual_$(date +%Y%m%d_%H%M%S).sql.gz
```

## Restore (incident recovery)

**Warning:** A live restore replaces clinical data. Do not execute one until an
isolated drill has passed, incident command has approved the restore point, and
application traffic has stopped. The automated tool below does not restore into
the live database.

```bash
cd /opt/plateforme-sante
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

gunzip -c backups/sante_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  psql -U sante sante

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
curl -s https://your-domain/api/health
```

## Guarded, isolated restore drill

Create credentials for a PostgreSQL server on which the current role may create
and drop a dedicated database. The target name must end in `_restore_verify` and
must differ from `DATABASE_URL`; system database names are refused.

```bash
export DATABASE_URL='postgresql://.../sante'
export VERIFICATION_DATABASE_URL='postgresql://.../sante_restore_verify'
bash scripts/db/restore_drill.sh backups/sante_YYYYMMDD_HHMMSS.sql.gz
```

The drill validates gzip and SQL signatures, records SHA-256 and backup age,
restores with `ON_ERROR_STOP=1`, verifies the Alembic head, counts critical
tables, checks for patients whose clinic is missing, measures RTO, drops the
verification database, and writes
`evidence/backup/latest-restore-drill.json`. It refuses to replace an existing
verification database unless `REPLACE_VERIFICATION_DATABASE=1` is explicitly
set. `KEEP_VERIFICATION_DATABASE=1` is available for authorized inspection.

Defaults are RPO <= 24 hours and RTO <= 60 minutes. Override only with the
clinic-approved targets:

```bash
BACKUP_RPO_TARGET_MINUTES=720 BACKUP_RTO_TARGET_MINUTES=30 \
  bash scripts/db/restore_drill.sh backups/sante_YYYYMMDD_HHMMSS.sql.gz
```

Artifact-only validation (no database mutation) is also available:

```bash
python3 scripts/db/backup_restore_evidence.py backups/sante_YYYYMMDD_HHMMSS.sql.gz \
  --evidence evidence/backup/artifact-check.json
```

## SQLite (development only)

```bash
cp sante.db backups/sante_dev_$(date +%Y%m%d).db
# Restore:
cp backups/sante_dev_YYYYMMDD.db sante.db
```

## Retention policy (recommended)

| Environment | Retention | Off-site |
|-------------|-----------|----------|
| Production | 30 daily + 12 monthly | Yes (encrypted object storage) |
| Staging | 7 daily | Optional |
| Development | Ad hoc | No |

## Post-restore checklist

1. Preserve the JSON evidence, dump SHA-256 sidecar, operator, and incident/drill ticket.
2. `GET /health` returns OK.
3. `alembic current` matches the expected head.
4. `python scripts/qa_production_e2e.py` reports zero failures.
5. Verify admin login, audit-log continuity, patient documents/attachments, and a sample invoice.
6. Record actual RPO/RTO against the approved target and obtain operator/clinic-lead sign-off.
