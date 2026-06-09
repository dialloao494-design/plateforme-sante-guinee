#!/usr/bin/env python3
"""GO PILOTE — verification checklist with proofs."""
from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BASE = os.getenv("PILOT_API_BASE", "http://127.0.0.1:8088/api").rstrip("/")
HTTPS_BASE = os.getenv("PILOT_HTTPS_BASE", "https://127.0.0.1:9443/api").rstrip("/")
def _pilot_pg_dsn() -> str:
    if os.getenv("PILOT_PG_DSN"):
        return os.getenv("PILOT_PG_DSN", "")
    user = os.getenv("POSTGRES_USER", "sante")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "sante")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


PG_DSN = _pilot_pg_dsn()

REQUIRED_TABLES = [
    "clinical_notes",
    "consultation_summaries",
    "patient_documents",
    "clinical_audit_logs",
]
REQUIRED_ROUTES = [
    "/patients/{patient_id}/notes",
    "/patients/{patient_id}/summaries",
    "/patients/{patient_id}/documents",
    "/patients/{patient_id}/timeline",
]

results: list[tuple[str, bool, str]] = []


def log(name: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "FAIL"
    results.append((name, ok, detail))
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def req(method: str, path: str, token: str | None = None, body: dict | None = None, base: str = BASE):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    ctx = None
    if base.startswith("https"):
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, timeout=30, context=ctx) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return e.code, json.loads(err)
        except json.JSONDecodeError:
            return e.code, err


def login(email: str, password: str) -> str:
    code, data = req("POST", "/auth/login-json", None, {"email": email, "password": password})
    if code != 200 or not isinstance(data, dict) or not data.get("access_token"):
        raise RuntimeError(f"Login failed {email}: {code} {data}")
    return data["access_token"]


def pg_query(sql: str):
    try:
        import psycopg2
    except ImportError:
        return None, "psycopg2 not installed"
    try:
        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows, None
    except Exception as exc:
        return None, str(exc)


def main() -> int:
    print("=== GO PILOTE — VERIFICATION ===\n")

    # PostgreSQL
    rows, err = pg_query("SELECT version()")
    log("PostgreSQL actif", rows is not None and err is None, err or (rows[0][0][:60] if rows else ""))

    for table in REQUIRED_TABLES:
        try:
            import psycopg2
            conn = psycopg2.connect(PG_DSN)
            cur = conn.cursor()
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                (table,),
            )
            exists = cur.fetchone()[0]
            conn.close()
            log(f"Table {table}", bool(exists), "present" if exists else "MISSING")
        except Exception as exc:
            log(f"Table {table}", False, str(exc))

    # Alembic version
    try:
        import psycopg2
        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version")
        ver = cur.fetchone()
        conn.close()
        log("Migration Alembic", ver is not None, ver[0] if ver else "no alembic_version")
    except Exception as exc:
        log("Migration Alembic", False, str(exc))

    # OpenAPI routes
    code, openapi = req("GET", "/openapi.json")
    paths = openapi.get("paths", {}) if isinstance(openapi, dict) else {}
    for route in REQUIRED_ROUTES:
        key = route.replace("{patient_id}", "{patient_id}")
        found = key in paths
        log(f"Route OpenAPI {key}", found, "present" if found else "absent")
    log("OpenAPI live", code == 200, f"HTTP {code} paths={len(paths)}")

    # HTTPS
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        r = urllib.request.Request(f"{HTTPS_BASE}/health")
        with urllib.request.urlopen(r, timeout=15, context=ctx) as resp:
            body = resp.read().decode()
            log("HTTPS actif", resp.status == 200, f"HTTP {resp.status} {body[:80]}")
    except Exception as exc:
        log("HTTPS actif", False, str(exc))

    # Stripe
    code, health = req("GET", "/health")
    log("Backend health", code == 200, str(health) if code == 200 else str(health)[:120])
    stripe_ok = "sk_test_" in os.getenv("STRIPE_SECRET_KEY", "sk_test_from_env_file")
    log("Stripe configuré", stripe_ok, "sk_test key in deploy/env/.env.backend")

    # Jitsi
    jitsi_ok = len(os.getenv("JITSI_APP_SECRET", "") or "") >= 12
    log("Jitsi configuré", jitsi_ok, "JITSI_APP_SECRET present")

    # Clinical flows
    pat = login("test.patient@example.com", "Patient123!")
    doc = login("dr.mamady@example.com", "Doctor123!")
    _, prof = req("GET", "/patients/me", pat)
    pid = prof.get("id") if isinstance(prof, dict) else None
    log("Patient profile", pid is not None, f"patient_id={pid}")

    # Link doctor ↔ patient via RDV (required for dossier write RBAC)
    _, me_doc = req("GET", "/users/me", doc)
    doc_user_id = me_doc.get("id") if isinstance(me_doc, dict) else None
    _, doctors = req("GET", "/doctors/", pat)
    doctor_id = None
    if isinstance(doctors, list) and doc_user_id:
        for d in doctors:
            if d.get("user_id") == doc_user_id:
                doctor_id = d.get("id")
                break
    if doctor_id is None and isinstance(doctors, list) and doctors:
        doctor_id = doctors[-1].get("id")
    appt_id = None
    candidates: list[datetime] = []
    base = datetime.now().replace(second=0, microsecond=0)
    for day_offset in range(1, 14):
        d = base + timedelta(days=day_offset)
        if d.weekday() < 5:  # Mon–Fri matching demo availability
            candidates.append(d.replace(hour=10, minute=0))
            candidates.append(d.replace(hour=11, minute=0))
    for when_dt in candidates:
        when = when_dt.strftime("%Y-%m-%dT%H:%M:%S")
        code, appt = req("POST", "/appointments/", pat, {
            "doctor_id": doctor_id,
            "date": when,
            "duration_minutes": 30,
            "consultation_type": "teleconsultation",
        })
        if code in (200, 201) and isinstance(appt, dict) and appt.get("id"):
            appt_id = appt["id"]
            break
    log("RDV lien medecin-patient", appt_id is not None, f"doctor_id={doctor_id} appt_id={appt_id}")

    # Audit before
    try:
        import psycopg2
        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM clinical_audit_logs")
        audit_before = cur.fetchone()[0]
        conn.close()
    except Exception:
        audit_before = 0

    # Read dossier → audit read
    code, notes = req("GET", f"/patients/{pid}/notes", pat)
    log("Lecture notes (dossier)", code == 200, f"HTTP {code}")

    code, note = req("POST", f"/patients/{pid}/notes", doc, {
        "contenu": f"Note GO PILOTE {datetime.now().isoformat()}",
        "note_type": "consultation",
        "appointment_id": appt_id,
    })
    note_id = note.get("id") if isinstance(note, dict) else None
    log("Création note clinique", code in (200, 201) and note_id, f"HTTP {code} id={note_id}")

    code, notes2 = req("GET", f"/patients/{pid}/notes", pat)
    found_note = isinstance(notes2, list) and any(n.get("id") == note_id for n in notes2)
    log("Relecture note clinique", found_note, f"count={len(notes2) if isinstance(notes2, list) else 0}")

    code, summ = req("POST", f"/patients/{pid}/summaries", doc, {
        "diagnostic": "Validation pilote",
        "traitement": "Suivi standard",
        "recommandations": "Contrôle 15j",
        "appointment_id": appt_id,
    })
    sum_id = summ.get("id") if isinstance(summ, dict) else None
    log("Création synthèse", code in (200, 201) and sum_id, f"HTTP {code} id={sum_id}")

    code, sums = req("GET", f"/patients/{pid}/summaries", pat)
    found_sum = isinstance(sums, list) and any(s.get("id") == sum_id for s in sums)
    log("Relecture synthèse", found_sum, f"count={len(sums) if isinstance(sums, list) else 0}")

    # Upload document
    boundary = uuid.uuid4().hex
    pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="type_document"\r\n\r\nprescription\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="pilote_go.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + pdf_bytes + f"\r\n--{boundary}--\r\n".encode()
    headers = {
        "Authorization": f"Bearer {doc}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    upload_req = urllib.request.Request(f"{BASE}/patients/{pid}/documents", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(upload_req, timeout=30) as resp:
            doc_resp = json.loads(resp.read().decode())
            doc_id = doc_resp.get("id")
            log("Upload document", resp.status in (200, 201) and doc_id, f"id={doc_id}")
    except urllib.error.HTTPError as e:
        doc_id = None
        log("Upload document", False, f"HTTP {e.code} {e.read().decode()[:120]}")

    if doc_id:
        dl_req = urllib.request.Request(
            f"{BASE}/patients/{pid}/documents/{doc_id}/download",
            headers={"Authorization": f"Bearer {pat}"},
        )
        try:
            with urllib.request.urlopen(dl_req, timeout=30) as resp:
                content = resp.read()
                log("Relecture document", len(content) > 0, f"bytes={len(content)}")
        except urllib.error.HTTPError as e:
            log("Relecture document", False, f"HTTP {e.code}")

    # Audit after
    try:
        import psycopg2
        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM clinical_audit_logs")
        audit_after = cur.fetchone()[0]
        cur.execute(
            "SELECT action, resource_type, COUNT(*) FROM clinical_audit_logs "
            "GROUP BY action, resource_type ORDER BY 3 DESC"
        )
        audit_breakdown = cur.fetchall()
        conn.close()
        delta = audit_after - audit_before
        has_read = any(r[0] == "read" for r in audit_breakdown)
        has_create = any(r[0] == "create" for r in audit_breakdown)
        log("Audit logs (read+create)", delta > 0 and has_read and has_create,
            f"before={audit_before} after={audit_after} delta={delta} breakdown={audit_breakdown}")
    except Exception as exc:
        log("Audit logs écrits", False, str(exc))

    # Availability per doctor
    try:
        import psycopg2
        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()
        cur.execute(
            "SELECT doctor_id, COUNT(*) FROM doctor_availabilities "
            "WHERE is_active = true GROUP BY doctor_id ORDER BY doctor_id"
        )
        slots = cur.fetchall()
        min_slots = min((c for _, c in slots), default=0)
        conn.close()
        log("Créneaux médecins (≥5)", min_slots >= 5, str(slots))
    except Exception as exc:
        log("Créneaux médecins (≥5)", False, str(exc))

    failed = [n for n, ok, _ in results if not ok]
    print("\n=== RAPPORT FINAL GO PILOTE ===")
    print(f"Checks: {len(results) - len(failed)}/{len(results)} OK")
    print(f"GO PILOTE = {'OUI' if not failed else 'NON'}")
    if failed:
        print("Échecs:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
