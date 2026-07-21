#!/usr/bin/env python3
"""Production proof — Clinique AASMA Reception module (10 screenshots)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
EMAIL = "baldoumar14@gmail.com"
PASSWORD = "AasmaRecep1!"
RUN_ID = str(int(time.time()))[-6:]
OUT = Path(__file__).resolve().parent.parent / "docs/ui_e2e_screenshots/reception-prod-aasma-proof"
OUT.mkdir(parents=True, exist_ok=True)

FAKE_IN_FIELD = [
    "Généré automatiquement à l'enregistrement",
    "Généré automatiquement à la création",
    "Généré à la création de la facture",
    "Généré automatiquement à la soumission",
    "Sélectionnez un patient via la recherche",
    "Créez ou sélectionnez une facture",
]


def display_text(page, legend: str, label: str) -> str:
    loc = page.locator(
        f'fieldset:has(legend:text("{legend}")) label:has-text("{label}") .reception-his-auto-display'
    )
    if loc.count() == 0:
        loc = page.get_by_label(label, exact=False).locator(".reception-his-auto-display")
    return loc.first.inner_text().strip()


def assert_no_fake_in_fields(page) -> None:
    displays = page.locator(".reception-his-auto-display")
    for i in range(displays.count()):
        text = displays.nth(i).inner_text().strip()
        for fake in FAKE_IN_FIELD:
            if fake in text:
                raise RuntimeError(f"Fake text inside field: {fake!r} -> {text!r}")


def assert_empty_display(page, legend: str, label: str) -> None:
    text = display_text(page, legend, label)
    if text:
        raise RuntimeError(f"Expected empty {label!r}, got {text!r}")


def login(page, path: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
    page.locator("#email").fill(EMAIL)
    page.locator("#password").fill(PASSWORD)
    page.click("button.login-submit")
    page.wait_for_timeout(8000)
    if path not in page.url:
        page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
    page.wait_for_selector(".reception-his-tabs", timeout=120000)
    page.wait_for_timeout(1000)


def main() -> int:
    results: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1400, "height": 1200}).new_page()
        login(page, "/clinical/reception")

        # 1 Registration before save
        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.wait_for_timeout(500)
        assert_empty_display(page, "Identité", "N° dossier patient")
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "01-registration-before-save.png"), full_page=True)

        # 2 Registration after save
        page.get_by_role("textbox", name="Nom *", exact=True).fill(f"Aasma{RUN_ID}")
        page.get_by_role("textbox", name="Prénom *", exact=True).fill(f"Proof{RUN_ID}")
        page.get_by_role("textbox", name="Date naissance *", exact=True).fill("1988-03-12")
        page.get_by_role("textbox", name="Tél. principal *", exact=True).fill(f"628{RUN_ID}")
        page.get_by_role("textbox", name="Adresse *", exact=True).fill("Kaloum")
        page.get_by_role("textbox", name="Nom du contact *", exact=True).fill("Contact")
        page.get_by_role("textbox", name="Téléphone *", exact=True).fill(f"629{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(5000)
        patient_id = page.locator(".reception-his-generated-id strong").first.inner_text().strip()
        if not patient_id.startswith("PAT-"):
            raise RuntimeError(f"Bad patient id: {patient_id!r}")
        results["patient"] = patient_id
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "02-registration-after-save.png"), full_page=True)

        # 3 Admission before patient
        page.get_by_role("button", name="Effacer").click()
        page.wait_for_timeout(800)
        page.locator(".reception-his-tabs button", has_text="Admission").click()
        page.wait_for_timeout(800)
        assert page.locator(".reception-his-form-notice").filter(has_text="Veuillez rechercher").count() > 0
        assert_empty_display(page, "Admission", "N° dossier patient")
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "03-admission-before-patient.png"), full_page=True)

        # 4 Admission with patient
        page.locator("#patient-search").fill(patient_id)
        page.get_by_role("button", name="Rechercher").first.click()
        page.wait_for_timeout(2000)
        page.locator(".reception-his-search-results button").first.click(force=True)
        page.wait_for_timeout(1500)
        assert display_text(page, "Admission", "N° dossier patient") == patient_id
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "04-admission-with-patient.png"), full_page=True)

        # 5 Admission created
        page.get_by_role("button", name="Créer l'admission").click()
        page.wait_for_timeout(4000)
        ok = page.locator(".clinical-message--ok").first.inner_text()
        if "Admission créée" not in ok:
            raise RuntimeError(ok)
        results["admission"] = ok.split("N° admission")[-1].strip()
        page.screenshot(path=str(OUT / "05-admission-created.png"), full_page=True)

        # 6 Billing before invoice
        page.locator(".reception-his-tabs button", has_text="Facturation").click()
        page.wait_for_timeout(800)
        assert_empty_display(page, "Facture", "N° facture")
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "06-billing-before-invoice.png"), full_page=True)

        # 7 Billing after invoice
        page.get_by_role("textbox", name="Description *", exact=True).fill("Consultation AASMA")
        page.get_by_role("spinbutton", name="Montant total *", exact=True).fill("175000")
        page.get_by_role("button", name="Créer facture").click()
        page.wait_for_timeout(4000)
        inv_id = display_text(page, "Facture", "N° facture")
        if not inv_id.startswith("INV-"):
            raise RuntimeError(f"Bad invoice: {inv_id!r}")
        results["invoice"] = inv_id
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "07-billing-after-invoice.png"), full_page=True)

        page.get_by_role("spinbutton", name="Montant à encaisser *", exact=True).fill("100000")
        page.get_by_label("Espèces", exact=True).check()
        page.get_by_role("button", name="Enregistrer paiement").click()
        page.wait_for_timeout(3000)

        # 8 Refund before submit
        page.locator(".reception-his-tabs button", has_text="Remboursement").click()
        page.wait_for_timeout(800)
        assert_empty_display(page, "Demande de remboursement", "N° remboursement")
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "08-refund-before-submit.png"), full_page=True)

        # 9 Refund after submit
        page.locator('label:has-text("Facture originale") select').select_option(index=1)
        page.wait_for_timeout(500)
        page.get_by_role("spinbutton", name="Montant consommé *", exact=True).fill("50000")
        page.wait_for_timeout(300)
        page.get_by_role("textbox", name="Bénéficiaire *", exact=True).fill("Famille Test")
        page.get_by_role("textbox", name="Tél. bénéficiaire *", exact=True).fill("622000000")
        page.get_by_role("button", name="Soumettre remboursement").click()
        page.wait_for_timeout(4000)
        ok = page.locator(".clinical-message--ok").first.inner_text()
        if "remboursement" not in ok.lower():
            raise RuntimeError(ok)
        results["refund"] = ok.split("N° remboursement")[-1].strip()
        assert_no_fake_in_fields(page)
        page.screenshot(path=str(OUT / "09-refund-after-submit.png"), full_page=True)

        # 10 Dashboard
        page.locator(".reception-his-tabs button", has_text="Tableau de bord").click()
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="Actualiser").click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "10-dashboard-stats.png"), full_page=True)

        page.close()
        browser.close()

    print("PRODUCTION_AASMA_OK")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print(f"Screenshots: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
