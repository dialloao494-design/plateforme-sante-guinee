# Database Migrations

## Alembic (recommended for production)

```bash
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# Create a new migration (developers only)
alembic revision --autogenerate -m "describe change"
```

Migration files live in `alembic/versions/`. Key revisions:

| Revision | Description |
|----------|-------------|
| `20260515_0001` | Baseline stamp |
| `20260525_0003` | Patient dossier |
| `20260526_0004` | Clinical CIS tables |
| `20260527_0005` | Clinic billing & audit |
| `20260528_0006` | Cashier RBAC |
| `20260615_0007` | Medical history & follow-ups |

## Startup additive migrations (SQLite / hotfix)

`database_migrations.py` runs lightweight `ALTER TABLE` guards on application startup for:

- Doctor geolocation columns
- Message attachment metadata
- Patient dossier schema
- Medical history tables (`ensure_medical_history_schema`)

These are idempotent and safe to run on every boot.

## Fresh local database

```bash
# SQLite (development)
rm -f sante.db
python init_db.py
alembic upgrade head
```

With pilot seed:

```bash
ENABLE_PILOT_SEED=true uvicorn main:app --host 127.0.0.1 --port 8000
python -m services.medical_history_seed
```

## Production PostgreSQL

1. Set `DATABASE_URL=postgresql://user:pass@host:5432/sante`
2. `alembic upgrade head`
3. Verify: `python scripts/qa_db_counts.py`
4. **Never** set `ENABLE_PILOT_SEED=true` in production

## Rollback

Alembic downgrades are available per revision file. For production, prefer restore from backup (see [BACKUP_RESTORE.md](./BACKUP_RESTORE.md)) over destructive downgrades.
