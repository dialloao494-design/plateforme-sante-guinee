#!/usr/bin/env python3
"""Production verification — Reception forms without fake field text."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://frontend-seven-rust-94.vercel.app"
EMAIL = "baldoumar14@gmail.com"
PASSWORD = "AasmaRecep1!"
RUN_ID = str(int(time.time()))[-6:]
OUT = Path(__file__).resolve().parent.parent / "docs/ui_e2e_screenshots/reception-prod-clean-fields"
OUT.mkdir(parents=True, exist_ok=True)

FAKE_TEXTS = [
    "Généré automatiquement à l'enregistrement",
    "Généré automatiquement à la création",
    "Généré à la création de la facture",
    "Généré automatiquement à la soumission",
    "Sélectionnez un patient via la recherche",
    "Créez ou sélectionnez une facture",
    "Sélectionnez une facture ci-dessous",
    "Calculé depuis la date de naissance",
]


def assert_no_fake_in_displays(page) -> None:
    for text in FAKE_TEXTS:
        loc = page.locator(f".reception-his-auto-display:has-text('{text}')")
        if loc.count() > 0:
            raise RuntimeError(f"Fake text still inside display field: {text!r}")


def display_text(page, legend: str, label: str) -> str:
    loc = page.locator(
        f'fieldset:has(legend:text("{legend}")) label:has-text("{label}") .reception-his-auto-display'
    )
    return loc.first.inner_text().strip()


def login(page, path: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
    page.locator("#email").fill(EMAIL)
    page.locator("#password").fill(PASSWORD)
    page.click("button.login-submit")
    page.wait_for_timeout(8000)
    if path not in page.url:
        page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
    page.wait_for_selector(".reception-his-tabs", timeout=120000)
    page.wait_for_timeout(1500)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 1200})
        page = ctx.new_page()
        login(page, "/clinical/reception")

        # Registration before save
        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.wait_for_timeout(500)
        assert display_text(page, "Identité", "N° dossier patient") == ""
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "01-registration-before-save.png"), full_page=True)

        page.get_by_role("textbox", name="Nom *", exact=True).fill(f"Prod{RUN_ID}")
        page.get_by_role("textbox", name="Prénom *", exact=True).fill(f"Clean{RUN_ID}")
        page.get_by_role("textbox", name="Date naissance *", exact=True).fill("1989-08-20")
        page.get_by_role("textbox", name="Tél. principal *", exact=True).fill(f"628{RUN_ID}")
        page.get_by_role("textbox", name="Adresse *", exact=True).fill("Kaloum")
        page.get_by_role("textbox", name="Nom du contact *", exact=True).fill("Contact")
        page.get_by_role("textbox", name="Téléphone *", exact=True).fill(f"629{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(5000)

        patient_id = page.locator(".reception-his-generated-id strong").first.inner_text().strip()
        if not patient_id.startswith("PAT-"):
            raise RuntimeError(f"Missing patient ID: {patient_id!r}")
        assert display_text(page, "Identité", "N° dossier patient") == patient_id
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "02-registration-after-save.png"), full_page=True)

        # Admission before patient (clear selection)
        page.get_by_role("button", name="Effacer").click()
        page.wait_for_timeout(800)
        page.locator(".reception-his-tabs button", has_text="Admission").click()
        page.wait_for_timeout(800)
        assert display_text(page, "Admission", "N° dossier patient") == ""
        assert display_text(page, "Admission", "Nom et prénom") == ""
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "03-admission-no-patient.png"), full_page=True)

        # Admission after patient selection
        page.locator("#patient-search").fill(patient_id)
        page.get_by_role("button", name="Rechercher").first.click()
        page.wait_for_timeout(2000)
        page.locator(".reception-his-search-results button").first.click(force=True)
        page.wait_for_timeout(1500)
        assert display_text(page, "Admission", "N° dossier patient") == patient_id
        assert "Prod" in display_text(page, "Admission", "Nom et prénom")
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "04-admission-with-patient.png"), full_page=True)

        page.get_by_role("button", name="Créer l'admission").click()
        page.wait_for_timeout(4000)
        page.screenshot(path=str(OUT / "05-admission-created.png"), full_page=True)

        # Billing before invoice
        page.locator(".reception-his-tabs button", has_text="Facturation").click()
        page.wait_for_timeout(800)
        assert display_text(page, "Facture", "N° facture") == ""
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "06-billing-before-invoice.png"), full_page=True)

        page.get_by_role("textbox", name="Description *", exact=True).fill("Consultation prod")
        page.get_by_role("spinbutton", name="Montant total *", exact=True).fill("150000")
        page.get_by_role("button", name="Créer facture").click()
        page.wait_for_timeout(4000)
        inv_id = display_text(page, "Facture", "N° facture")
        if not inv_id.startswith("INV-"):
            raise RuntimeError(f"Missing invoice: {inv_id!r}")
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "07-billing-after-invoice.png"), full_page=True)

        page.get_by_role("spinbutton", name="Montant à encaisser *", exact=True).fill("100000")
        page.get_by_label("Espèces", exact=True).check()
        page.get_by_role("button", name="Enregistrer paiement").click()
        page.wait_for_timeout(3000)

        # Refund before submit
        page.locator(".reception-his-tabs button", has_text="Remboursement").click()
        page.wait_for_timeout(800)
        assert display_text(page, "Demande de remboursement", "N° remboursement") == ""
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "08-refund-before-submit.png"), full_page=True)

        page.locator('label:has-text("Facture originale") select').select_option(index=1)
        page.wait_for_timeout(500)
        page.get_by_role("spinbutton", name="Montant consommé *", exact=True).fill("50000")
        page.get_by_role("spinbutton", name="Montant à rembourser *", exact=True).fill("50000")
        page.get_by_role("textbox", name="Bénéficiaire *", exact=True).fill("Famille Test")
        page.get_by_role("textbox", name="Tél. bénéficiaire *", exact=True).fill("622000000")
        page.get_by_role("button", name="Soumettre remboursement").click()
        page.wait_for_timeout(4000)
        assert_no_fake_in_displays(page)
        page.screenshot(path=str(OUT / "09-refund-after-submit.png"), full_page=True)

        page.close()
        ctx.close()
        browser.close()

    print("PRODUCTION_OK", patient_id, inv_id)
    print(f"Screenshots: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
