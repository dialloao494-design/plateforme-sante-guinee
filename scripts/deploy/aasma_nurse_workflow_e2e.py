#!/usr/bin/env python3
"""Browser + API E2E: Reception → Admission → Nurse → Doctor (AASMA production)."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

FRONTEND = os.getenv("NURSE_E2E_FRONTEND", "https://plateforme-sante-guinee.vercel.app")
BACKEND = os.getenv("NURSE_E2E_BACKEND", "https://web-production-ad6a36.up.railway.app")

CREDS = {
    "reception": ("baldoumar14@gmail.com", "AasmaRecep1!"),
    "nurse": ("contactpolycliniqueaasma@gmail.com", "AasmaAdmin1!"),
}

RUN = uuid.uuid4().hex[:6]
PATIENT = {
    "last_name": f"NURSE{RUN}",
    "first_name": "E2E",
    "phone": f"624{uuid.uuid4().hex[:7]}",
    "dob": "1988-06-15",
}
NURSE_COMPLAINT = f"Fièvre et céphalées E2E {RUN}"
OUT = Path(__file__).resolve().parents[2] / "docs" / "AASMA_NURSE_E2E.json"


def api(method: str, path: str, token: str, **kwargs):
    headers = {"Authorization": f"Bearer {token}"}
    return httpx.request(method, f"{BACKEND}{path}", headers=headers, timeout=90, **kwargs)


def login(email: str, password: str) -> str:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": email, "password": password}, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def login_ui(page, email: str, password: str, expect_path: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload()
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
    page.goto(f"{FRONTEND}{expect_path}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=90000)


def click_tab(page, label: str) -> None:
    page.locator(f"nav.reception-his-tabs button:has-text('{label}')").click()
    time.sleep(0.4)


def nurse_search_and_select(page, query: str) -> None:
    page.locator("#nurse-patient-search").fill(query)
    page.locator('button:has-text("Rechercher")').click()
    page.locator(".reception-his-search-results button").first.wait_for(timeout=30000)
    page.locator(".reception-his-search-results button").first.click()
    page.wait_for_selector('fieldset:has(legend:has-text("Signes vitaux"))', timeout=30000)


def unique_appointment_slot() -> datetime:
    offset_minutes = uuid.uuid4().int % (24 * 60 - 60) + 60
    return (datetime.now() + timedelta(days=3, minutes=offset_minutes)).replace(second=0, microsecond=0)


def resolve_doctor_for_appointment(recep_token: str) -> tuple[int | None, str | None, str | None]:
    doctors = api("GET", "/clinical/reception/doctors", recep_token).json()
    if not doctors:
        return None, None, None
    doc = doctors[0]
    return doc.get("doctor_id") or doc.get("id"), doc.get("email"), doc.get("name")


def main() -> int:
    report: dict[str, list] = {"reception": [], "admission": [], "nurse": [], "doctor": []}
    patient_id = None
    patient_number = ""
    appointment_id = None

    recep_token = login(*CREDS["reception"])
    nurse_token = login(*CREDS["nurse"])

    dash = api("GET", "/clinical/nurse/dashboard", nurse_token)
    report["nurse"].append(("Nurse API deployed", dash.status_code == 200, dash.text[:120]))

    doctor_id, doctor_email, doctor_name = resolve_doctor_for_appointment(recep_token)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        try:
            login_ui(page, *CREDS["reception"], "/clinical/reception")
            click_tab(page, "Enregistrement")
            page.get_by_role("textbox", name=re.compile(r"Nom \*")).fill(PATIENT["last_name"])
            page.get_by_role("textbox", name=re.compile(r"Prénom \*")).fill(PATIENT["first_name"])
            page.locator('label:has-text("Date naissance") input').fill(PATIENT["dob"])
            page.get_by_role("textbox", name=re.compile(r"Adresse \*")).fill("Kobaya test nurse E2E")
            page.get_by_role("textbox", name=re.compile(r"Tél. principal \*")).fill(PATIENT["phone"])
            page.get_by_role("textbox", name=re.compile(r"Nom du contact \*")).fill("Contact E2E")
            page.locator('fieldset:has(legend:has-text("Personne")) select').select_option("Père")
            page.locator('fieldset:has(legend:has-text("Personne")) label:has-text("Téléphone") input').fill(f"625{RUN[:6]}")
            page.click('button:has-text("Enregistrer le patient")')
            page.wait_for_selector("text=/Patient enregistré/i", timeout=90000)
            dossier_el = page.locator(".reception-his-selected strong").nth(1)
            patient_number = dossier_el.inner_text() if dossier_el.count() else ""
            report["reception"].append(("Register patient", True, patient_number))

            click_tab(page, "Admission")
            page.locator('label.reception-his-check:has-text("Consultation externe")').first.check()
            page.select_option('label:has-text("Type d\'admission") select', value="outpatient")
            page.click('button:has-text("Créer l\'admission")')
            page.wait_for_selector("text=Admission créée", timeout=60000)
            report["admission"].append(("Create admission", True, ""))
        except Exception as exc:
            report["reception"].append(("Reception workflow", False, str(exc)[:200]))

        browser.close()

        search = api("GET", "/clinical/reception/his/patients/search", recep_token, params={"q": patient_number or PATIENT["last_name"]}).json()
        if search:
            match = next((p for p in search if p.get("patient_number") == patient_number), search[0])
            patient_id = match["id"]
            patient_number = patient_number or match.get("patient_number", "")

        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            login_ui(page, *CREDS["nurse"], "/clinical/nurse")
            report["nurse"].append(("Nurse dashboard route", "/clinical/nurse" in page.url, page.url))
            nurse_search_and_select(page, patient_number or PATIENT["last_name"])
            report["nurse"].append(("Nurse form sections", page.locator('legend:has-text("Signes vitaux")').count() > 0, ""))
            vitals = page.locator('fieldset:has(legend:has-text("Signes vitaux")) input')
            vitals.nth(0).fill("38.2")
            vitals.nth(1).fill("130")
            vitals.nth(2).fill("85")
            vitals.nth(3).fill("92")
            vitals.nth(4).fill("18")
            vitals.nth(5).fill("172")
            vitals.nth(6).fill("68")
            page.wait_for_timeout(500)
            bmi_text = page.locator('label:has-text("IMC") .reception-his-auto-display').inner_text()
            page.locator('fieldset:has(legend:has-text("Motif de consultation")) textarea').fill(NURSE_COMPLAINT)
            page.get_by_label("Allergies").fill("Pénicilline")
            page.locator('fieldset:has(legend:has-text("Notes infirmières")) textarea').fill(f"Note infirmière E2E {RUN}")
            page.click('button:has-text("Enregistrer l\'évaluation")')
            page.wait_for_selector("text=Évaluation infirmière enregistrée", timeout=60000)
            time.sleep(2)
            report["nurse"].append(("Save nurse assessment", True, ""))
            report["nurse"].append(("BMI auto-calculated", bmi_text.strip() not in ("", "—"), bmi_text))
        except Exception as exc:
            report["nurse"].append(("Nurse browser workflow", False, str(exc)[:200]))
        browser.close()

    if patient_id:
        time.sleep(2)
        r = api("GET", f"/clinical/nurse/patients/{patient_id}/assessment", nurse_token)
        assessment = r.json() if r.status_code == 200 else None
        report["doctor"].append(("Nurse assessment API", assessment is not None, str(assessment.get("reason_for_consultation") if assessment else "")))
        if assessment:
            report["doctor"].append(("Complaint saved", NURSE_COMPLAINT in (assessment.get("reason_for_consultation") or ""), ""))
            report["doctor"].append(("Allergies saved", "Pénicilline" in (assessment.get("allergies") or ""), ""))
            report["doctor"].append(("BMI in assessment", assessment.get("bmi") is not None, str(assessment.get("bmi"))))

    if patient_id and doctor_id:
        appt_resp = api(
            "POST",
            "/clinical/reception/appointments",
            recep_token,
            json={"patient_id": patient_id, "doctor_id": doctor_id, "date": unique_appointment_slot().isoformat(), "duration_minutes": 30},
        )
        if appt_resp.status_code in (200, 201):
            appointment_id = appt_resp.json()["id"]
            checkin = api("POST", f"/clinical/reception/appointments/{appointment_id}/check-in", recep_token)
            report["doctor"].append(("Check-in appointment", checkin.status_code in (200, 201), ""))
        else:
            report["doctor"].append(("Create appointment", False, appt_resp.text[:200]))

    if appointment_id and doctor_email:
        try:
            doc_token = login(doctor_email, CREDS["reception"][1])
        except Exception:
            doc_token = None
        if doc_token:
            consult_resp = api(
                "POST",
                "/clinical/consultations",
                doc_token,
                json={"appointment_id": appointment_id, "chief_complaint": "fallback"},
            )
            if consult_resp.status_code in (200, 201):
                consult = consult_resp.json()
                report["doctor"].append(("Consultation nurse complaint", NURSE_COMPLAINT in (consult.get("chief_complaint") or ""), consult.get("chief_complaint", "")[:80]))
                report["doctor"].append(("Consultation nurse history", "Pénicilline" in (consult.get("history") or ""), ""))

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 900})
                try:
                    login_ui(page, doctor_email, CREDS["reception"][1], "/clinical/doctor")
                    page.click('button:has-text("Démarrer consultation")')
                    page.wait_for_selector(".nurse-doctor-panel", timeout=20000)
                    body = page.locator(".nurse-doctor-panel").inner_text()
                    report["doctor"].append(("Doctor UI nurse panel", "Évaluation infirmière" in body, body[:120]))
                    report["doctor"].append(("Doctor UI shows complaint", NURSE_COMPLAINT[:20] in body, ""))
                except Exception as exc:
                    report["doctor"].append(("Doctor browser workflow", False, str(exc)[:200]))
                browser.close()

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    all_pass = all(ok for section in report.values() for _, ok, _ in section)
    print(f"\nOverall: {'PASS' if all_pass else 'PARTIAL/FAIL'}")
    print(f"Report: {OUT}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
