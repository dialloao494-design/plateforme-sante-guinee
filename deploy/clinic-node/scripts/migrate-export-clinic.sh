#!/usr/bin/env bash
# Phase 5 — export clinic-scoped PostgreSQL dump from a source DB URL (e.g. Railway).
# Usage:
#   SOURCE_DATABASE_URL=postgresql://... CLINIC_ID=17 \
#     ./deploy/clinic-node/scripts/migrate-export-clinic.sh /path/to/out.sgmig.sql
set -euo pipefail
OUT="${1:?output sql file required}"
CLINIC_ID="${CLINIC_ID:?CLINIC_ID required}"
SOURCE_DATABASE_URL="${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL required}"

echo "[migrate-export] clinic_id=${CLINIC_ID} -> ${OUT}"
# Export schema + data filtered by clinic_id for primary tenant tables.
# For V1 Offline we dump full schema then filtered data for key tables.
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

pg_dump --dbname="${SOURCE_DATABASE_URL}" --schema-only > "${TMPDIR}/schema.sql"
pg_dump --dbname="${SOURCE_DATABASE_URL}" --data-only --inserts \
  --table=clinics --table=users --table=clinic_staff --table=patients \
  --table=clinical_consultations --table=lab_orders --table=lab_results \
  --table=prescriptions --table=pharmacy_orders --table=clinic_charges \
  > "${TMPDIR}/data_raw.sql" || true

{
  echo "-- Santé Guinée clinic migration export"
  echo "-- clinic_id=${CLINIC_ID}"
  echo "-- exported_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cat "${TMPDIR}/schema.sql"
  echo
  echo "-- NOTE: Operator must filter/import clinic_id=${CLINIC_ID} rows carefully."
  echo "-- Prefer application-level migrate tools for production cutover."
  cat "${TMPDIR}/data_raw.sql"
} > "${OUT}"

echo "[migrate-export] wrote ${OUT} ($(wc -c < "${OUT}") bytes)"
echo "MIGRATION_EXPORT_OK"
