#!/bin/sh
# Railway / Docker entrypoint:
# 1) wait for Postgres  2) alembic upgrade head  3) verify schema (no runtime DDL)  4) start uvicorn
set -e

COMMIT_SHA="${RAILWAY_GIT_COMMIT_SHA:-${RAILWAY_GIT_COMMIT:-${GIT_COMMIT:-unset}}}"
MARKER_FILE="/app/deploy/RAILWAY_DEPLOY_MARKER.txt"
MARKER_ID="missing"
if [ -f "$MARKER_FILE" ]; then
  MARKER_ID="$(sed -n 's/^marker_id=//p' "$MARKER_FILE" | head -n1)"
fi
echo "[entrypoint] commit_sha=${COMMIT_SHA}"
echo "[entrypoint] deploy_marker=${MARKER_ID}"
echo "[entrypoint] Waiting for PostgreSQL..."
python <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

from core.deploy_hardening import (
    database_host,
    database_url_sslmode,
    normalize_database_url_for_runtime,
)

url = normalize_database_url_for_runtime(os.environ.get("DATABASE_URL", ""))
os.environ["DATABASE_URL"] = url
host = database_host(url) or "(none)"
print(
    f"[entrypoint] db_host={host} sslmode={database_url_sslmode(url) or 'default'}"
)
if not url.startswith("postgresql"):
    print("[entrypoint] Non-Postgres DATABASE_URL — skipping DB wait.")
    sys.exit(0)

engine = create_engine(url, pool_pre_ping=True)
for i in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] Database is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"[entrypoint] DB not ready ({i+1}/60): {exc}")
        time.sleep(2)
print("[entrypoint] FATAL: database not reachable", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] Applying Alembic migrations to head..."
python <<'PY'
import os
import sys

import models.user  # noqa: F401
import models.patient  # noqa: F401
import models.doctor  # noqa: F401
import models.rendezvous  # noqa: F401
import models.payment  # noqa: F401
import models.availability  # noqa: F401
import models.message  # noqa: F401
import models.notification_event  # noqa: F401
import models.clinical_note  # noqa: F401
import models.consultation_summary  # noqa: F401
import models.patient_document  # noqa: F401
import models.clinical_audit_log  # noqa: F401
import models.clinic  # noqa: F401
import models.clinical_consultation  # noqa: F401
import models.lab_order  # noqa: F401
import models.lab_result  # noqa: F401
import models.prescription  # noqa: F401
import models.pharmacy_order  # noqa: F401
import models.nutrition  # noqa: F401
import models.immunization  # noqa: F401
import models.password_reset_token  # noqa: F401
import models.email_verification_token  # noqa: F401
import models.visit_workflow  # noqa: F401
import models.refresh_token  # noqa: F401
import models.nurse_assessment  # noqa: F401
import models.clinic_charge  # noqa: F401
import models.clinic_charge_payment  # noqa: F401

from database import engine
from database_migrations import (
    ensure_alembic_version_column,
    ensure_doctor_geolocation_columns,
    ensure_patient_dossier_schema,
    ensure_user_roles_check_constraint,
    normalize_legacy_user_roles,
    ensure_single_platform_owner_index,
    ensure_user_session_security_columns,
    run_alembic_upgrade_head,
)
from sqlalchemy import inspect, text

deployed = (os.getenv("ENVIRONMENT") or "").strip().lower() in {
    "production",
    "staging",
    "clinic-node",
    "clinic_node",
} or bool((os.getenv("RAILWAY_ENVIRONMENT") or "").strip())

# alembic_version column helper is metadata-only for migration bookkeeping.
ensure_alembic_version_column(engine)

try:
    run_alembic_upgrade_head(fail_closed=deployed)
    print("[entrypoint] Alembic upgrade head OK.")
except Exception as exc:
    import traceback

    cause = exc.__cause__ or exc.__context__
    print(f"[entrypoint] FATAL: Alembic upgrade failed: {exc}", file=sys.stderr)
    if cause is not None:
        print(f"[entrypoint] Alembic underlying cause: {cause!r}", file=sys.stderr)
    traceback.print_exc()
    if deployed:
        sys.exit(1)
    print("[entrypoint] Continuing in non-deployed mode after Alembic failure.")

# Production/deployed: Alembic is the sole schema authority — no runtime DDL.
# Development/local: keep ensure_* helpers for disposable databases.
if deployed:
    print("[entrypoint] Deployed mode: skipping runtime ensure_* schema mutations (Alembic-only).")
else:
    try:
        ensure_user_session_security_columns(engine)
        print("[entrypoint] users.session_version / token_version verified.")
    except Exception as exc:
        print(f"[entrypoint] FATAL: security column ensure failed: {exc}", file=sys.stderr)
        sys.exit(1)

    ensure_doctor_geolocation_columns(engine)
    ensure_patient_dossier_schema(engine)
    ensure_user_roles_check_constraint(engine)
    normalize_legacy_user_roles(engine)
    ensure_single_platform_owner_index(engine)

# Verify-only checks (no DDL) — fail closed if schema incomplete.
insp = inspect(engine)
if "users" not in insp.get_table_names():
    print("[entrypoint] FATAL: users table missing after migrations", file=sys.stderr)
    sys.exit(1)
cols = {c["name"] for c in insp.get_columns("users")}
required = {"session_version", "token_version", "role", "email", "hashed_password"}
missing = sorted(required - cols)
if missing:
    print(
        f"[entrypoint] FATAL: users missing required columns: {missing}",
        file=sys.stderr,
    )
    sys.exit(1)

# Smoke: ORM-shaped SELECT that previously crashed production.
with engine.connect() as conn:
    conn.execute(text("SELECT id, session_version, token_version FROM users LIMIT 1"))
print("[entrypoint] Schema ready — starting application.")
PY

echo "[entrypoint] Preflight import main (boot guards)..."
python - <<'PY'
import sys

try:
    import main  # noqa: F401
except SystemExit as exc:
    print(f"[entrypoint] FATAL: main boot guard exited: {exc}", file=sys.stderr)
    raise
except Exception as exc:
    print(f"[entrypoint] FATAL: main import failed: {exc}", file=sys.stderr)
    raise
print("[entrypoint] main import OK")
PY

if [ "${ENABLE_PILOT_SEED:-false}" = "true" ]; then
  echo "[entrypoint] Seeding pilot accounts..."
  python -c "from services.pilot_seed import seed_pilot_accounts; seed_pilot_accounts()" \
    || echo "[entrypoint] WARNING: pilot seed skipped (non-fatal)"
fi

if [ "${ENABLE_STAGING_E2E_SEED:-false}" = "true" ]; then
  echo "[entrypoint] Seeding staging E2E multi-tenant accounts..."
  python scripts/deploy/staging_e2e_seed.py \
    || echo "[entrypoint] WARNING: staging E2E seed skipped (non-fatal)"
fi

echo "[entrypoint] Starting: $*"
exec "$@"
