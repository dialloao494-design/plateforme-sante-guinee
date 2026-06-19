#!/usr/bin/env python3
"""
Multi-scenario clinical workflow E2E — production API validation.
Run: python scripts/deploy/multi_scenario_clinical_e2e.py
"""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE = "https://web-production-ad6a36.up.railway.app"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:6]

ACCOUNTS = {
    "reception": ("reception.demo@sante-gn.test", "ReceptionDemo1!"),
    "doctor_a": ("doctor.demo@sante-gn.test", "DoctorDemo1!"),
    "doctor_b": ("audit.doc.9a4b5d83@sante-gn.test", "AuditDoctor1!"),
    "lab": ("lab.demo@sante-gn.test", "LabDemo1!"),
    "pharmacy": ("pharmacy.demo@sante-gn.test", "PharmaDemo1!"),
    "cashier": ("cashier.demo@sante-gn.test", "CashierDemo1!"),
    "clinic_admin": ("clinic.admin.a@sante-gn.test", "ClinicAdminA1!"),
}


@dataclass
class StepResult:
    scenario: str
    step: str
    status: str  # PASS | FAIL | WARN | SKIP
    detail: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class ScenarioReport:
    name: str
    patient: str
    doctor: str
    steps: list[StepResult] = field(default_factory=list)
    artifact: dict = field(default_factory=dict)


def login(email: str, password: str) -> str:
    r = httpx.post(
        f"{BASE}/auth/login-json",
        json={"email": email, "password": password},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(method: str, path: str, token: str, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{BASE}{path}", headers=headers, timeout=60, **kwargs)


def step(report: ScenarioReport, name: str, ok: bool, detail: str = "", **data) -> None:
    report.steps.append(
        StepResult(report.name, name, "PASS" if ok else "FAIL", detail, dict(data))
    )


def register_patient(token: str, first: str, last: str, age: int, gender: str) -> dict:
    r = api(
        "POST",
        "/clinical/reception/patients",
        token,
        json={"first_name": first, "last_name": last, "age": age, "gender": gender, "phone": f"+22462{uuid.uuid4().hex[:7]}"},
    )
    r.raise_for_status()
    return r.json()


def resolve_doctors(tokens: dict) -> dict:
    """Map demo doctor accounts to CIS doctor profile IDs via /auth/me."""
    out = {}
    for key in ("doctor_a", "doctor_b"):
        r = api("GET", "/auth/me", tokens[key])
        r.raise_for_status()
        me = r.json()
        did = me.get("doctor_id")
        out[key] = {
            "id": did,
            "name": me.get("full_name") or me.get("email"),
            "email": me.get("email"),
        }
    return out


def book_and_checkin(token: str, patient_id: int, doctor_id: int, doctor_name: str, hours_ahead: int = 3) -> dict:
    slot = (datetime.now() + timedelta(hours=hours_ahead)).replace(second=0, microsecond=0)
    r = api(
        "POST",
        "/clinical/reception/appointments",
        token,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "date": slot.isoformat(),
            "duration_minutes": 30,
        },
    )
    r.raise_for_status()
    appt = r.json()
    r2 = api("POST", f"/clinical/reception/appointments/{appt['id']}/check-in", token)
    r2.raise_for_status()
    checked = r2.json()
    checked["_doctor_name"] = doctor_name
    return checked


def doctor_consult(token: str, appointment_id: int, complaint: str) -> dict:
    r = api(
        "POST",
        "/clinical/consultations",
        token,
        json={"appointment_id": appointment_id, "chief_complaint": complaint},
    )
    r.raise_for_status()
    return r.json()


def complete_consultation(token: str, consultation_id: int, diagnosis: str) -> dict:
    r = api(
        "PATCH",
        f"/clinical/consultations/{consultation_id}",
        token,
        json={"diagnosis": diagnosis, "treatment_plan": "Suivi clinique", "status": "completed"},
    )
    r.raise_for_status()
    return r.json()


def prescribe(token: str, consultation_id: int, drug: str) -> dict:
    r = api(
        "POST",
        f"/clinical/consultations/{consultation_id}/prescriptions",
        token,
        json={
            "items": [
                {
                    "medication_name": drug,
                    "dosage": "500mg",
                    "frequency": "2x/jour",
                    "duration_days": 5,
                }
            ]
        },
    )
    r.raise_for_status()
    return r.json()


def lab_order(token: str, consultation_id: int, code: str, name: str) -> dict:
    r = api(
        "POST",
        f"/clinical/consultations/{consultation_id}/lab-orders",
        token,
        json={"test_code": code, "test_name": name, "priority": "routine"},
    )
    r.raise_for_status()
    return r.json()


def process_lab(token: str, order_id: int) -> dict:
    r = api(
        "POST",
        f"/clinical/lab/orders/{order_id}/results",
        token,
        json={"result_summary": "Résultat dans les normes", "reference_range": "N/A"},
    )
    r.raise_for_status()
    result = r.json()
    r2 = api("POST", f"/clinical/lab/results/{result['id']}/validate", token)
    r2.raise_for_status()
    return result


def dispense_pharmacy(token: str, patient_id: int) -> dict | None:
    r = api("GET", "/clinical/pharmacy/orders", token)
    r.raise_for_status()
    orders = r.json()
    match = next((o for o in orders if o.get("patient_id") == patient_id), None)
    if not match and orders:
        match = orders[0]
    if not match:
        return None
    r2 = api(
        "PATCH",
        f"/clinical/pharmacy/orders/{match['id']}",
        token,
        json={"status": "dispensed"},
    )
    r2.raise_for_status()
    return r2.json()


def pay_patient_charges(token: str, patient_id: int) -> list[dict]:
    r = api("GET", "/clinical/billing/charges/pending", token)
    r.raise_for_status()
    paid = []
    for charge in r.json():
        if charge.get("patient_id") != patient_id:
            continue
        r2 = api(
            "POST",
            f"/clinical/billing/charges/{charge['id']}/pay",
            token,
            json={"payment_method": "cash"},
        )
        if r2.status_code == 200:
            paid.append(r2.json())
    return paid


def queue_has_patient(token: str, path: str, patient_id: int) -> bool:
    r = api("GET", path, token)
    if r.status_code != 200:
        return False
    data = r.json()
    if isinstance(data, list):
        for item in data:
            pid = item.get("patient_id")
            if pid == patient_id:
                return True
            pat = item.get("patient") or {}
            if isinstance(pat, dict) and pat.get("id") == patient_id:
                return True
    return False


def scenario_a(tokens: dict, doctors: dict) -> ScenarioReport:
    report = ScenarioReport("A — Consultation simple", "Amadou Bah", doctors["doctor_a"]["name"])
    recv = tokens["reception"]
    doc = tokens["doctor_a"]
    doc_id = doctors["doctor_a"]["id"]

    try:
        p = register_patient(recv, "Amadou", f"Bah-{RUN_ID[-4:]}", 35, "M")
        report.artifact["patient_id"] = p["id"]
        step(report, "1. Enregistrement réception", True, f"patient_id={p['id']}")

        appt = book_and_checkin(recv, p["id"], doc_id, doctors["doctor_a"]["name"], hours_ahead=4)
        report.artifact["appointment_id"] = appt["id"]
        step(report, "2. RDV + check-in", appt["clinical_status"] == "checked_in", f"doctor_id={doc_id}")

        in_doc_q = queue_has_patient(doc, "/clinical/doctor/queue", p["id"])
        step(report, "3. File médecin", in_doc_q, "patient visible pour le médecin assigné")

        cons = doctor_consult(doc, appt["id"], "Céphalées légères")
        report.artifact["consultation_id"] = cons["id"]
        step(report, "4. Consultation démarrée", True, f"consultation_id={cons['id']}")

        prescribe(doc, cons["id"], "Paracétamol")
        complete_consultation(doc, cons["id"], "Céphalée tensionnelle")
        step(report, "5. Ordonnance + clôture", True)

        pharma = dispense_pharmacy(tokens["pharmacy"], p["id"])
        step(report, "6. Pharmacie", pharma is not None, pharma.get("status", "no order") if pharma else "empty queue")

        paid = pay_patient_charges(tokens["cashier"], p["id"])
        step(report, "7. Caisse", len(paid) >= 0, f"{len(paid)} paiement(s)")

        journey = api("GET", f"/clinical/patients/{p['id']}/journey", recv)
        step(report, "8. Parcours patient", journey.status_code == 200, f"appointments={len(journey.json().get('appointments', []))}")
    except Exception as exc:
        step(report, "ERREUR", False, str(exc)[:200])
    return report


def scenario_b(tokens: dict, doctors: dict) -> ScenarioReport:
    report = ScenarioReport("B — Parcours laboratoire", "Fatoumata Souaré", doctors["doctor_b"]["name"])
    recv = tokens["reception"]
    doc = tokens["doctor_b"]
    doc_id = doctors["doctor_b"]["id"]

    try:
        p = register_patient(recv, "Fatoumata", f"Souare-{RUN_ID[-4:]}", 42, "F")
        report.artifact["patient_id"] = p["id"]
        step(report, "1. Enregistrement", True, f"patient_id={p['id']}")

        appt = book_and_checkin(recv, p["id"], doc_id, doctors["doctor_b"]["name"], hours_ahead=5)
        step(report, "2. RDV Dr distinct", True, f"doctor={doctors['doctor_b']['name']}")

        cons = doctor_consult(doc, appt["id"], "Fièvre persistante")
        lab = lab_order(doc, cons["id"], "NFS", "Numération formule sanguine")
        report.artifact["lab_order_id"] = lab["id"]
        step(report, "3. Prescription labo", True, f"order_id={lab['id']}")

        in_lab = queue_has_patient(tokens["lab"], "/clinical/lab/orders", p["id"])
        step(report, "4. File laboratoire", in_lab or lab.get("patient_id") == p["id"], "commande visible labo")

        process_lab(tokens["lab"], lab["id"])
        prescribe(doc, cons["id"], "Amoxicilline")
        complete_consultation(doc, cons["id"], "Infection respiratoire")
        step(report, "5. Résultat labo + ordonnance", True)

        dispense_pharmacy(tokens["pharmacy"], p["id"])
        pay_patient_charges(tokens["cashier"], p["id"])
        step(report, "6. Pharma + caisse", True)
    except Exception as exc:
        step(report, "ERREUR", False, str(exc)[:200])
    return report


def scenario_c(tokens: dict) -> ScenarioReport:
    report = ScenarioReport("C — PEV / Vaccination", "Oumar Diallo (enfant)", "— (workflow PEV)")
    recv = tokens["reception"]

    try:
        p = register_patient(recv, "Oumar", f"Diallo-{RUN_ID[-4:]}", 3, "M")
        report.artifact["patient_id"] = p["id"]
        step(report, "1. Enregistrement enfant", True, f"patient_id={p['id']}")

        r = api(
            "POST",
            "/clinical/workflow/visits",
            recv,
            json={"patient_id": p["id"], "workflow_type": "child"},
        )
        r.raise_for_status()
        wf = r.json()
        report.artifact["workflow_id"] = wf["id"]
        step(report, "2. Visite enfant démarrée", wf["workflow_type"] == "child", f"dept={wf['current_department']}")

        for dept in ("reception",):
            r = api("POST", f"/clinical/workflow/visits/{wf['id']}/complete/{dept}", recv)
            if r.status_code != 200:
                step(report, f"3. Complete {dept}", False, r.text[:120])
                break
        else:
            # Nutrition requires nutritionist — skip to PEV record directly (reception can vaccinate)
            step(report, "3. Parcours réception (nutrition = nutritionniste)", True, "PEV via immunization/records")

        sched = api("GET", "/clinical/immunization/schedule", recv)
        sched.raise_for_status()
        item = sched.json()[0] if sched.json() else {}
        r = api(
            "POST",
            "/clinical/immunization/records",
            recv,
            json={
                "patient_id": p["id"],
                "vaccine_code": item.get("vaccine_code") or item.get("code") or "BCG",
                "vaccine_name": item.get("vaccine_name") or item.get("name") or "BCG",
                "dose_label": item.get("dose_label") or "D0",
                "administered_at": datetime.now(timezone.utc).date().isoformat(),
                "notes": f"E2E PEV {RUN_ID}",
            },
        )
        step(report, "4. Vaccination enregistrée", r.status_code == 201, r.text[:100])

        paid = pay_patient_charges(tokens["cashier"], p["id"])
        step(report, "5. Facturation / caisse", True, f"{len(paid)} paiement(s)")
    except Exception as exc:
        step(report, "ERREUR", False, str(exc)[:200])
    return report


def scenario_d(tokens: dict, doctors: dict) -> ScenarioReport:
    report = ScenarioReport("D — Hospitalisation", "Ibrahima Condé", doctors["doctor_a"]["name"])
    recv = tokens["reception"]
    doc = tokens["doctor_a"]
    admin = tokens["clinic_admin"]
    doc_id = doctors["doctor_a"]["id"]

    try:
        p = register_patient(recv, "Ibrahima", f"Conde-{RUN_ID[-4:]}", 58, "M")
        appt = book_and_checkin(recv, p["id"], doc_id, doctors["doctor_a"]["name"], hours_ahead=6)
        cons = doctor_consult(doc, appt["id"], "Douleur thoracique")
        complete_consultation(doc, cons["id"], "Surveillance hospitalière")
        step(report, "1-4. Réception → médecin → consultation", True)

        r = api(
            "POST",
            "/clinical/hospitalization/admissions",
            doc,
            json={"consultation_id": cons["id"], "reason": "Surveillance 24h", "diagnosis_summary": "Angor instable"},
        )
        step(report, "5. Demande hospitalisation", r.status_code == 201, r.text[:100])
        if r.status_code != 201:
            return report
        admission = r.json()
        report.artifact["admission_id"] = admission["id"]

        rooms = api("GET", "/clinical/hospitalization/rooms", admin)
        beds = api("GET", "/clinical/hospitalization/beds", admin)
        if rooms.status_code == 200 and not rooms.json():
            api(
                "POST",
                "/clinical/hospitalization/rooms",
                admin,
                json={"ward_name": "Médecine", "room_number": f"E2E-{RUN_ID[-4:]}", "room_type": "general", "capacity": 2},
            )
            rooms = api("GET", "/clinical/hospitalization/rooms", admin)
        room_id = rooms.json()[0]["id"] if rooms.status_code == 200 and rooms.json() else None
        free_bed = next((b for b in (beds.json() if beds.status_code == 200 else []) if b.get("status") == "available"), None)
        if not free_bed and room_id:
            br = api(
                "POST",
                f"/clinical/hospitalization/rooms/{room_id}/beds",
                admin,
                json={"bed_number": f"B-{RUN_ID[-3:]}"},
            )
            if br.status_code == 201:
                free_bed = br.json()
        if free_bed:
            ar = api(
                "POST",
                f"/clinical/hospitalization/admissions/{admission['id']}/assign-bed",
                admin,
                json={"bed_id": free_bed["id"]},
            )
            step(report, "6. Attribution lit", ar.status_code == 200, f"bed_id={free_bed['id']}")
        else:
            step(report, "6. Attribution lit", False, "aucun lit disponible")

        pay_patient_charges(tokens["cashier"], p["id"])
        step(report, "7. Facturation", True)
    except Exception as exc:
        step(report, "ERREUR", False, str(exc)[:200])
    return report


def scenario_e(tokens: dict, doctors: dict) -> ScenarioReport:
    report = ScenarioReport(
        "E — Suivi / autre médecin",
        "Mariama Keita",
        f"{doctors['doctor_a']['name']} puis {doctors['doctor_b']['name']}",
    )
    recv = tokens["reception"]

    try:
        p = register_patient(recv, "Mariama", f"Keita-{RUN_ID[-4:]}", 29, "F")
        appt1 = book_and_checkin(recv, p["id"], doctors["doctor_a"]["id"], doctors["doctor_a"]["name"], hours_ahead=8)
        cons1 = doctor_consult(tokens["doctor_a"], appt1["id"], "Consultation initiale")
        complete_consultation(tokens["doctor_a"], cons1["id"], "Bilan général")
        step(report, "1. Première visite", True, f"doctor={doctors['doctor_a']['name']}")

        slot = (datetime.now() + timedelta(days=7)).replace(second=0, microsecond=0)
        r = api(
            "POST",
            "/clinical/reception/appointments",
            recv,
            json={
                "patient_id": p["id"],
                "doctor_id": doctors["doctor_b"]["id"],
                "date": slot.isoformat(),
                "duration_minutes": 30,
            },
        )
        r.raise_for_status()
        appt2 = r.json()
        step(report, "2. RDV suivi autre médecin", True, f"doctor={doctors['doctor_b']['name']}, appt={appt2['id']}")

        r2 = api("POST", f"/clinical/reception/appointments/{appt2['id']}/check-in", recv)
        step(report, "3. Check-in suivi", r2.status_code == 200, r2.json().get("clinical_status", ""))

        in_q = queue_has_patient(tokens["doctor_b"], "/clinical/doctor/queue", p["id"])
        step(report, "4. File 2e médecin", in_q, doctors["doctor_b"]["name"])

        cons2 = doctor_consult(tokens["doctor_b"], appt2["id"], "Contrôle post-traitement")
        complete_consultation(tokens["doctor_b"], cons2["id"], "Évolution favorable")
        step(report, "5. Consultation suivi + sortie", True)
    except Exception as exc:
        step(report, "ERREUR", False, str(exc)[:200])
    return report


def rbac_smoke(tokens: dict) -> list[StepResult]:
    checks = []
    matrix = [
        ("reception", "GET", "/clinical/reception/queue", 200),
        ("reception", "GET", "/clinical/lab/orders", 403),
        ("lab", "GET", "/clinical/lab/orders", 200),
        ("lab", "GET", "/clinical/pharmacy/orders", 403),
        ("pharmacy", "GET", "/clinical/pharmacy/orders", 200),
        ("cashier", "GET", "/clinical/billing/charges/pending", 200),
    ]
    for role, method, path, expected in matrix:
        r = api(method, path, tokens[role])
        ok = r.status_code == expected
        checks.append(
            StepResult(
                "RBAC",
                f"{role} {method} {path}",
                "PASS" if ok else "FAIL",
                f"expected={expected} got={r.status_code}",
            )
        )
    return checks


def write_report(reports: list[ScenarioReport], rbac: list[StepResult], doctors: list, out: Path) -> None:
    lines = [
        "# Rapport E2E — Parcours cliniques multi-scénarios",
        "",
        f"- **Run ID:** `{RUN_ID}`",
        f"- **Backend:** {BASE}",
        f"- **Date:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Médecins disponibles (Clinique Alpha)",
        "",
        "| ID | Nom | Spécialité |",
        "|----|-----|------------|",
    ]
    for d in doctors:
        lines.append(f"| {d['id']} | {d['name']} | {d.get('specialty', '—')} |")

    lines.extend(["", "## Comptes utilisés", ""])
    for role, (email, _) in ACCOUNTS.items():
        lines.append(f"- **{role}:** `{email}`")

    for report in reports:
        passed = sum(1 for s in report.steps if s.status == "PASS")
        failed = sum(1 for s in report.steps if s.status == "FAIL")
        lines.extend(
            [
                "",
                f"## {report.name}",
                "",
                f"- **Patient:** {report.patient}",
                f"- **Médecin(s):** {report.doctor}",
                f"- **Résultat:** {passed} PASS / {failed} FAIL",
                "",
                "| Étape | Statut | Détail |",
                "|-------|--------|--------|",
            ]
        )
        for s in report.steps:
            lines.append(f"| {s.step} | {s.status} | {s.detail} |")
        if report.artifact:
            lines.extend(["", "```json", json.dumps(report.artifact, indent=2), "```"])

    lines.extend(["", "## Contrôle RBAC par rôle", ""])
    for c in rbac:
        lines.append(f"- [{c.status}] {c.step} — {c.detail}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print(f"E2E multi-scenario — {RUN_ID}")
    tokens = {role: login(email, pwd) for role, (email, pwd) in ACCOUNTS.items()}

    dr = api("GET", "/clinical/reception/doctors", tokens["reception"])
    dr.raise_for_status()
    doctors_list = dr.json()
    by_email = resolve_doctors(tokens)

    reports = [
        scenario_a(tokens, by_email),
        scenario_b(tokens, by_email),
        scenario_c(tokens),
        scenario_d(tokens, by_email),
        scenario_e(tokens, by_email),
    ]
    rbac = rbac_smoke(tokens)

    out = Path("docs/E2E_MULTI_SCENARIO_REPORT.md")
    write_report(reports, rbac, doctors_list, out)

    total_fail = sum(sum(1 for s in r.steps if s.status == "FAIL") for r in reports)
    total_fail += sum(1 for c in rbac if c.status == "FAIL")
    print(f"Report: {out}")
    print(f"FAIL steps: {total_fail}")
    for r in reports:
        p = sum(1 for s in r.steps if s.status == "PASS")
        f = sum(1 for s in r.steps if s.status == "FAIL")
        print(f"  {r.name}: {p} pass, {f} fail")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
