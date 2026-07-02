#!/usr/bin/env python3
"""Local browser E2E: Reception -> Admission -> Nurse -> Doctor."""

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

FRONTEND = os.getenv("NURSE_E2E_FRONTEND", "http://127.0.0.1:5181")
BACKEND = os.getenv("NURSE_E2E_BACKEND", "http://127.0.0.1:8023")

CREDS = {
    "reception": ("reception@pilot.local", "ReceptionPilot1!"),
    "nurse": ("admin@pilot.local", "AdminPilot1!"),
    "doctor": ("dr.pilot@pilot.local", "DoctorPilot1!"),
}

RUN = uuid.uuid4().hex[:6]
PATIENT = {
    "last_name": f"NURSE{RUN}",
    "first_name": "Local",
    "phone": f"626{uuid.uuid4().hex[:7]}",
    "dob": "1990-04-20",
}
NURSE_COMPLAINT = f"Douleur abdominale E2E {RUN}"
OUT = Path(__file__).resolve().parents[2] / "docs" / "LOCAL_NURSE_E2E.json"


def login(email: str, password: str) -> str:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": email, "password": password}, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def api(method: str, path: str, token: str, **kwargs):
    return httpx.request(method, f"{BACKEND}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=90, **kwargs)


def login_ui(page, email: str, password: str, expect_path: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload()
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=60000)
    page.goto(f"{FRONTEND}{expect_path}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=60000)


def resolve_doctor_id(token: str) -> int:
    me = api("GET", "/auth/me", token).json()
    doctor_id = me.get("doctor_id")
    if not doctor_id:
        raise RuntimeError("Doctor account has no doctor_id")
    return int(doctor_id)


def unique_appointment_slot() -> datetime:
    offset_minutes = uuid.uuid4().int % (24 * 60 - 60) + 60
    return (datetime.now() + timedelta(days=2, minutes=offset_minutes)).replace(second=0, microsecond=0)


def click_tab(page, label: str) -> None:
    page.locator(f"nav.reception-his-tabs button:has-text('{label}')").click()
    time.sleep(0.4)


def nurse_search_and_select(page, query: str) -> None:
    page.locator("#nurse-patient-search").fill(query)
    page.locator('button:has-text("Rechercher")').click()
    page.locator(".reception-his-search-results button").first.wait_for(timeout=20000)
    page.locator(".reception-his-search-results button").first.click()
    page.wait_for_selector('fieldset:has(legend:has-text("Signes vitaux"))', timeout=20000)


def main() -> int:
    report: dict[str, list] = {"reception": [], "admission": [], "nurse": [], "doctor": []}
    patient_id = None
    patient_number = ""
    appointment_id = None

    recep_token = login(*CREDS["reception"])
    doctor_token = login(*CREDS["doctor"])
    doctor_id = resolve_doctor_id(doctor_token)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        try:
            login_ui(page, *CREDS["reception"], "/clinical/reception")
            click_tab(page, "Enregistrement")
            page.get_by_role("textbox", name=re.compile(r"Nom \*")).fill(PATIENT["last_name"])
            page.get_by_role("textbox", name=re.compile(r"Prénom \*")).fill(PATIENT["first_name"])
            page.locator('label:has-text("Date naissance") input').fill(PATIENT["dob"])
            page.get_by_role("textbox", name=re.compile(r"Adresse \*")).fill("Kobaya local E2E")
            page.get_by_role("textbox", name=re.compile(r"Tél. principal \*")).fill(PATIENT["phone"])
            page.get_by_role("textbox", name=re.compile(r"Nom du contact \*")).fill("Contact local")
            page.locator('fieldset:has(legend:has-text("Personne")) select').select_option("Père")
            page.locator('fieldset:has(legend:has-text("Personne")) label:has-text("Téléphone") input').fill(f"627{RUN[:6]}")
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
            report["reception"].append(("Workflow", False, str(exc)[:200]))

        browser.close()

        search = api("GET", "/clinical/reception/his/patients/search", recep_token, params={"q": PATIENT["last_name"]}).json()
        if search:
            patient_id = search[0]["id"]
            patient_number = patient_number or search[0].get("patient_number", "")

        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            login_ui(page, *CREDS["nurse"], "/clinical/nurse")
            report["nurse"].append(("Dashboard route", "/clinical/nurse" in page.url, page.url))
            nurse_search_and_select(page, patient_number or PATIENT["last_name"])
            vitals = page.locator('fieldset:has(legend:has-text("Signes vitaux")) input')
            vitals.nth(0).fill("38.1")
            vitals.nth(1).fill("120")
            vitals.nth(2).fill("80")
            vitals.nth(3).fill("88")
            vitals.nth(4).fill("18")
            vitals.nth(5).fill("170")
            vitals.nth(6).fill("70")
            page.locator('fieldset:has(legend:has-text("Motif de consultation")) textarea').fill(NURSE_COMPLAINT)
            page.get_by_label("Allergies").fill("Latex")
            page.locator('fieldset:has(legend:has-text("Notes infirmières")) textarea').fill(f"Note {RUN}")
            page.click('button:has-text("Enregistrer l\'évaluation")')
            page.wait_for_selector("text=Évaluation infirmière enregistrée", timeout=60000)
            bmi = page.locator('label:has-text("IMC") .reception-his-auto-display').inner_text()
            report["nurse"].append(("Save assessment", True, ""))
            report["nurse"].append(("BMI calculated", bmi.strip() not in ("", "—"), bmi))
        except Exception as exc:
            report["nurse"].append(("Nurse browser workflow", False, str(exc)[:200]))
        browser.close()

        if patient_id and doctor_id:
            slot = unique_appointment_slot()
            appt_resp = api(
                "POST",
                "/clinical/reception/appointments",
                recep_token,
                json={"patient_id": patient_id, "doctor_id": doctor_id, "date": slot.isoformat(), "duration_minutes": 30},
            )
            if appt_resp.status_code not in (200, 201):
                report["doctor"].append(("Create appointment", False, appt_resp.text[:200]))
            else:
                appointment_id = appt_resp.json()["id"]
                checkin = api("POST", f"/clinical/reception/appointments/{appointment_id}/check-in", recep_token)
                report["doctor"].append(("Check-in appointment", checkin.status_code in (200, 201), checkin.text[:120]))

        if appointment_id:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            try:
                login_ui(page, *CREDS["doctor"], "/clinical/doctor")
                page.click('button:has-text("Démarrer consultation")')
                page.wait_for_selector(".nurse-doctor-panel", timeout=20000)
                panel = page.locator(".nurse-doctor-panel").inner_text()
                report["doctor"].append(("Doctor UI nurse panel", "Évaluation infirmière" in panel, panel[:100]))
                report["doctor"].append(("Doctor UI shows complaint", NURSE_COMPLAINT[:15] in panel, ""))
                report["doctor"].append(("Doctor UI shows allergies", "Latex" in panel, ""))
            except Exception as exc:
                report["doctor"].append(("Doctor browser workflow", False, str(exc)[:200]))
            browser.close()

            consult = api(
                "GET",
                f"/clinical/consultations?appointment_id={appointment_id}",
                doctor_token,
            )
            if consult.status_code == 200 and consult.json():
                data = consult.json()[0] if isinstance(consult.json(), list) else consult.json()
            else:
                data = api(
                    "POST",
                    "/clinical/consultations",
                    doctor_token,
                    json={"appointment_id": appointment_id, "chief_complaint": "placeholder"},
                ).json()
            report["doctor"].append(("API nurse complaint synced", NURSE_COMPLAINT in (data.get("chief_complaint") or ""), data.get("chief_complaint", "")))
            report["doctor"].append(("API allergies in history", "Latex" in (data.get("history") or ""), ""))

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    ok = all(item[1] for section in report.values() for item in section)
    print("Overall:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
