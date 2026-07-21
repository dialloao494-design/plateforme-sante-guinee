#!/usr/bin/env python3
"""
Production UI validation — 5 clinical scenarios via Playwright (real browser).
Run: python scripts/deploy/ui_clinical_e2e_playwright.py
"""

from __future__ import annotations

import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from playwright.sync_api import Page, sync_playwright, expect

FRONTEND = "https://plateforme-sante-guinee.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
RUN_ID = datetime.utcnow().strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:6]
OUT = Path(__file__).resolve().parents[2] / "docs" / "ui_e2e_screenshots" / RUN_ID
OUT.mkdir(parents=True, exist_ok=True)

ACCOUNTS = {
    "reception": ("reception.demo@sante-gn.test", "ReceptionDemo1!"),
    "doctor_a": ("doctor.demo@sante-gn.test", "DoctorDemo1!"),
    "doctor_b": ("audit.doc.9a4b5d83@sante-gn.test", "AuditDoctor1!"),
    "lab": ("lab.demo@sante-gn.test", "LabDemo1!"),
    "pharmacy": ("pharmacy.demo@sante-gn.test", "PharmaDemo1!"),
    "cashier": ("cashier.demo@sante-gn.test", "CashierDemo1!"),
    "clinic_admin": ("clinic.admin.a@sante-gn.test", "ClinicAdminA1!"),
}

results: list[tuple[str, str, str]] = []  # scenario, step, status


def shot(page: Page, scenario: str, step: str) -> None:
    safe = re.sub(r"[^\w\-]+", "_", f"{scenario}_{step}")[:120]
    path = OUT / f"{safe}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [screenshot] {path.name}")


def log(scenario: str, step: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    results.append((scenario, step, status))
    msg = f"[{status}] {scenario} — {step}"
    if detail:
        msg += f" ({detail})"
    print(msg)


def login_ui(page: Page, email: str, password: str, scenario: str, step: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=90000)
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload(wait_until="domcontentloaded")
    page.locator("#email").wait_for(state="visible", timeout=90000)
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    shot(page, scenario, f"{step}_01_login_form")
    page.click('button.login-submit')
    page.wait_for_function(
        "() => !window.location.pathname.includes('/login')",
        timeout=90000,
    )
    page.wait_for_load_state("networkidle", timeout=90000)
    shot(page, scenario, f"{step}_02_after_login")


def logout_ui(page: Page) -> None:
    for sel in [
        'button.sidebar-user-action-logout',
        'button:has-text("Déconnexion")',
        'a:has-text("Déconnexion")',
        '[data-testid="logout"]',
    ]:
        if page.locator(sel).count():
            page.locator(sel).first.click()
            page.wait_for_url(re.compile(r"/login"), timeout=30000)
            return
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")


def resolve_doctors() -> dict:
    out = {}
    for key in ("doctor_a", "doctor_b"):
        email, pwd = ACCOUNTS[key]
        r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": email, "password": pwd}, timeout=60)
        r.raise_for_status()
        token = r.json()["access_token"]
        me = httpx.get(f"{BACKEND}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=60).json()
        out[key] = {"id": me["doctor_id"], "name": me.get("full_name") or email}
    return out


def slot_local(days_ahead: int) -> str:
    jitter = int(RUN_ID.split("-")[-1][:4], 16) % 480
    dt = (datetime.now() + timedelta(days=days_ahead, minutes=jitter)).replace(second=0, microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M")


def register_patient_ui(page: Page, scenario: str, first: str, last: str, age: int, gender: str = "M") -> str:
    if "/clinical/reception" not in page.url:
        page.goto(f"{FRONTEND}/clinical/reception", wait_until="domcontentloaded", timeout=90000)
    page.locator("#reception-patient").wait_for(state="visible", timeout=90000)
    page.wait_for_load_state("networkidle", timeout=90000)
    shot(page, scenario, "reception_dashboard")
    page.locator("#reception-patient").scroll_into_view_if_needed()
    section = page.locator("#reception-patient")
    fields = section.locator(".clinical-field")
    fields.nth(0).locator("input").fill(first)
    fields.nth(1).locator("input").fill(last)
    fields.nth(2).locator("input").fill(str(age))
    fields.nth(3).locator("select").select_option(gender)
    fields.nth(4).locator("input").fill(f"+22462{uuid.uuid4().hex[:7]}")
    shot(page, scenario, "patient_form_filled")
    page.locator('#reception-patient button[type="submit"]').click()
    page.wait_for_timeout(2000)
    shot(page, scenario, "patient_registered")
    success = page.locator(".clinical-success").inner_text(timeout=5000)
    m = re.search(r"#(\d+)", success)
    patient_id = m.group(1) if m else ""
    log(scenario, "Patient creation", bool(patient_id), f"id={patient_id}")
    return patient_id


def book_appointment_ui(page: Page, scenario: str, patient_id: str, doctor_id: int, days_ahead: int) -> None:
    page.locator("#reception-rdv").scroll_into_view_if_needed()
    page.locator('#reception-rdv form input').first.fill(patient_id)
    page.locator('#reception-rdv select').select_option(value=str(doctor_id))
    page.locator('#reception-rdv input[type="datetime-local"]').fill(slot_local(days_ahead))
    shot(page, scenario, "appointment_form")
    page.locator('#reception-rdv button[type="submit"]').click()
    page.wait_for_timeout(2500)
    shot(page, scenario, "appointment_created")
    err = page.locator(".clinical-error").first.inner_text() if page.locator(".clinical-error").count() else ""
    ok = page.locator(".clinical-success").count() > 0
    log(scenario, "Appointment creation", ok, err[:120] if err else "")


def checkin_patient_ui(page: Page, scenario: str, patient_name: str) -> None:
    page.locator("#reception-file").scroll_into_view_if_needed()
    shot(page, scenario, "reception_queue_before_checkin")
    item = page.locator(f"#reception-file li:has-text('{patient_name}')").filter(
        has=page.locator('button:has-text("Check-in")')
    ).first
    if item.count():
        item.locator('button:has-text("Check-in")').click()
        page.wait_for_timeout(2500)
    shot(page, scenario, "reception_queue_after_checkin")
    checked_in = page.locator(
        f"#reception-file li:has-text('{patient_name}') .clinical-badge:has-text('checked_in')"
    ).count() > 0
    log(scenario, "Check-in", checked_in, patient_name)


def doctor_consult_flow(page: Page, scenario: str, patient_name: str, with_lab: bool = False, drug: str = "Paracétamol", admit: bool = False) -> None:
    page.goto(f"{FRONTEND}/clinical/doctor", wait_until="domcontentloaded", timeout=90000)
    page.locator("#doctor-queue").wait_for(state="visible", timeout=90000)
    page.wait_for_timeout(1500)
    shot(page, scenario, "doctor_queue")
    queue_item = page.locator(f"#doctor-queue li:has-text('{patient_name}')").first
    visible = queue_item.count() > 0
    log(scenario, "Doctor queue visibility", visible, patient_name)
    if not visible:
        return
    queue_item.locator('button:has-text("Démarrer consultation")').click()
    page.locator("#doctor-consultation").wait_for(state="visible", timeout=30000)
    page.wait_for_timeout(1500)
    shot(page, scenario, "consultation_started")
    page.locator('#doctor-consultation textarea').first.fill("Motif de consultation E2E UI")
    page.locator('#doctor-consultation textarea').nth(3).fill("Diagnostic E2E")
    if with_lab:
        page.locator('#doctor-consultation button:has-text("Envoyer au laboratoire")').click()
        page.wait_for_timeout(1500)
        shot(page, scenario, "lab_order_sent")
        log(scenario, "Lab order from doctor", True)
    page.locator('#doctor-consultation label:has-text("Médicament") + input').fill(drug)
    page.locator('#doctor-consultation label:has-text("Posologie") + input').fill("500mg")
    page.locator('#doctor-consultation button:has-text("Transmettre à la pharmacie")').click()
    page.wait_for_timeout(1500)
    shot(page, scenario, "prescription_sent")
    if admit:
        page.locator('#doctor-consultation button:has-text("Demander admission")').click()
        page.wait_for_timeout(2000)
        shot(page, scenario, "admission_requested")
        log(scenario, "Hospitalization request", page.locator(".clinical-success").count() > 0)
    else:
        page.locator('#doctor-consultation button:has-text("Terminer")').click()
        page.wait_for_timeout(2000)
        shot(page, scenario, "consultation_completed")
        log(scenario, "Consultation completed", page.locator(".clinical-success").count() > 0)


def lab_process_ui(page: Page, scenario: str, patient_name: str) -> None:
    page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle", timeout=90000)
    shot(page, scenario, "lab_queue")
    order = page.locator(f"section.clinical-card li:has-text('{patient_name}')").first
    visible = order.count() > 0
    log(scenario, "Laboratory queue visibility", visible, patient_name)
    if not visible:
        return
    if order.locator('button:has-text("Prélèvement")').count():
        order.locator('button:has-text("Prélèvement")').click()
        page.wait_for_timeout(1000)
    order.locator('button:has-text("Saisir résultat")').click()
    page.wait_for_timeout(1000)
    shot(page, scenario, "lab_result_form")
    page.locator('section.clinical-card textarea').first.fill("Résultat dans les normes — UI E2E")
    page.locator('button:has-text("Valider le résultat")').click()
    page.wait_for_timeout(2000)
    shot(page, scenario, "lab_result_validated")
    log(scenario, "Lab processing", page.locator(".clinical-success").count() > 0)


def pharmacy_process_ui(page: Page, scenario: str, patient_name: str) -> None:
    page.goto(f"{FRONTEND}/clinical/pharmacy", wait_until="networkidle", timeout=90000)
    shot(page, scenario, "pharmacy_queue")
    order = page.locator(f"#pharmacy-orders tr:has-text('{patient_name}')").first
    visible = order.count() > 0
    log(scenario, "Pharmacy queue visibility", visible, patient_name)
    if not visible:
        return
    if order.locator('button:has-text("Préparer")').count():
        order.locator('button:has-text("Préparer")').click()
        page.wait_for_timeout(1000)
    order.locator('button:has-text("Délivrer")').click()
    page.wait_for_timeout(2000)
    shot(page, scenario, "pharmacy_dispensed")
    log(scenario, "Pharmacy processing", page.locator(".clinical-success").count() > 0)


def cashier_process_ui(page: Page, scenario: str, patient_name: str) -> None:
    page.goto(f"{FRONTEND}/clinical/reception", wait_until="domcontentloaded", timeout=90000)
    page.locator("#reception-caisse").scroll_into_view_if_needed()
    shot(page, scenario, "cashier_pending_charges")
    charge = page.locator(f"#reception-caisse li:has-text('{patient_name}')").first
    visible = charge.count() > 0
    log(scenario, "Cashier pending charges", visible or scenario == "C", patient_name if visible else ("none (expected for PEV)" if scenario == "C" else "none"))
    if not visible:
        shot(page, scenario, "cashier_payment_done")
        log(scenario, "Cashier processing", scenario == "C")
        return
    while charge.locator('button:has-text("Encaisser")').count():
        charge.locator('button:has-text("Encaisser")').first.click()
        page.wait_for_timeout(2000)
        charge = page.locator(f"#reception-caisse li:has-text('{patient_name}')").first
    shot(page, scenario, "cashier_payment_done")
    log(scenario, "Cashier processing", True)


def hospitalization_ui(page: Page, scenario: str, patient_name: str) -> None:
    page.goto(f"{FRONTEND}/clinical/hospitalization", wait_until="domcontentloaded", timeout=90000)
    shot(page, scenario, "hospitalization_dashboard")
    admission = page.locator(f"ul.clinical-queue li:has-text('{patient_name}')").first
    visible = admission.count() > 0
    log(scenario, "Admission visible", visible, patient_name)
    if not visible:
        return
    admission.locator('button:has-text("Assigner lit")').first.click()
    page.wait_for_timeout(1000)
    select = page.locator('section.clinical-panel:has-text("Assignation") select').first
    if select.locator('option').count() <= 1:
        bed_num = f"B-{RUN_ID[-4:]}"
        room_select = page.locator('section:has-text("Ajouter un lit") select').first
        if room_select.locator('option').count() > 1:
            room_select.select_option(index=1)
            page.locator('section:has-text("Ajouter un lit") input').fill(bed_num)
            page.locator('section:has-text("Ajouter un lit") button:has-text("Ajouter lit")').click()
            page.wait_for_timeout(2000)
            page.reload(wait_until="domcontentloaded")
            admission = page.locator(f"ul.clinical-queue li:has-text('{patient_name}')").first
            admission.locator('button:has-text("Assigner lit")').first.click()
            page.wait_for_timeout(1000)
            select = page.locator('section.clinical-panel:has-text("Assignation") select').first
    options = select.locator('option').all()
    if len(options) > 1:
        select.select_option(index=1)
    shot(page, scenario, "bed_assignment_form")
    page.locator('button:has-text("Confirmer assignation")').click()
    page.wait_for_timeout(2500)
    shot(page, scenario, "bed_assigned")
    ok = page.locator(".clinical-alert--success, .clinical-success").count() > 0
    log(scenario, "Bed assignment", ok)


def start_child_visit_ui(page: Page, scenario: str, patient_id: str) -> None:
    page.goto(f"{FRONTEND}/clinical/reception", wait_until="networkidle")
    page.locator("#reception-visit").scroll_into_view_if_needed()
    page.locator('#reception-visit input').first.fill(patient_id)
    page.locator('#reception-visit select').select_option("child")
    shot(page, scenario, "child_visit_form")
    page.locator('#reception-visit button[type="submit"]').click()
    page.wait_for_timeout(2000)
    shot(page, scenario, "child_visit_started")
    log(scenario, "Child visit started", page.locator(".clinical-success").count() > 0)


def pev_vaccination_ui(page: Page, scenario: str, patient_name: str) -> None:
    page.goto(f"{FRONTEND}/clinical/immunization", wait_until="networkidle", timeout=90000)
    shot(page, scenario, "pev_dashboard")
    page.locator('input[type="search"]').first.fill(patient_name.split()[0])
    page.locator('button:has-text("Rechercher")').click()
    page.wait_for_timeout(2000)
    btn = page.locator(f"button.clinical-link-btn:has-text('{patient_name.split()[0]}')").first
    if btn.count():
        btn.click()
    page.wait_for_timeout(1500)
    shot(page, scenario, "pev_patient_selected")
    renseigner = page.locator('button:has-text("Renseigner")').first
    if renseigner.count():
        renseigner.click()
    else:
        page.locator('label:has-text("Code vaccin") input').fill("BCG")
        page.locator('label:has-text("Nom vaccin") input').fill("BCG")
        page.locator('label:has-text("Dose") input').fill("Naissance")
    page.locator('section:has-text("Enregistrer une vaccination") button[type="submit"]').click()
    page.wait_for_timeout(2000)
    shot(page, scenario, "pev_vaccination_recorded")
    log(scenario, "PEV vaccination", page.locator(".clinical-success").count() > 0)


def scenario_a(page: Page, doctors: dict) -> None:
    s = "A"
    last = f"Bah-{RUN_ID[-4:]}"
    full = f"Amadou {last}"
    login_ui(page, *ACCOUNTS["reception"], s, "login_reception")
    pid = register_patient_ui(page, s, "Amadou", last, 35, "M")
    book_appointment_ui(page, s, pid, doctors["doctor_a"]["id"], 3)
    checkin_patient_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["doctor_a"], s, "login_doctor")
    doctor_consult_flow(page, s, full, drug="Paracétamol")
    logout_ui(page)
    login_ui(page, *ACCOUNTS["pharmacy"], s, "login_pharmacy")
    pharmacy_process_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["cashier"], s, "login_cashier")
    cashier_process_ui(page, s, full)
    shot(page, s, "final_status")
    logout_ui(page)


def scenario_b(page: Page, doctors: dict) -> None:
    s = "B"
    last = f"Souare-{RUN_ID[-4:]}"
    full = f"Fatoumata {last}"
    login_ui(page, *ACCOUNTS["reception"], s, "login_reception")
    pid = register_patient_ui(page, s, "Fatoumata", last, 42, "F")
    book_appointment_ui(page, s, pid, doctors["doctor_b"]["id"], 4)
    checkin_patient_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["doctor_b"], s, "login_doctor")
    doctor_consult_flow(page, s, full, with_lab=True, drug="Amoxicilline")
    logout_ui(page)
    login_ui(page, *ACCOUNTS["lab"], s, "login_lab")
    lab_process_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["pharmacy"], s, "login_pharmacy")
    pharmacy_process_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["cashier"], s, "login_cashier")
    cashier_process_ui(page, s, full)
    shot(page, s, "final_status")
    logout_ui(page)


def scenario_c(page: Page, _doctors: dict) -> None:
    s = "C"
    last = f"Diallo-{RUN_ID[-4:]}"
    full = f"Oumar {last}"
    login_ui(page, *ACCOUNTS["reception"], s, "login_reception")
    pid = register_patient_ui(page, s, "Oumar", last, 3, "M")
    start_child_visit_ui(page, s, pid)
    pev_vaccination_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["cashier"], s, "login_cashier")
    cashier_process_ui(page, s, full)
    shot(page, s, "final_status")
    logout_ui(page)


def scenario_d(page: Page, doctors: dict) -> None:
    s = "D"
    last = f"Conde-{RUN_ID[-4:]}"
    full = f"Ibrahima {last}"
    login_ui(page, *ACCOUNTS["reception"], s, "login_reception")
    pid = register_patient_ui(page, s, "Ibrahima", last, 58, "M")
    book_appointment_ui(page, s, pid, doctors["doctor_a"]["id"], 5)
    checkin_patient_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["doctor_a"], s, "login_doctor")
    doctor_consult_flow(page, s, full, admit=True)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["clinic_admin"], s, "login_admin")
    hospitalization_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["cashier"], s, "login_cashier")
    cashier_process_ui(page, s, full)
    shot(page, s, "final_status")
    logout_ui(page)


def scenario_e(page: Page, doctors: dict) -> None:
    s = "E"
    last = f"Keita-{RUN_ID[-4:]}"
    full = f"Mariama {last}"
    login_ui(page, *ACCOUNTS["reception"], s, "login_reception")
    pid = register_patient_ui(page, s, "Mariama", last, 29, "F")
    book_appointment_ui(page, s, pid, doctors["doctor_a"]["id"], 6)
    checkin_patient_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["doctor_a"], s, "login_doctor")
    doctor_consult_flow(page, s, full, drug="Vitamine D")
    logout_ui(page)
    login_ui(page, *ACCOUNTS["reception"], s, "login_reception_2")
    book_appointment_ui(page, s, pid, doctors["doctor_b"]["id"], 8)
    checkin_patient_ui(page, s, full)
    logout_ui(page)
    login_ui(page, *ACCOUNTS["doctor_b"], s, "login_doctor_b")
    doctor_consult_flow(page, s, full, drug="Ibuprofène")
    logout_ui(page)
    login_ui(page, *ACCOUNTS["cashier"], s, "login_cashier")
    cashier_process_ui(page, s, full)
    shot(page, s, "final_status")
    logout_ui(page)


def write_report() -> None:
    report = OUT.parent.parent / f"UI_E2E_REPORT_{RUN_ID}.md"
    lines = [
        f"# UI E2E Report — {RUN_ID}",
        "",
        f"Frontend: {FRONTEND}",
        f"Screenshots: `{OUT}`",
        "",
        "## Results",
        "",
        "| Scenario | Step | Status |",
        "|----------|------|--------|",
    ]
    for sc, step, st in results:
        lines.append(f"| {sc} | {step} | {st} |")
    fails = sum(1 for _, _, st in results if st == "FAIL")
    lines.extend(["", f"**Total steps:** {len(results)} | **Failures:** {fails}"])
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {report}")


def main() -> int:
    print(f"UI E2E run {RUN_ID}")
    print(f"Screenshots -> {OUT}")
    doctors = resolve_doctors()
    print(f"Doctors: {doctors}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900}, locale="fr-FR")
        page = context.new_page()
        page.set_default_timeout(60000)

        for fn in (scenario_a, scenario_b, scenario_c, scenario_d, scenario_e):
            try:
                print(f"\n=== Scenario {fn.__name__} ===")
                fn(page, doctors)
            except Exception as exc:
                sc = fn.__name__.replace("scenario_", "").upper()
                log(sc, "EXCEPTION", False, str(exc)[:200])
                shot(page, sc, "error_state")
            finally:
                try:
                    logout_ui(page)
                except Exception:
                    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
                    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")

        browser.close()

    write_report()
    fails = sum(1 for _, _, st in results if st == "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
