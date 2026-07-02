#!/usr/bin/env python3
"""Debug lab save network on production."""
import re, time, uuid, httpx
from playwright.sync_api import sync_playwright

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
LAB = ("mamadoudianbarry06@gmail.com", "AasmaLab1!")
RUN = uuid.uuid4().hex[:6]

# Create patient via API first
rt = httpx.post(f"{BACKEND}/auth/login-json", json={"email": "baldoumar14@gmail.com", "password": "AasmaRecep1!"}).json()["access_token"]
h = {"Authorization": f"Bearer {rt}"}
reg = httpx.post(
    f"{BACKEND}/clinical/reception/his/patients",
    headers=h,
    json={
        "first_name": "LabDbg",
        "last_name": f"E2E{RUN}",
        "date_of_birth": "1990-01-01",
        "gender": "M",
        "address": "Test",
        "phone": f"621{RUN[:6]}",
        "registration_date": "2026-07-02",
        "emergency_contact": {"full_name": "C", "relationship": "Père", "phone": f"622{RUN[:6]}"},
        "payer": {"payer_type": "patient"},
    },
    timeout=90,
).json()
pid = reg["id"]
pn = reg["patient_number"]
httpx.post(
    f"{BACKEND}/clinical/reception/his/admissions",
    headers=h,
    json={
        "patient_id": pid,
        "admission_type": "specialized_consultation",
        "services": ["Consultation spécialisée — Pédiatrie", "Laboratoire"],
        "admission_date": "2026-07-02",
        "admission_time": "10:00",
    },
    timeout=90,
)

failures = []
with sync_playwright() as p:
    page = p.chromium.launch(headless=True).new_page()
    page.on("requestfailed", lambda r: failures.append(f"FAIL {r.method} {r.url} {r.failure}"))
    page.on("response", lambda r: failures.append(f"RESP {r.status} {r.request.method} {r.url}") if r.status >= 400 else None)
    page.goto(f"{FRONTEND}/login")
    page.locator("#email").fill(LAB[0])
    page.locator("#password").fill(LAB[1])
    page.click("button.login-submit")
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
    page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle")
    page.locator("#lab-patient-search").fill(pn)
    time.sleep(1.5)
    page.locator(".reception-his-search-results button").first.click()
    time.sleep(2)
    page.locator('button:has-text("Saisir résultats")').first.click(timeout=30000)
    page.locator('button:has-text("Hémogramme (Mindray BC-10)")').click()
    page.locator(".lab-his-results-table tbody tr").first.locator("input").nth(1).fill("5.1")
    page.locator('label:has-text("Biologiste") input').fill("Tech Dbg")
    page.locator('.lab-his-status-options input[type="radio"]').nth(2).check(force=True)
    page.click('button:has-text("Enregistrer les résultats")')
    time.sleep(15)
    msgs = page.locator(".clinical-message, .clinical-success, .clinical-error").all_inner_texts()
    print("MESSAGES:", msgs)
    for line in failures[-30:]:
        print(line)
