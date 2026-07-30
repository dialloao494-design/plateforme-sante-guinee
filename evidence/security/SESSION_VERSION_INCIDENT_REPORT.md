# Railway incident — missing `users.session_version`

## 1. Exact root cause

Railway runtime error:

```text
psycopg2.errors.UndefinedColumn: column users.session_version does not exist
```

The SQLAlchemy `User` model and auth path (`security.get_current_user`, login JWT claims) require `users.session_version`. Production PostgreSQL did not have the column.

Why the column was missing even though migration `20260730_0023` adds it:

1. `0023` added `session_version` in the **same Alembic transaction** as the unique `platform_owner` index. If the index step failed, PostgreSQL rolled back the column add.
2. Entrypoint / `run_alembic_upgrade_head()` previously **swallowed** Alembic failures and continued to start Uvicorn.
3. `Base.metadata.create_all()` does **not** add columns to existing tables.
4. Result: app started, queried `users.session_version` → `UndefinedColumn` → 502.

`token_version` (Wave 0) is a **distinct** column used for access-token invalidation (`tv` JWT claim). Both are required; neither replaces the other.

## 2. Missing / broken migration revision

| Revision | Role |
|---|---|
| `20260730_0023_single_platform_owner` | Originally added `session_version` + unique owner index (transaction coupling risk) |
| `20260730_0024_security_wave0_identity` | Adds `token_version` and other Wave0 fields |
| **`20260730_0025_ensure_session_version` (new)** | Idempotent recovery: adds missing `session_version` / Wave0 columns / token tables |

## 3. Fix implemented

1. New Alembic revision `20260730_0025_ensure_session_version` (idempotent, preserves rows, default `0`).
2. Hardened `0023` to commit `session_version` via `autocommit_block` before index creation.
3. `ensure_user_session_security_columns()` runtime failsafe (ADD COLUMN IF NOT EXISTS on Postgres).
4. Entrypoint order: wait DB → `alembic upgrade head` (fail closed when deployed) → ensure security columns → verify `SELECT session_version` → start Uvicorn.
5. `run_alembic_upgrade_head(fail_closed=True)` on Railway/production.
6. Startup schema check requires `session_version` + `token_version`.

## 4. Alembic chain

**Before:**  
`… → 0022 → 0023 → 0024` (single head `0024`)

**After:**  
`… → 0022 → 0023 → 0024 → 0025` (single head `0025`)

## 5. Tests executed

- Full suite: **307 passed, 1 skipped**
- `tests/test_session_version_migration.py` — stamped-at-0024 missing column → upgrade to 0025; ensure helper; login after migration
- Auth / Wave0 / session tests
- Local simulation: existing users preserved, `session_version=0`, head=`0025`

## 6–8. Production deployment / health / data

Filled after Railway redeploy of this commit (see SHA below). No `drop_all`, reset, or destructive purge is used.

## 9. Deployed commit SHA

See git tip after push to `main`.
