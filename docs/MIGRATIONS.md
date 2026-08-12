# Database Migrations

## Alembic (required for production)

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
| `20260812_0028` | `patient_number` backfill + per-clinic unique index |

## Schema authority by environment

| Environment | `create_all` | `ensure_*` runtime DDL | Alembic `upgrade head` |
|-------------|--------------|------------------------|-------------------------|
| Local dev / pytest | Yes (empty DB bootstrap) | Yes (idempotent guards) | Yes (recommended) |
| Production / staging / clinic-node | **No** | **No** | **Required** (fail-closed on error) |
| Railway (`RAILWAY_*` without `ENVIRONMENT`) | **No** | **No** | **Required** |

`main._alembic_only_schema()` gates this behaviour. Deployed boots verify critical columns including `patients.patient_number` after Alembic runs.

## Startup additive migrations (SQLite / hotfix — dev only)

`database_migrations.py` runs lightweight `ALTER TABLE` guards on application startup **only in local development** for:

- Doctor geolocation columns
- Message attachment metadata
- Patient dossier schema
- Medical history tables (`ensure_medical_history_schema`)

These are idempotent and safe to run on every boot in dev. **Do not rely on them in production** — add an Alembic revision instead.

## `patient_number` integrity

- Canonical format: `PAT-{clinic_id:03d}-{patient_id:06d}` (see `core/patient_number.py`).
- Reception HIS assigns on registration (flush → assign → single commit).
- Alembic `20260812_0028` backfills legacy `NULL` rows and adds `uq_patients_clinic_patient_number` when no duplicates remain.
- DB-level `NOT NULL` is applied on PostgreSQL when safe; SQLite keeps nullable column + app enforcement.

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
