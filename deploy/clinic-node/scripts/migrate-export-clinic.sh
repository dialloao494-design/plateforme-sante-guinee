#!/usr/bin/env bash
# Production-safe clinic export with clinic_id filtering, checksum, dry-run.
# Usage:
#   SOURCE_DATABASE_URL=postgresql://... CLINIC_ID=17 \
#     ./deploy/clinic-node/scripts/migrate-export-clinic.sh /path/to/out.sgmig.sql.gz
#   DRY_RUN=1 ... (validates connectivity + counts only)
set -euo pipefail
OUT="${1:?output sql.gz file required}"
CLINIC_ID="${CLINIC_ID:?CLINIC_ID required}"
SOURCE_DATABASE_URL="${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL required}"
DRY_RUN="${DRY_RUN:-0}"
export CLINIC_ID SOURCE_DATABASE_URL OUT DRY_RUN

echo "[migrate-export] clinic_id=${CLINIC_ID} dry_run=${DRY_RUN} -> ${OUT}"

if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi
export DOCKER

python3 <<'PY'
import gzip, hashlib, os, subprocess, sys
from pathlib import Path
import psycopg2

url = os.environ["SOURCE_DATABASE_URL"]
cid = int(os.environ["CLINIC_ID"])
out = Path(os.environ["OUT"])
dry = os.environ.get("DRY_RUN") == "1"
docker = os.environ.get("DOCKER", "sudo docker")

conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("SELECT id, name FROM clinics WHERE id=%s", (cid,))
row = cur.fetchone()
if not row:
    print("CLINIC_NOT_FOUND", cid, file=sys.stderr)
    sys.exit(1)
print("CLINIC_OK", row[0], row[1])

tables = [
    ("users", "clinic_id"),
    ("patients", "clinic_id"),
    ("consultations", "clinic_id"),
    ("lab_orders", "clinic_id"),
    ("prescriptions", "clinic_id"),
    ("pharmacy_orders", "clinic_id"),
    ("clinic_charges", "clinic_id"),
]
for t, c in tables:
    try:
        cur.execute(f"SELECT count(*) FROM {t} WHERE {c}=%s", (cid,))
        print(f"COUNT {t}", cur.fetchone()[0])
    except Exception as e:
        conn.rollback()
        print(f"COUNT {t} SKIP", e)

if dry:
    print("MIGRATION_EXPORT_DRY_RUN_OK")
    conn.close()
    sys.exit(0)

def dump_schema() -> str:
    # Prefer local pg_dump; fall back to clinic-node db container.
    try:
        return subprocess.check_output(
            ["pg_dump", f"--dbname={url}", "--schema-only", "--no-owner", "--no-acl"],
            text=True,
        )
    except FileNotFoundError:
        return subprocess.check_output(
            [
                *docker.split(),
                "exec",
                "clinic-node-db-1",
                "pg_dump",
                "-U",
                "sante",
                "--schema-only",
                "--no-owner",
                "--no-acl",
                "sante",
            ],
            text=True,
        )

schema = dump_schema()

def sql_literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"

parts = [f"-- Santé Guinée clinic migration export\n-- clinic_id={cid}\n", schema, "\nBEGIN;\n"]
cur.execute("SELECT * FROM clinics WHERE id=%s", (cid,))
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
if rows:
    vals = ",".join(sql_literal(v) for v in rows[0])
    parts.append(f"DELETE FROM clinics WHERE id={cid};\n")
    parts.append(f"INSERT INTO clinics ({', '.join(cols)}) VALUES ({vals});\n")

for table, col in tables:
    try:
        cur.execute(f"SELECT * FROM {table} WHERE {col}=%s", (cid,))
    except Exception:
        conn.rollback()
        continue
    cols = [d[0] for d in cur.description]
    fetched = cur.fetchall()
    parts.append(f"-- data {table} n={len(fetched)}\n")
    parts.append(f"DELETE FROM {table} WHERE {col}={cid};\n")
    for row in fetched:
        vals = ",".join(sql_literal(v) for v in row)
        parts.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({vals});\n")

parts.append("COMMIT;\n")
raw = "".join(parts).encode()
out.parent.mkdir(parents=True, exist_ok=True)
with gzip.open(out, "wb") as gz:
    gz.write(raw)
digest = hashlib.sha256(raw).hexdigest()
Path(str(out) + ".sha256").write_text(digest + "\n", encoding="utf-8")
print("WROTE", out, "bytes", out.stat().st_size, "sha256", digest)
print("MIGRATION_EXPORT_OK")
conn.close()
PY
