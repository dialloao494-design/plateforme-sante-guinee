#!/bin/sh
# Railway / Docker entrypoint — wait for DB, apply schema, start uvicorn.
# Intentionally runs as the container user (no gosu) for Railway compatibility.
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
python <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
if not url.startswith("postgresql"):
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
sys.exit(1)
PY

echo "[entrypoint] Applying schema (create_all + Alembic)..."
python <<'PY'
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

from database import engine, Base
from database_migrations import (
    ensure_alembic_version_column,
    ensure_doctor_geolocation_columns,
    ensure_patient_dossier_schema,
    ensure_user_roles_check_constraint,
    normalize_legacy_user_roles,
    ensure_single_platform_owner_index,
)

Base.metadata.create_all(bind=engine)
ensure_alembic_version_column(engine)

try:
    from alembic.config import Config
    from alembic import command

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    print("[entrypoint] Alembic upgrade head OK.")
except Exception as exc:
    print(f"[entrypoint] Alembic warning (retry after widen): {exc}")
    ensure_alembic_version_column(engine)
    try:
        from alembic.config import Config
        from alembic import command

        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
        print("[entrypoint] Alembic upgrade head OK (retry).")
    except Exception as exc2:
        print(f"[entrypoint] Alembic warning (fallback migrations): {exc2}")

ensure_doctor_geolocation_columns(engine)
ensure_patient_dossier_schema(engine)
ensure_user_roles_check_constraint(engine)
normalize_legacy_user_roles(engine)
ensure_single_platform_owner_index(engine)
print("[entrypoint] Schema ready.")
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
