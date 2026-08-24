import { test, expect } from '@playwright/test';
import { loginAsRole } from './helpers.js';

async function expectNoPageOverflow(page) {
  await expect.poll(() => page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
}

test('shared hospital workflow navigation stays usable on a narrow pharmacy screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsRole(page, 'pharmacy');

  const workflow = page.getByTestId('pharmacy-tab-workflow');
  const stock = page.getByTestId('pharmacy-tab-stock');
  await expect(workflow).toHaveAttribute('aria-current', 'page');
  await stock.click();
  await expect(stock).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('heading', { name: /Stock pharmacie/i })).toBeVisible();
  await expectNoPageOverflow(page);
});

test('billing and administration forms reflow on a narrow clinic screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsRole(page, 'admin');
  let submittedPayment = null;

  await page.route('**/clinical/billing/unified/invoices*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 901,
          invoice_number: 'INV-RESP-0001',
          patient_name: 'Patient Exemple',
          status: 'pending',
          total_amount_gnf: 250000,
          paid_amount_gnf: 0,
          items: [{ id: 1, description: 'Consultation spécialisée — Médecine', amount_gnf: 250000 }],
        },
        {
          id: 902,
          invoice_number: 'INV-RESP-0002',
          patient_name: 'Patient Réglé',
          status: 'paid',
          total_amount_gnf: 150000,
          paid_amount_gnf: 150000,
          items: [{ id: 2, description: 'Consultation externe', amount_gnf: 150000 }],
        },
      ]),
    });
  });
  await page.route('**/clinical/billing/unified/invoices/901/pay', async (route) => {
    submittedPayment = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  await page.goto('/clinical/billing');
  await expect(page.getByTestId('billing-dashboard')).toBeVisible();
  await expect(page.getByRole('tab', { name: /À encaisser/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByLabel('Mode de paiement')).toHaveCount(0);
  await expect(page.locator('.billing-invoice-list')).toHaveCSS('list-style-type', 'none');
  await expect(page.getByText('INV-RESP-0001')).toBeVisible();
  await page.getByRole('button', { name: 'Encaisser 250 000 GNF' }).click();
  await expect(page.getByText('Confirmer l’encaissement')).toBeVisible();
  await expect(page.getByText('Montant à recevoir : 250 000 GNF')).toBeVisible();
  await expect(page.getByLabel('Mode de paiement')).toHaveValue('cash');
  await page.getByLabel('Mode de paiement').selectOption('orange_money');
  await expect(page.getByLabel('Mode de paiement')).toHaveValue('orange_money');
  await expect(page.getByRole('button', { name: 'Confirmer 250 000 GNF' })).toBeVisible();
  await page.getByRole('button', { name: 'Annuler' }).click();
  await expect(page.getByLabel('Mode de paiement')).toHaveCount(0);
  await page.getByRole('button', { name: 'Encaisser 250 000 GNF' }).click();
  await page.getByLabel('Mode de paiement').selectOption('orange_money');
  await page.getByRole('button', { name: 'Confirmer 250 000 GNF' }).click();
  await expect.poll(() => submittedPayment).toEqual({ payment_method: 'orange_money' });
  await expect(page.getByText('Paiement enregistré')).toBeVisible();
  await expect(page.getByLabel('Mode de paiement')).toHaveCount(0);
  await page.getByRole('tab', { name: /Payées/ }).click();
  await expect(page.getByRole('tab', { name: /Payées/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByLabel('Mode de paiement')).toHaveCount(0);
  await expect(page.getByText('INV-RESP-0002')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Télécharger la facture' }).first()).toBeVisible();
  await expectNoPageOverflow(page);

  await page.goto('/clinical/admin#create-user');
  await expect(page.getByTestId('admin-dashboard')).toBeVisible();
  await expect(page.getByLabel('Email professionnel')).toBeVisible();
  await expect(page.getByText('Aucun mot de passe à transmettre')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ouverture et relève du poste' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Ouvrir le poste|Clôturer et transmettre/ })).toBeVisible();
  await expectNoPageOverflow(page);
});

test('ward census and configuration remain operable on a narrow hospital screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsRole(page, 'admin');
  await page.goto('/clinical/hospitalization');
  await expect(page.getByTestId('hospitalization-dashboard')).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Plan des lits' })).toHaveAttribute('aria-selected', 'true');
  await page.getByRole('tab', { name: 'Configuration' }).click();
  await expect(page.getByRole('heading', { name: 'Services, chambres et couchages' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Créer le service' })).toBeVisible();
  await expectNoPageOverflow(page);
});
