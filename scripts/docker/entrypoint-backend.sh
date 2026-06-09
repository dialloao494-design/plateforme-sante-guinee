#!/bin/sh
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
python <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
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

from database import engine, Base
from database_migrations import ensure_doctor_geolocation_columns, ensure_patient_dossier_schema

Base.metadata.create_all(bind=engine)

try:
    from alembic.config import Config
    from alembic import command

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    print("[entrypoint] Alembic upgrade head OK.")
except Exception as exc:
    print(f"[entrypoint] Alembic warning (fallback migrations): {exc}")

ensure_doctor_geolocation_columns(engine)
ensure_patient_dossier_schema(engine)
print("[entrypoint] Schema ready.")
PY

if [ "${ENABLE_PILOT_SEED:-false}" = "true" ]; then
  echo "[entrypoint] Seeding pilot accounts..."
  python -c "from services.pilot_seed import seed_pilot_accounts; seed_pilot_accounts()"
fi

exec "$@"
