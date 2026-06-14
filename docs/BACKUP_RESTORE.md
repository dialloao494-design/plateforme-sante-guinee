# Backup & Restore — PostgreSQL

## Automated backup (VPS)

Daily cron via deployment scripts:

```bash
bash deploy/vps/backup-db.sh
bash scripts/db/backup_verify.sh
```

Backups are written to `backups/sante_YYYYMMDD_HHMMSS.sql.gz` (gitignored).

## Manual backup

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  pg_dump -U sante sante | gzip > backups/sante_manual_$(date +%Y%m%d_%H%M%S).sql.gz
```

## Restore (incident recovery)

**Warning:** This replaces live data. Stop application traffic first.

```bash
cd /opt/plateforme-sante
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

gunzip -c backups/sante_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  psql -U sante sante

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
curl -s https://your-domain/api/health
```

## Non-destructive restore drill

```bash
bash scripts/db/restore_drill.sh backups/sante_YYYYMMDD.sql.gz
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

1. `GET /health` returns OK
2. `alembic current` matches expected head
3. `python scripts/qa_production_e2e.py` — zero FAIL
4. Verify admin login and audit log continuity
